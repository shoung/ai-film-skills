"""Loopback-only local dashboard HTTP API."""
import argparse
import hashlib
import http.cookies
import http.client
import json
import os
import secrets
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

try:
    from . import project_reader
except ImportError:
    import project_reader

RUNTIME = Path(os.environ.get('LOCALAPPDATA') or tempfile.gettempdir()) / 'film-workbench'
STATIC_ROOT = Path(__file__).resolve().parents[1] / 'assets' / 'dashboard'
CSP = "default-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'"


class Server(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, addr, root, token):
        self.root = Path(root).resolve()
        self.token = token
        super().__init__(addr, Handler)


class Handler(BaseHTTPRequestHandler):
    server_version = 'FilmWorkbench/1.0'

    def log_message(self, *_args):
        pass

    def _json(self, status, obj, headers=None):
        data = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', CSP)
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(data)

    def _err(self, status, message):
        self._json(status, {'error': message})

    def _safe_host(self):
        try:
            host = urllib.parse.urlsplit('//' + self.headers.get('Host', '')).hostname
        except ValueError:
            return False
        return host in ('127.0.0.1', 'localhost', '::1')

    def _origin_ok(self):
        origin = self.headers.get('Origin')
        return not origin or origin in (
            'http://127.0.0.1:' + str(self.server.server_port),
            'http://localhost:' + str(self.server.server_port),
        )

    def _authorized(self, cookie=False):
        if not self._safe_host() or not self._origin_ok():
            return False
        if secrets.compare_digest(self.headers.get('X-Film-Token', ''), self.server.token):
            return True
        if cookie:
            jar = http.cookies.SimpleCookie(self.headers.get('Cookie', ''))
            morsel = jar.get(self._cookie_name())
            return bool(morsel and secrets.compare_digest(morsel.value, self.server.token))
        return False

    def _cookie_name(self):
        return 'film_session_' + str(self.server.server_port)

    def do_POST(self):
        if not self._safe_host() or not self._origin_ok():
            return self._err(403, '拒絕非本機來源')
        if self.path == '/api/session':
            if not self._authorized():
                return self._err(403, '工作階段驗證失敗')
            cookie = self._cookie_name() + '=' + self.server.token + '; HttpOnly; SameSite=Strict; Path=/; Max-Age=43200'
            return self._json(200, {'ok': True}, {'Set-Cookie': cookie})
        if self.path == '/api/shutdown':
            if not self._authorized():
                return self._err(403, '工作階段驗證失敗')
            self._json(200, {'ok': True})
            threading.Thread(target=self.server.shutdown, daemon=True).start()
            return
        return self._err(404, '找不到端點')

    def do_GET(self):
        if not self._safe_host() or not self._origin_ok():
            return self._err(403, '拒絕非本機來源')
        parsed = urllib.parse.urlsplit(self.path)
        if parsed.path == '/' or parsed.path in ('/app.js', '/styles.css', '/tokens.css'):
            return self._static(parsed.path)
        if parsed.path.startswith('/api/') and not self._authorized(cookie=parsed.path == '/api/media'):
            return self._err(403, '工作階段驗證失敗')
        if parsed.path == '/api/health':
            return self._json(200, {'ok': True})
        if parsed.path == '/api/media':
            return self._media(urllib.parse.parse_qs(parsed.query).get('path', [''])[0])
        try:
            if parsed.path == '/api/project':
                snapshot = project_reader.project_snapshot(self.server.root)
                query = urllib.parse.parse_qs(parsed.query)
                if 'episodes' in query:
                    selected = set(query['episodes'])
                    snapshot['episodes'] = [ep for ep in snapshot['episodes'] if ep['id'] in selected]
                if 'columns' in query:
                    selected = set(query['columns'][0].split(','))
                    snapshot['columns'] = [col for col in snapshot['columns'] if col in selected]
                if 'files' in query:
                    selected = set(query['files'])
                    snapshot['files'] = [entry for entry in snapshot['files'] if entry['path'] in selected]
                return self._json(200, snapshot)
            if parsed.path == '/api/file':
                path = urllib.parse.parse_qs(parsed.query).get('path', [''])[0]
                return self._json(200, project_reader.read_document(self.server.root, path))
            return self._err(404, '找不到端點')
        except PermissionError as exc:
            return self._err(403, str(exc))
        except (ValueError, OSError, UnicodeError) as exc:
            return self._err(400, str(exc))

    def _static(self, url_path):
        relative = 'index.html' if url_path == '/' else url_path.lstrip('/')
        if any(part in ('..', '.') or part.startswith('.') for part in Path(relative).parts):
            return self._err(404, '找不到頁面資源')
        candidate = STATIC_ROOT / relative
        target = candidate.resolve(strict=False)
        if candidate.is_symlink() or STATIC_ROOT.resolve() not in target.parents or not target.is_file():
            return self._err(404, '找不到頁面資源')
        mime = {'.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8',
                '.css': 'text/css; charset=utf-8'}.get(target.suffix.lower(), 'application/octet-stream')
        try:
            data = target.read_bytes()
        except OSError:
            return self._err(404, '找不到頁面資源')
        self.send_response(200)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', CSP)
        self.end_headers()
        self.wfile.write(data)

    def do_PUT(self):
        if not self._authorized():
            return self._err(403, '工作階段驗證失敗')
        if urllib.parse.urlsplit(self.path).path != '/api/file':
            return self._err(404, '找不到端點')
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if length < 1 or length > 8 * 1024 * 1024:
                self.close_connection = True
                self._json(413, {'error': '文件大小不正確或超過上限'}, {'Connection': 'close'})
                # Drain oversized requests in bounded chunks so clients receive
                # the 413 response cleanly without buffering an untrusted body.
                if 0 < length <= 32 * 1024 * 1024:
                    self.connection.settimeout(3)
                    remaining = length
                    try:
                        while remaining:
                            chunk = self.rfile.read(min(64 * 1024, remaining))
                            if not chunk:
                                break
                            remaining -= len(chunk)
                    except OSError:
                        pass
                return
            body = json.loads(self.rfile.read(length).decode('utf-8'))
            if not isinstance(body, dict):
                return self._err(400, 'JSON 內容必須是物件')
            if not all(isinstance(body.get(key), str) for key in ('path', 'content', 'expected_version')):
                return self._err(400, 'path、content、expected_version 必須都是字串')
            result = project_reader.read_document(self.server.root, body.get('path'),
                                                  content=body.get('content'),
                                                  expected_version=body.get('expected_version'))
            return self._json(200, result)
        except (json.JSONDecodeError, UnicodeError):
            return self._err(400, 'JSON 或文字編碼格式錯誤')
        except PermissionError as exc:
            return self._err(403, str(exc))
        except ValueError as exc:
            return self._err(409 if '已變更' in str(exc) else 400, str(exc))
        except (OSError, TypeError) as exc:
            return self._err(400, '無法保存文件：' + str(exc))

    def _media(self, relative):
        try:
            target = project_reader._safe(self.server.root, relative)
            if target.suffix.lower()[1:] not in project_reader.MEDIA or not target.is_file():
                return self._err(404, '找不到媒體')
            size = target.stat().st_size
            start, end, status = 0, size - 1, 200
            requested = self.headers.get('Range')
            if requested:
                import re
                match = re.fullmatch(r'bytes=(\d*)-(\d*)', requested.strip())
                if not match:
                    return self._range_error(size)
                first, last = match.groups()
                if not first and not last:
                    return self._range_error(size)
                if not first:
                    start = max(0, size - int(last))
                else:
                    start = int(first)
                if first and last:
                    end = int(last)
                end = min(end, size - 1)
                if start >= size or end < start:
                    return self._range_error(size)
                status = 206
            self.send_response(status)
            self.send_header('Content-Type', _mime(target.suffix))
            content_length = end - start + 1
            self.send_header('Content-Length', str(content_length))
            self.send_header('Accept-Ranges', 'bytes')
            self.send_header('X-Content-Type-Options', 'nosniff')
            if status == 206:
                self.send_header('Content-Range', 'bytes ' + str(start) + '-' + str(end) + '/' + str(size))
            self.end_headers()
            remaining = content_length
            with target.open('rb') as handle:
                handle.seek(start)
                while remaining:
                    chunk = handle.read(min(64 * 1024, remaining))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    remaining -= len(chunk)
        except (ValueError, OSError):
            return self._err(400, '媒體路徑無效')

    def _range_error(self, size):
        self.send_response(416)
        self.send_header('Content-Range', 'bytes */' + str(size))
        self.send_header('Content-Length', '0')
        self.end_headers()


