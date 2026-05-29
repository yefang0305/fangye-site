from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path


def safe_filename(value: str, fallback: str = "untitled") -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value).strip(" ._")
    return cleaned[:120] or fallback


def export_links_to_markdown(
    profile_url: str,
    sec_uid: str,
    links: list[str],
    output_dir: str | Path,
) -> Path:
    """将作品链接导出为 Markdown 文件。

    Returns:
        生成的 Markdown 文件路径。
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = safe_filename(f"douyin_links_{sec_uid}_{timestamp}", "douyin_links") + ".md"
    output_path = output_dir / filename

    lines = [
        f"# 抖音主页作品链接",
        "",
        f"- **主页链接**: {profile_url}",
        f"- **sec_uid**: `{sec_uid}`",
        f"- **导出时间**: {datetime.now().isoformat(timespec='seconds')}",
        f"- **作品数量**: {len(links)}",
        "",
        "---",
        "",
    ]

    for i, link in enumerate(links, 1):
        lines.append(f"{i}. [{link}]({link})")

    lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path
