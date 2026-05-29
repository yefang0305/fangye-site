from __future__ import annotations

import logging
from pathlib import Path

from flask import Flask, jsonify, render_template, request

from core.markdown_exporter import export_links_to_markdown
from core.profile_extractor import ProfileExtractionError, extract_profile_links

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/extract", methods=["POST"])
def api_extract():
    data = request.get_json(silent=True) or {}
    profile_url = (data.get("profile_url") or "").strip()
    cookie_text = (data.get("cookie_text") or "").strip()
    cookie_file = (data.get("cookie_file") or "").strip()
    page_size = int(data.get("page_size") or 35)
    max_pages = int(data.get("max_pages") or 200)
    timeout = int(data.get("timeout") or 30)

    if not profile_url:
        return jsonify({"ok": False, "error": "请填写抖音主页链接"}), 400

    try:
        result = extract_profile_links(
            profile_url=profile_url,
            cookie_text=cookie_text,
            cookie_file=cookie_file,
            timeout=timeout,
            page_size=page_size,
            max_pages=max_pages,
        )
    except ProfileExtractionError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception as exc:
        logger.exception("提取失败")
        return jsonify({"ok": False, "error": f"提取失败: {exc}"}), 500

    md_path = export_links_to_markdown(
        profile_url=profile_url,
        sec_uid=result["sec_uid"],
        links=result["links"],
        output_dir=OUTPUT_DIR,
    )

    return jsonify({
        "ok": True,
        "profile_url": result["profile_url"],
        "final_url": result["final_url"],
        "sec_uid": result["sec_uid"],
        "total": result["total"],
        "links": result["links"],
        "md_file": str(md_path),
    })


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5999, debug=True)