def _mime(ext):
    return {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.gif': 'image/gif',
            '.webp': 'image/webp', '.mp3': 'audio/mpeg', '.wav': 'audio/wav', '.m4a': 'audio/mp4',
            '.mp4': 'video/mp4', '.mov': 'video/quicktime', '.webm': 'video/webm'}.get(ext.lower(), 'application/octet-stream')


def serve(root, port=0, token=None):
    token = token or secrets.token_urlsafe(32)
    return Server(('127.0.0.1', port), root, token), token


def _state_path(root):
    digest = hashlib.sha256(str(Path(root).resolve()).encode('utf-8')).hexdigest()
    return RUNTIME / (digest + '.json')


def _write_state(path, state):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(state, ensure_ascii=False), encoding='utf-8')
    os.replace(temporary, path)


def _health(info):
    try:
        parts = urllib.parse.urlsplit(info['url'])
        if parts.scheme != 'http' or parts.hostname not in ('127.0.0.1', 'localhost', '::1') or not parts.port:
            return False
        url = urllib.parse.urlunsplit((parts.scheme, parts.netloc, '/api/health', '', ''))
        request = urllib.request.Request(url, headers={'X-Film-Token': info['token']})
        with urllib.request.urlopen(request, timeout=0.6) as response:
            return response.status == 200
    except (OSError, KeyError, ValueError):
        return False


