from __future__ import annotations

import http.cookiejar
import json
import logging
import subprocess
import tempfile
import time
from pathlib import Path
from urllib.parse import urlparse

import requests

from .downloader import DownloadError
from .models import safe_filename, stable_url_hash

logger = logging.getLogger("BenchmarkIngestion.DouyinCR")

DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36"
)
AB_JS_URL = "http://www.cr-soft.top/js/ab.js"


def normalize_crck_cookie_output(text: str) -> str:
    """Normalize CR TubeGet crck.exe output to Netscape cookie format."""
    lines = []
    for line in text.splitlines():
        if line.startswith("Cookie:"):
            line = line[len("Cookie:"):].lstrip()
        lines.append(line)
    normalized = "\n".join(lines).strip() + "\n"
    if not normalized.startswith("# Netscape HTTP Cookie File"):
        raise DownloadError("CR TubeGet cookie 导出不是 Netscape 格式")
    return normalized


def parse_aweme_detail(data: dict, referer: str) -> dict:
    """Parse 抖音 aweme/detail API response into video metadata."""
    item = data.get("aweme_detail")
    if not item and data.get("item_list"):
        item = data["item_list"][0]
    if not item:
        raise DownloadError("抖音详情接口未返回视频信息")

    video = item.get("video") or {}
    play_addr = video.get("play_addr") or video.get("playAddr") or {}
    url_list = play_addr.get("url_list") or play_addr.get("urlList") or []
    if not url_list:
        raise DownloadError("抖音详情接口未返回可下载视频直链")

    cover = video.get("cover") or {}
    cover_urls = cover.get("url_list") or cover.get("urlList") or []
    download_urls = _build_download_candidates(video)
    if not download_urls:
        download_urls = [str(url_list[0]).replace("playwm", "play")]
    direct_url = download_urls[0]
    return {
        "id": str(item.get("aweme_id") or item.get("id") or stable_url_hash(referer)),
        "title": item.get("desc") or item.get("caption") or "douyin_video",
        "direct_url": direct_url,
        "download_urls": download_urls,
        "thumbnail": cover_urls[0] if cover_urls else "",
        "duration": (item.get("duration") or 0) / 1000,
        "referer": referer,
    }


def _build_download_candidates(video: dict) -> list[str]:
    candidates: list[str] = []

    play_addr = video.get("play_addr") or video.get("playAddr") or {}
    uri = play_addr.get("uri") or video.get("uri")
    height = int(video.get("height") or play_addr.get("height") or 0)
    if uri:
        ratio = "1080p" if height > 720 else "720p"
        candidates.append(f"https://aweme.snssdk.com/aweme/v1/play/?video_id={uri}&ratio={ratio}&line=0")

    for url in play_addr.get("url_list") or play_addr.get("urlList") or []:
        candidates.append(str(url).replace("playwm", "play"))

    for bitrate in video.get("bit_rate") or video.get("bitRate") or []:
        br_play_addr = bitrate.get("play_addr") or bitrate.get("playAddr") or {}
        for url in br_play_addr.get("url_list") or br_play_addr.get("urlList") or []:
            candidates.append(str(url).replace("playwm", "play"))

    seen = set()
    unique = []
    for url in candidates:
        if not url or url in seen:
            continue
        seen.add(url)
        unique.append(url)
    return unique


def is_douyin_url(url: str) -> bool:
    host = urlparse(url).netloc.lower()
    return "douyin.com" in host or "iesdouyin.com" in host


