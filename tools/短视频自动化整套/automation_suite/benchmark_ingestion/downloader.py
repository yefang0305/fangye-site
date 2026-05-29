from __future__ import annotations

from pathlib import Path
import logging

from .models import safe_filename, stable_url_hash

logger = logging.getLogger("BenchmarkIngestion.Downloader")


class DownloadError(RuntimeError):
    pass


def explain_yt_dlp_error(error: Exception | str) -> str:
    """Translate yt-dlp errors into actionable Chinese guidance."""
    text = str(error)
    if "Failed to decrypt with DPAPI" in text:
        return (
            "无法解密浏览器 Cookie（Windows DPAPI 权限限制）。"
            "请改用浏览器扩展导出 douyin.com 的 Netscape 格式 cookies.txt，"
            "然后在“抖音 Cookie”的 Cookie 文件里选择该文件。"
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


class YtDlpVideoDownloader:
    """Video downloader using yt-dlp with optional CR TubeGet fallback for 抖音."""

    def __init__(
        self,
        cookie_file: str = "",
        cookie_string: str = "",
        cookies_from_browser: str = "",
        crtubeget_dir: str = "",
        douyin_fallback_downloader=None,
    ):
        self.cookie_file = cookie_file
        self.cookie_string = cookie_string
        self.cookies_from_browser = cookies_from_browser
        self.crtubeget_dir = crtubeget_dir
        self.douyin_fallback_downloader = douyin_fallback_downloader

    def download(self, url: str, output_dir: str | Path) -> Path:
        output_root = Path(output_dir)
        output_root.mkdir(parents=True, exist_ok=True)

        if self._should_use_douyin_cr_first(url):
            return self._douyin_fallback().download(url, output_root)

        try:
            return self._download_with_yt_dlp(url, output_root, str(output_root / "%(title).120B-%(id)s.%(ext)s"))
        except DownloadError as exc:
            if self._can_fallback_to_douyin_cr(url, str(exc)):
                return self._douyin_fallback().download(url, output_root)
            raise

    def _download_with_yt_dlp(self, url: str, output_root: Path, outtmpl: str | Path) -> Path:
        try:
            import yt_dlp
        except ImportError as exc:
            raise DownloadError("yt-dlp 未安装，请先安装依赖或在 requirements.txt 中启用 yt-dlp") from exc

        fallback_name = stable_url_hash(url)
        opts = self._build_opts(outtmpl)

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
        except Exception as exc:
            raise DownloadError(explain_yt_dlp_error(exc)) from exc

        requested = info.get("requested_downloads") or []
        for item in requested:
            filepath = item.get("filepath")
            if filepath and Path(filepath).exists():
                return Path(filepath)

        title = safe_filename(info.get("title") or fallback_name, fallback_name)
        video_id = safe_filename(str(info.get("id") or fallback_name), fallback_name)
        candidates = list(output_root.glob(f"{title}-{video_id}.*")) or list(output_root.glob(f"*{video_id}*"))
        for candidate in candidates:
            if candidate.is_file():
                return candidate

        raise DownloadError(f"下载完成后未找到输出文件: {url}")

    def _can_fallback_to_douyin_cr(self, url: str, error_message: str) -> bool:
        if "抖音要求新鲜 Cookie" not in error_message and "Fresh cookies" not in error_message:
            return False
        return self._is_douyin_with_fallback(url)

    def _should_use_douyin_cr_first(self, url: str) -> bool:
        return self._is_douyin_with_fallback(url)

    def _is_douyin_with_fallback(self, url: str) -> bool:
        try:
            from .douyin_cr import is_douyin_url
        except Exception:
            return False
        return is_douyin_url(url) and bool(self.douyin_fallback_downloader or self.crtubeget_dir)

    def _douyin_fallback(self):
        if self.douyin_fallback_downloader:
            return self.douyin_fallback_downloader
        from .douyin_cr import DouyinCRVideoDownloader

        self.douyin_fallback_downloader = DouyinCRVideoDownloader(
            self.crtubeget_dir,
            cookie_file=self.cookie_file,
        )
        return self.douyin_fallback_downloader

    def _build_opts(self, outtmpl: str | Path) -> dict:
        opts = {
            "format": "bv*+ba/best",
            "outtmpl": str(outtmpl),
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