def _read_state(path):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None


def _stop(info):
    if not _health(info):
        return False
    url = info['url'].split('#', 1)[0] + '/api/shutdown'
    request = urllib.request.Request(url, data=b'{}', method='POST', headers={
        'Content-Type': 'application/json', 'X-Film-Token': info['token']})
    try:
        with urllib.request.urlopen(request, timeout=2) as response:
            if response.status != 200:
                return False
    except OSError:
        return False
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if not _health(info):
            return True
        time.sleep(0.1)
    return False


def main(argv=None):
    parser = argparse.ArgumentParser(description='本機八欄創作台後端')
    parser.add_argument('project', nargs='?')
    parser.add_argument('--port', type=int, default=0)
    parser.add_argument('--open', action='store_true')
    parser.add_argument('--detach', action='store_true')
    parser.add_argument('--status', action='store_true')
    parser.add_argument('--stop', action='store_true')
    args = parser.parse_args(argv)
    RUNTIME.mkdir(parents=True, exist_ok=True)
    if args.status:
        if args.project:
            root = Path(args.project).resolve(strict=True)
            path = _state_path(root)
            info = _read_state(path)
            running = bool(info and info.get('project') == str(root) and _health(info))
            print(json.dumps({'running': running, 'url': info.get('url') if running else None}, ensure_ascii=False))
        else:
            states = []
            for path in RUNTIME.glob('*.json'):
                info = _read_state(path)
                if info and _health(info):
                    states.append({'project': info['project'], 'url': info['url']})
            print(json.dumps({'running': bool(states), 'servers': states}, ensure_ascii=False))
        return 0
    if args.stop:
        if not args.project:
            parser.error('--stop 需要指定專案路徑')
        root = Path(args.project).resolve(strict=True)
        state_path = _state_path(root)
        info = _read_state(state_path)
        if not info or info.get('project') != str(root) or not _stop(info):
            print('沒有可停止的本專案服務')
            return 1
        deadline = time.monotonic() + 3
        while state_path.exists() and time.monotonic() < deadline:
            try:
                state_path.unlink()
            except PermissionError:
                time.sleep(0.1)
        if state_path.exists():
            print('服務已停止，但系統狀態檔暫時無法刪除')
            return 1
        print('已停止')
        return 0
    if not args.project:
        parser.error('需要指定專案根目錄')
    root = Path(args.project).resolve(strict=True)
    if not root.is_dir():
        parser.error('專案路徑必須是目錄')
    existing = _read_state(_state_path(root))
    if existing and existing.get('project') == str(root) and _health(existing):
        print('創作台網址：' + existing['url'])
        if args.open:
            import webbrowser
            webbrowser.open(existing['url'])
        return 0
    if args.detach:
        state_path = _state_path(root)
        previous = _read_state(state_path)
        if previous and previous.get('project') == str(root) and _health(previous):
            print('創作台網址：' + previous['url'])
            if args.open:
                import webbrowser
                webbrowser.open(previous['url'])
            return 0
        state_path.unlink(missing_ok=True)
        lock_path = state_path.with_suffix('.lock')
        try:
            lock_fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(lock_fd)
        except FileExistsError:
            print('本專案背景服務正在啟動，請稍後查詢 --status')
            return 1
        command = [sys.executable, str(Path(__file__).resolve()), str(root), '--port', str(args.port)]
        log_path = RUNTIME / 'server.log'
        try:
            flags = getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0) | getattr(subprocess, 'CREATE_NO_WINDOW', 0)
            with log_path.open('ab') as log:
                process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log,
                                           stderr=subprocess.STDOUT, creationflags=flags)
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                info = _read_state(state_path)
                if info and info.get('pid') == process.pid and _health(info):
                    print('創作台網址：' + info['url'])
                    if args.open:
                        import webbrowser
                        webbrowser.open(info['url'])
                    return 0
                if process.poll() is not None:
                    break
                time.sleep(0.1)
            print('背景服務未能就緒，請查閱系統暫存目錄中的 server.log')
            return 1
        finally:
            lock_path.unlink(missing_ok=True)
    server, token = serve(root, args.port)
    url = 'http://127.0.0.1:' + str(server.server_port) + '/#token=' + token
    state_path = _state_path(root)
    _write_state(state_path, {'pid': os.getpid(), 'project': str(root), 'url': url, 'token': token})
    print('創作台網址：' + url, flush=True)
    if args.open:
        import webbrowser
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        current = _read_state(state_path)
        if current and current.get('pid') == os.getpid():
            state_path.unlink(missing_ok=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