class DouyinCRResolver:
    """Resolve 抖音 video URLs via the aweme/detail API using CR TubeGet tooling.

    Requires CR TubeGet installed locally (provides qjs.exe for a_bogus
    signing and crck.exe for cookie export).
    """

    def __init__(
        self,
        crtubeget_dir: str | Path,
        cookie_file: str = "",
        timeout: int = 30,
    ):
        self.crtubeget_dir = Path(crtubeget_dir)
        self.cookie_file = cookie_file
        self.timeout = timeout
        self.qjs_path = self.crtubeget_dir / "qjs.exe"
        self.crck_path = self.crtubeget_dir / "crck.exe"

    def resolve(self, url: str) -> dict:
        if not is_douyin_url(url):
            raise DownloadError("CR TubeGet fallback 仅支持抖音链接")
        if not self.qjs_path.exists():
            raise DownloadError(f"未找到 CR TubeGet qjs.exe: {self.qjs_path}")

        with tempfile.TemporaryDirectory(prefix="douyin_cr_") as tmp:
            tmp_path = Path(tmp)
            session = requests.Session()
            session.headers.update({"User-Agent": DEFAULT_UA})
            self._load_cookies(session, url, tmp_path)

            redirect = session.get(url, allow_redirects=True, timeout=self.timeout)
            redirect.raise_for_status()
            referer = redirect.url
            item_id = self._extract_item_id(referer)
            if not item_id:
                raise DownloadError(f"未能从抖音链接解析作品 ID: {referer}")

            detail = self._fetch_aweme_detail(session, item_id, referer, tmp_path)
            return parse_aweme_detail(detail, referer)

    def _load_cookies(self, session: requests.Session, url: str, tmp_path: Path) -> None:
        cookie_paths = []
        if self.crck_path.exists():
            exported = subprocess.check_output(
                [str(self.crck_path), url],
                cwd=str(self.crtubeget_dir),
                timeout=self.timeout,
                text=True,
                stderr=subprocess.STDOUT,
            )
            cr_cookie = tmp_path / "crtubeget_cookies.txt"
            cr_cookie.write_text(normalize_crck_cookie_output(exported), encoding="utf-8")
            cookie_paths.append(cr_cookie)
        if self.cookie_file:
            cookie_paths.append(Path(self.cookie_file))

        for cookie_path in cookie_paths:
            if not cookie_path.exists():
                continue
            jar = http.cookiejar.MozillaCookieJar(str(cookie_path))
            jar.load(ignore_discard=True, ignore_expires=True)
            session.cookies.update(jar)

    def _fetch_aweme_detail(
        self,
        session: requests.Session,
        item_id: str,
        referer: str,
        tmp_path: Path,
    ) -> dict:
        args = (
            "app_name=aweme&aid=1128&device_platform=iphone&os_version=12.3.1"
            f"&device_id={int(time.time() * 1000)}&aweme_id={item_id}"
        )
        api_url = (
            "https://www.douyin.com/aweme/v1/web/aweme/detail/?"
            f"{args}&a_bogus={self._a_bogus(args, tmp_path)}"
        )
        headers = {
            "User-Agent": DEFAULT_UA,
            "Referer": referer,
            "Accept": "application/json, text/plain, */*",
        }
        response = session.get(api_url, headers=headers, timeout=self.timeout)
        response.raise_for_status()
        try:
            return response.json()
        except json.JSONDecodeError as exc:
            raise DownloadError("抖音详情接口返回了非 JSON 内容") from exc

    def _a_bogus(self, args: str, tmp_path: Path) -> str:
        ab_js = tmp_path / "ab.js"
        ab_source = self._load_ab_js()
        ab_js.write_text(ab_source, encoding="utf-8")
        runner = tmp_path / "run_ab.js"
        runner.write_text(
            "var window={}; var navigator={userAgent:%r};\n%s\nconsole.log(window.ab(%r,%r));\n"
            % (DEFAULT_UA, ab_source, args, DEFAULT_UA),
            encoding="utf-8",
        )
        return subprocess.check_output(
            [str(self.qjs_path), str(runner)],
            cwd=str(self.crtubeget_dir),
            timeout=self.timeout,
            text=True,
        ).strip()

    def _load_ab_js(self) -> str:
        cache_path = self.crtubeget_dir / "ab.js"
        try:
            response = requests.get(AB_JS_URL, timeout=self.timeout)
            response.raise_for_status()
            source = response.text.strip()
            if "window.ab" not in source:
                raise DownloadError("远程 ab.js 内容不完整")
            try:
                cache_path.write_text(source, encoding="utf-8")
            except OSError as exc:
                logger.warning("写入 ab.js 缓存失败: %s", exc)
            return source
        except Exception as exc:
            if cache_path.exists():
                logger.warning("远程 ab.js 不可用，改用本地缓存: %s", exc)
                cached = cache_path.read_text(encoding="utf-8").strip()
                if cached:
                    return cached
            raise DownloadError(f"获取抖音 a_bogus 脚本失败，且没有可用缓存: {exc}") from exc

    @staticmethod
    def _extract_item_id(url: str) -> str:
        parsed = urlparse(url)
        parts = [part for part in parsed.path.split("/") if part]
        for marker in ("video", "note"):
            if marker in parts:
                index = parts.index(marker)
                if index + 1 < len(parts):
                    return parts[index + 1]
        return ""


class DouyinCRVideoDownloader:
    """Download 抖音 videos via the CR TubeGet resolution + direct download path."""

    def __init__(self, crtubeget_dir: str | Path, cookie_file: str = "", timeout: int = 30):
        self.resolver = DouyinCRResolver(crtubeget_dir, cookie_file=cookie_file, timeout=timeout)
        self.timeout = timeout

    def download(self, url: str, output_dir: str | Path) -> Path:
        resolved = self.resolver.resolve(url)
        output_root = Path(output_dir)
        output_root.mkdir(parents=True, exist_ok=True)
        title = safe_filename(resolved.get("title") or "douyin_video", "douyin_video")
        video_id = safe_filename(resolved.get("id") or stable_url_hash(url), stable_url_hash(url))
        target = output_root / f"{title}-{video_id}.mp4"
        tmp_target = target.with_suffix(target.suffix + ".part")

        headers_list = self._download_headers(resolved.get("referer") or url)
        errors = []
        for candidate in resolved.get("download_urls") or [resolved["direct_url"]]:
            for headers in headers_list:
                try:
                    self._download_candidate(candidate, tmp_target, headers)
                    break
                except requests.HTTPError as exc:
                    status = exc.response.status_code if exc.response is not None else "unknown"
                    errors.append(f"{status} {candidate}")
                    if tmp_target.exists():
                        tmp_target.unlink()
                    continue
                except requests.RequestException as exc:
                    errors.append(f"{type(exc).__name__} {candidate}")
                    if tmp_target.exists():
                        tmp_target.unlink()
                    continue
            if tmp_target.exists() and tmp_target.stat().st_size > 0:
                break
        else:
            raise DownloadError("CR TubeGet fallback 下载失败: " + "; ".join(errors[-3:]))

        tmp_target.replace(target)
        if target.stat().st_size <= 0:
            raise DownloadError("CR TubeGet fallback 下载到空文件")
        return target

    def _download_candidate(self, candidate: str, tmp_target: Path, headers: dict) -> None:
        with requests.get(
            candidate,
            headers=headers,
            stream=True,
            timeout=self.timeout,
            allow_redirects=True,
        ) as response:
            response.raise_for_status()
            with tmp_target.open("wb") as fh:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        fh.write(chunk)

    def _download_headers(self, referer: str) -> list[dict]:
        ios_ua = (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 18_2 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Mobile/15E148 Safari/604.1"
        )
        return [
            {"User-Agent": ios_ua, "Referer": referer},
            {"User-Agent": DEFAULT_UA, "Referer": referer},
            {"User-Agent": ios_ua},
            {"User-Agent": DEFAULT_UA},
        ]
