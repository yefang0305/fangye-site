"""
公众号智能排版助手 - 本地服务器
作用:
  1. 托管 index.html (解决 file:// 打开的各种限制)
  2. 代理豆包 API 请求 (解决浏览器 CORS 拦截)
  3. API Key 由浏览器传入后只在本机转发,不出你电脑
"""
import http.server
import socketserver
import socket
import json
import urllib.request
import urllib.error
import webbrowser
import threading
import os
import sys

# Windows 控制台中文兼容
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

PORT = 8765
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    def do_POST(self):
        if self.path == '/api/format':
            self.handle_format()
        else:
            self.send_error(404, 'Not Found')

    def handle_format(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            req_data = json.loads(body.decode('utf-8'))

            base_url = req_data.pop('baseURL', '').rstrip('/')
            api_key = req_data.pop('apiKey', '')

            if not base_url or not api_key:
                self._send_json(400, {'error': {'message': '缺少 baseURL 或 apiKey'}})
                return

            target_url = f'{base_url}/chat/completions'
            req = urllib.request.Request(
                target_url,
                data=json.dumps(req_data).encode('utf-8'),
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {api_key}'
                },
                method='POST'
            )

            with urllib.request.urlopen(req, timeout=600) as resp:
                data = resp.read()
                self.send_response(resp.status)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        except urllib.error.HTTPError as e:
            err_body = e.read()
            try:
                err_json = json.loads(err_body.decode('utf-8'))
            except Exception:
                err_json = {'error': {'message': err_body.decode('utf-8', errors='replace')}}
            self._send_json(e.code, err_json)

        except socket.timeout:
            self._send_json(504, {'error': {'message': 'API 服务器响应超时：模型生成时间过长。已等待 10 分钟，可以尝试缩短文章、关闭配图建议，或换更快的模型。'}})

        except urllib.error.URLError as e:
            self._send_json(502, {'error': {'message': f'无法连接到 API 服务器: {e.reason}'}})

        except Exception as e:
            self._send_json(500, {'error': {'message': f'代理异常: {e}'}})

    def _send_json(self, status, obj):
        data = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format, *args):
        # 简化日志输出
        sys.stderr.write(f'[{self.log_date_time_string()}] {format % args}\n')


def open_browser():
    webbrowser.open(f'http://localhost:{PORT}/index.html')


def main():
    try:
        with socketserver.TCPServer(('127.0.0.1', PORT), Handler) as httpd:
            print('=' * 50)
            print(f'  公众号智能排版助手已启动')
            print(f'  访问地址: http://localhost:{PORT}/index.html')
            print(f'  按 Ctrl+C 停止服务')
            print('=' * 50)
            threading.Timer(0.8, open_browser).start()
            httpd.serve_forever()
    except KeyboardInterrupt:
        print('\n服务已停止')
    except OSError as e:
        if 'Address already in use' in str(e) or getattr(e, 'errno', None) in (48, 98, 10048):
            print(f'端口 {PORT} 已被占用,请关闭占用该端口的程序后再试。')
        else:
            raise


if __name__ == '__main__':
    main()


