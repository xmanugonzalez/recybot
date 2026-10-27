"""Pi 3: static UI, camera proxy and capture forwarding to Pi 5."""
import json
import os
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

CAMERA = 'http://127.0.0.1:8765'
AI = os.environ.get('RECYBOT_AI_URL', 'http://10.199.232.70:8766')
TOKEN = (Path.home() / '.config/recybot/api-token').read_text().strip()
LOCK = threading.Lock()


class Handler(SimpleHTTPRequestHandler):
    def reply(self, status, data):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path not in ('/api/camara/stream', '/api/camara/frame', '/api/camara/status'):
            return super().do_GET()
        started = False
        try:
            with urlopen(CAMERA + self.path, timeout=8) as upstream:
                self.send_response(200)
                self.send_header('Content-Type', upstream.headers['Content-Type'])
                self.send_header('Cache-Control', 'no-store')
                self.end_headers()
                started = True
                while True:
                    data = upstream.read1(16384)
                    if not data:
                        break
                    self.wfile.write(data)
        except (OSError, URLError):
            if not started:
                self.reply(503, {'error': 'Cámara no disponible'})

    def do_POST(self):
        if self.path != '/api/identificar':
            return self.reply(404, {'error': 'Ruta desconocida'})
        # Browser must use same-origin JS with this header; no permissive CORS.
        if self.headers.get('X-Recybot-Capture') != '1':
            return self.reply(403, {'error': 'Solicitud no permitida'})
        if not LOCK.acquire(blocking=False):
            return self.reply(429, {'error': 'Ya se está analizando una captura'})
        try:
            try:
                with urlopen(CAMERA + '/api/camara/frame', timeout=8) as camera:
                    frame = camera.read(2 * 1024 * 1024 + 1)
                if len(frame) > 2 * 1024 * 1024:
                    return self.reply(413, {'error': 'Captura demasiado grande'})
            except (OSError, URLError):
                return self.reply(503, {'error': 'La cámara de la Pi 3 no entrega una captura nueva'})
            request = Request(AI + '/api/identificar', data=frame,
                              headers={'Content-Type': 'image/jpeg',
                                       'Authorization': 'Bearer ' + TOKEN}, method='POST')
            try:
                with urlopen(request, timeout=45) as response:
                    self.reply(200, json.load(response))
            except HTTPError as error:
                try:
                    detail = json.loads(error.read())
                except ValueError:
                    detail = {'error': 'La Pi 5 rechazó la captura'}
                self.reply(error.code, detail)
            except (OSError, URLError):
                self.reply(503, {'error': 'No responde la Pi 5. Verifica su alimentación y conexión de red.'})
        finally:
            LOCK.release()


if __name__ == '__main__':
    handler = partial(Handler, directory=str(Path.home() / 'recybot-web'))
    ThreadingHTTPServer(('0.0.0.0', 8080), handler).serve_forever()
