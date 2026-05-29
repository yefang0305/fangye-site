"""Run report generation (Markdown and JSON)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


class RunReport:
    """Collects per-URL status and writes Markdown / JSON reports."""

    def __init__(self):
        self.entries: list[dict] = []
        self.started_at = datetime.now().isoformat(timespec="seconds")
        self.finished_at = ""

    def record(self, url: str, status: str, message: str = "", filepath: str = ""):
        self.entries.append({
            "url": url,
            "status": status,
            "message": message,
            "filepath": filepath,
        })

    def finish(self):
        self.finished_at = datetime.now().isoformat(timespec="seconds")

    @property
    def summary(self) -> dict:
        total = len(self.entries)
        ok = sum(1 for e in self.entries if e["status"] == "ok")
        fail = sum(1 for e in self.entries if e["status"] == "fail")
        skipped = sum(1 for e in self.entries if e["status"] == "skipped")
        return {"total": total, "ok": ok, "fail": fail, "skipped": skipped}

    def to_markdown(self) -> str:
        lines = [
            "# 抖音视频下载报告",
            "",
            f"- 开始时间: {self.started_at}",
            f"- 结束时间: {self.finished_at or '进行中'}",
            f"- 总计: {self.summary['total']}  |  成功: {self.summary['ok']}  |  失败: {self.summary['fail']}  |  跳过: {self.summary['skipped']}",
            "",
            "| # | 状态 | URL | 信息 |",
            "|---|------|-----|------|",
        ]
        for i, entry in enumerate(self.entries, 1):
            status_icon = {"ok": "✅", "fail": "❌", "skipped": "⏭️"}.get(entry["status"], "❓")
            msg = entry["message"] or "-"
            lines.append(f"| {i} | {status_icon} | {entry['url']} | {msg} |")
        return "\n".join(lines) + "\n"

    def to_json(self) -> str:
        return json.dumps({
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "summary": self.summary,
            "entries": self.entries,
        }, ensure_ascii=False, indent=2)

    def save(self, output_dir: str | Path) -> tuple[Path, Path]:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        md_path = out / f"download_report_{ts}.md"
        json_path = out / f"download_report_{ts}.json"
        md_path.write_text(self.to_markdown(), encoding="utf-8")
        json_path.write_text(self.to_json(), encoding="utf-8")
        return md_path, json_path
