"""Core downloader that wraps yt-dlp for Douyin video downloads."""

from __future__ import annotations

import logging
from pathlib import Path

from url_utils import stable_url_hash

logger = logging.getLogger("douyin_downloader")


class DownloadError(RuntimeError):
    """Raised when a single-URL download fails after all retries."""


class YtDlpDownloader:
    """Minimal yt-dlp wrapper for downloading Douyin videos."""

    def __init__(
        self,
        cookie_file: str = "",
        cookies_from_browser: str = "",
        crtubeget_dir: str = "",
        prefer_crtubeget: bool = True,
    ):
        self.cookie_file = cookie_file
        self.cookies_from_browser = cookies_from_browser
        self.crtubeget_dir = crtubeget_dir
        self.prefer_crtubeget = prefer_crtubeget

    def download(self, url: str, output_dir: str | Path) -> Path:
        output_root = Path(output_dir)
        output_root.mkdir(parents=True, exist_ok=True)
        outtmpl = str(output_root / "%(title).120B-%(id)s.%(ext)s")

        if self._should_use_crtubeget_first(url):
            return self._download_with_crtubeget(url, output_root)

        try:
            info = self._download_with_yt_dlp(url, outtmpl)
        except DownloadError as exc:
            if self._can_fallback_to_crtubeget(url, str(exc)):
                return self._download_with_crtubeget(url, output_root)
            raise

        requested = info.get("requested_downloads") or []
        for item in requested:
            filepath = item.get("filepath")
            if filepath and Path(filepath).exists():
                return Path(filepath)

        fallback = stable_url_hash(url)
        candidates = list(output_root.glob(f"*{fallback}*")) + list(output_root.glob("*"))
        for candidate in sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True):
            if candidate.is_file():
                return candidate

        raise DownloadError(f"下载完成后未找到输出文件: {url}")

    def _download_with_yt_dlp(self, url: str, outtmpl: str) -> dict:
        try:
            import yt_dlp
        except ImportError as exc:
            raise DownloadError("yt-dlp 未安装，请先安装依赖: pip install yt-dlp") from exc

        opts = self._build_opts(outtmpl)
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                return ydl.extract_info(url, download=True)
        except Exception as exc:
            raise DownloadError(_explain_yt_dlp_error(exc)) from exc

    def _should_use_crtubeget_first(self, url: str) -> bool:
        return bool(self.prefer_crtubeget and self.crtubeget_dir and _is_douyin_url(url))

    def _can_fallback_to_crtubeget(self, url: str, error_message: str) -> bool:
        if not self.crtubeget_dir or not _is_douyin_url(url):
            return False
        fallback_needles = (
            "抖音要求新鲜 Cookie",
            "Fresh cookies",
            "HTTP Error 403",
            "HTTP Error 404",
            "Unsupported URL",
        )
        return any(needle in error_message for needle in fallback_needles)

    def _download_with_crtubeget(self, url: str, output_root: Path) -> Path:
        from douyin_cr import DouyinCRVideoDownloader

        return DouyinCRVideoDownloader(
            self.crtubeget_dir,
            cookie_file=self.cookie_file,
        ).download(url, output_root)

    def _build_opts(self, outtmpl: str) -> dict:
        opts: dict = {
            "format": "bv*+ba/best",
            "outtmpl": outtmpl,
            "merge_output_format": "mp4",
            "quiet": True,
            "no_warnings": True,
            "retries": 3,
            "fragment_retries": 3,
            "socket_timeout": 30,
            "nocheckcertificate": True,
        }
        if self.cookie_file:
            opts["cookiefile"] = self.cookie_file
        if self.cookies_from_browser:
            opts["cookiesfrombrowser"] = (self.cookies_from_browser,)
        return opts


def _explain_yt_dlp_error(error: Exception) -> str:
    text = str(error)
    if "Failed to decrypt with DPAPI" in text:
        return (
            "无法解密浏览器 Cookie（Windows DPAPI 权限限制）。"
            "请改用浏览器扩展导出 douyin.com 的 Netscape 格式 cookies.txt。"
        )
    if "Fresh cookies" in text:
        return (
            "抖音要求新鲜 Cookie。请先在浏览器里打开抖音并确认能播放该视频，"
            "或导出 douyin.com 的 cookies.txt 后在页面中选择。"
        )
    if "Could not copy Chrome cookie database" in text or "Permission denied" in text:
        return (
            "无法复制浏览器 Cookie 数据库。请完全关闭对应浏览器后台进程，"
            "或改用 cookies.txt 文件。"
        )
    return text


def _is_douyin_url(url: str) -> bool:
    try:
        from douyin_cr import is_douyin_url
    except Exception:
        return False
    return is_douyin_url(url)
