"""Flask web server for batch Douyin video downloading."""

from __future__ import annotations

import logging
import threading
from pathlib import Path

from flask import Flask, jsonify, render_template_string, request, send_file

from downloader import YtDlpDownloader
from report import RunReport
from url_utils import is_douyin_url, validate_urls

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("douyin_web")

app = Flask(__name__)

INDEX_HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>抖音视频批量下载</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f5f5f5; color: #333; }
  .container { max-width: 800px; margin: 40px auto; padding: 24px; }
  h1 { font-size: 1.5rem; margin-bottom: 20px; text-align: center; }
  .card { background: #fff; border-radius: 8px; padding: 24px; margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
  .card h2 { font-size: 1.1rem; margin-bottom: 12px; }
  label { display: block; font-weight: 600; margin-bottom: 6px; font-size: 0.9rem; }
  textarea { width: 100%; min-height: 160px; padding: 10px; border: 1px solid #d0d0d0; border-radius: 4px; font-family: monospace; font-size: 0.85rem; resize: vertical; }
  input[type="text"], select { width: 100%; padding: 8px 10px; border: 1px solid #d0d0d0; border-radius: 4px; font-size: 0.85rem; }
  .hint { font-size: 0.8rem; color: #888; margin-top: 4px; }
  .row { display: flex; gap: 16px; margin-bottom: 12px; }
  .row > * { flex: 1; }
  button { padding: 10px 24px; border: none; border-radius: 4px; font-size: 1rem; cursor: pointer; }
  .btn-primary { background: #fe2c55; color: #fff; }
  .btn-primary:hover { background: #e0264d; }
  .btn-primary:disabled { background: #ccc; cursor: not-allowed; }
  .btn-secondary { background: #e0e0e0; color: #333; }
  .btn-secondary:hover { background: #d0d0d0; }
  .actions { display: flex; gap: 12px; align-items: center; margin-top: 16px; }
  #status { margin-top: 16px; }
  .log-entry { padding: 6px 0; border-bottom: 1px solid #f0f0f0; font-size: 0.85rem; }
  .log-entry.ok { color: #2e7d32; }
  .log-entry.fail { color: #c62828; }
  .log-entry.info { color: #555; }
  .summary { font-weight: 600; margin: 12px 0; padding: 8px; background: #fafafa; border-radius: 4px; }
  .report-links { margin-top: 12px; }
  .report-links a { margin-right: 16px; color: #1976d2; }
  .error { color: #c62828; font-size: 0.85rem; }
</style>
</head>
<body>
<div class="container">
  <h1>抖音视频批量下载</h1>

  <div class="card">
    <h2>输入视频链接</h2>
    <label for="urls">抖音作品链接（每行一个，支持 https://www.douyin.com/video/... 和 https://v.douyin.com/... 短链接）</label>
    <textarea id="urls" placeholder="https://www.douyin.com/video/1234567890123456789&#10;https://v.douyin.com/AbCdEfG/&#10;https://www.douyin.com/note/9876543210987654321"></textarea>
    <div class="hint">以 # 开头的行会被忽略。重复链接自动去重。</div>
  </div>

  <div class="card">
    <h2>Cookie 设置（可选）</h2>
    <div class="row">
      <div>
        <label for="cookie_file">Cookie 文件路径</label>
        <input type="text" id="cookie_file" placeholder="J:\cookies\douyin_cookies.txt">
        <div class="hint">浏览器扩展导出的 Netscape 格式 cookies.txt</div>
      </div>
      <div>
        <label for="cookies_from_browser">从浏览器读取 Cookie</label>
        <select id="cookies_from_browser">
          <option value="">不使用</option>
          <option value="chrome">Chrome</option>
          <option value="edge">Edge</option>
          <option value="firefox">Firefox</option>
        </select>
        <div class="hint">使用前请关闭对应浏览器</div>
      </div>
    </div>
  </div>

  <div class="card">
    <h2>CR TubeGet 设置（推荐用于抖音）</h2>
    <div class="row">
      <div>
        <label for="crtubeget_dir">CR TubeGet 目录</label>
        <input type="text" id="crtubeget_dir" value="crtubeget_runtime" placeholder="例如 D:\tools\CRTubeGet">
        <div class="hint">已内置 crtubeget_runtime；目录内需要 qjs.exe，如果有 crck.exe，会优先用它自动导出抖音 Cookie。</div>
      </div>
      <div>
        <label for="prefer_crtubeget">下载策略</label>
        <select id="prefer_crtubeget">
          <option value="1">优先使用 CR TubeGet</option>
          <option value="0">优先使用 yt-dlp，失败再尝试 CR TubeGet</option>
        </select>
        <div class="hint">不填写目录时，只使用 yt-dlp。</div>
      </div>
    </div>
  </div>

  <div class="card">
    <h2>输出目录</h2>
    <div class="row">
      <div>
        <label for="output_dir">视频保存目录</label>
        <input type="text" id="output_dir" value="downloads">
        <div class="hint">相对于工具目录的路径，如 downloads 或 D:\videos</div>
      </div>
      <div>
        <label for="report_dir">报告保存目录</label>
        <input type="text" id="report_dir" value="reports">
        <div class="hint">下载完成后会生成 .md 和 .json 报告</div>
      </div>
    </div>
  </div>

  <div class="actions">
    <button class="btn-primary" id="btn-start" onclick="startDownload()">开始下载</button>
    <button class="btn-secondary" id="btn-validate" onclick="validateUrls()">仅验证链接</button>
  </div>

  <div id="status"></div>
</div>

<script>
let running = false;

function statusEl() { return document.getElementById('status'); }

async function validateUrls() {
  const urls = document.getElementById('urls').value;
  const resp = await fetch('/api/validate', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({urls: urls})
  });
  const data = await resp.json();
  let html = '<div class="summary">验证结果: ' + data.valid_count + ' 个有效, ' + data.rejected_count + ' 个无效</div>';
  if (data.valid.length) {
    html += '<div style="margin-top:8px"><strong>有效链接:</strong></div>';
    data.valid.forEach(u => { html += '<div class="log-entry ok">' + u + '</div>'; });
  }
  if (data.rejected.length) {
    html += '<div style="margin-top:8px"><strong style="color:#c62828">无效链接:</strong></div>';
    data.rejected.forEach(r => { html += '<div class="log-entry fail">' + r.reason + ': ' + r.url + '</div>'; });
  }
  statusEl().innerHTML = html;
}

async function startDownload() {
  if (running) return;
  running = true;
  const btn = document.getElementById('btn-start');
  btn.disabled = true;
  btn.textContent = '下载中...';

  const urls = document.getElementById('urls').value;
  const cookie_file = document.getElementById('cookie_file').value;
  const cookies_from_browser = document.getElementById('cookies_from_browser').value;
  const crtubeget_dir = document.getElementById('crtubeget_dir').value;
  const prefer_crtubeget = document.getElementById('prefer_crtubeget').value === '1';
  const output_dir = document.getElementById('output_dir').value;
  const report_dir = document.getElementById('report_dir').value;

  statusEl().innerHTML = '<div class="log-entry info">正在验证链接...</div>';

  const resp = await fetch('/api/download', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({urls, cookie_file, cookies_from_browser, crtubeget_dir, prefer_crtubeget, output_dir, report_dir})
  });

  const data = await resp.json();

  let html = '<div class="summary">下载完成: 总计 ' + data.summary.total + ' | 成功 ' + data.summary.ok + ' | 失败 ' + data.summary.fail + ' | 跳过 ' + data.summary.skipped + '</div>';

  data.entries.forEach(e => {
    const cls = e.status === 'ok' ? 'ok' : e.status === 'fail' ? 'fail' : 'info';
    html += '<div class="log-entry ' + cls + '">[' + e.status.toUpperCase() + '] ' + e.url + (e.message ? ' — ' + e.message : '') + '</div>';
  });

  if (data.report_md || data.report_json) {
    html += '<div class="report-links">';
    if (data.report_md) html += '<a href="' + data.report_md + '" target="_blank">下载报告 (Markdown)</a>';
    if (data.report_json) html += '<a href="' + data.report_json + '" target="_blank">下载报告 (JSON)</a>';
    html += '</div>';
  }

  statusEl().innerHTML = html;
  btn.disabled = false;
  btn.textContent = '开始下载';
  running = false;
}
</script>
</body>
</html>"""


@app.route("/")
def index():
    return render_template_string(INDEX_HTML)


@app.route("/api/validate", methods=["POST"])
def api_validate():
    data = request.get_json(silent=True) or {}
    raw = data.get("urls", "")
    valid, rejected = validate_urls(raw)
    return jsonify({
        "valid": valid,
        "valid_count": len(valid),
        "rejected": [{"url": u, "reason": _reject_reason(u)} for u in rejected],
        "rejected_count": len(rejected),
    })


@app.route("/api/download", methods=["POST"])
def api_download():
    data = request.get_json(silent=True) or {}
    raw = data.get("urls", "")
    cookie_file = data.get("cookie_file", "").strip()
    cookies_from_browser = data.get("cookies_from_browser", "").strip()
    crtubeget_dir = data.get("crtubeget_dir", "").strip()
    prefer_crtubeget = bool(data.get("prefer_crtubeget", True))
    output_dir = data.get("output_dir", "downloads").strip() or "downloads"
    report_dir = data.get("report_dir", "reports").strip() or "reports"

    valid_urls, rejected = validate_urls(raw)

    report = RunReport()
    for u in rejected:
        report.record(u, "skipped", _reject_reason(u))

    if not valid_urls:
        report.finish()
        md_path, json_path = report.save(report_dir)
        return jsonify(_report_response(report, md_path, json_path))

    downloader = YtDlpDownloader(
        cookie_file=cookie_file,
        cookies_from_browser=cookies_from_browser,
        crtubeget_dir=crtubeget_dir,
        prefer_crtubeget=prefer_crtubeget,
    )

    for url in valid_urls:
        try:
            filepath = downloader.download(url, output_dir)
            report.record(url, "ok", str(filepath), str(filepath))
            logger.info("下载成功: %s -> %s", url, filepath)
        except Exception as exc:
            report.record(url, "fail", str(exc))
            logger.warning("下载失败: %s — %s", url, exc)

    report.finish()
    md_path, json_path = report.save(report_dir)
    return jsonify(_report_response(report, md_path, json_path))


@app.route("/reports/<path:filename>")
def serve_report(filename):
    reports_dir = Path("reports")
    filepath = reports_dir / filename
    if not filepath.exists():
        return jsonify({"error": "文件不存在"}), 404
    return send_file(filepath, as_attachment=False)


def _reject_reason(url: str) -> str:
    url = url.strip()
    if not url or url.startswith("#"):
        return "空行或注释"
    if not url.startswith("http"):
        return "不是有效 URL"
    if not is_douyin_url(url):
        return "不是抖音链接"
    return "未知原因"


def _report_response(report: RunReport, md_path: Path, json_path: Path) -> dict:
    return {
        "summary": report.summary,
        "entries": report.entries,
        "report_md": f"/reports/{md_path.name}",
        "report_json": f"/reports/{json_path.name}",
    }


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5080, debug=False)
