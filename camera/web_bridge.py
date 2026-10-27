"""Pi 3: static UI, camera proxy and capture forwarding to Pi 5."""
import json
import os
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

CAMERA = os.environ.get('RECYBOT_CAMERA_URL', 'http://127.0.0.1:8765').rstrip('/')
AI = os.environ.get('RECYBOT_AI_URL', 'http://10.199.232.70:8766').rstrip('/')
TOKEN_PATH = Path(os.environ.get(
    'RECYBOT_API_TOKEN_PATH',
    Path.home() / '.config/recybot/api-token',
))
LOCK = threading.Lock()
MAX_FRAME_BYTES = 2 * 1024 * 1024


class CaptureRequestError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = message


def read_uploaded_frame(headers, stream):
    try:
        length = int(headers.get('Content-Length', '0'))
    except ValueError as error:
        raise CaptureRequestError(400, 'Longitud de captura incorrecta') from error
    if not 0 < length <= MAX_FRAME_BYTES:
        raise CaptureRequestError(413, 'Captura vacía o demasiado grande')
    frame = stream.read(length)
    if len(frame) != length:
        raise CaptureRequestError(400, 'La captura llegó incompleta')
    return frame


def read_token():
    token = TOKEN_PATH.read_text().strip()
    if len(token) < 32:
        raise RuntimeError('Token de acceso inválido')
    return token


class Handler(SimpleHTTPRequestHandler):
    def reply(self, status, data):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def forward_ai(self, request, timeout=45):
        try:
            with urlopen(request, timeout=timeout) as response:
                self.reply(response.status, json.load(response))
        except HTTPError as error:
            try:
                detail = json.loads(error.read())
            except ValueError:
                detail = {'error': 'La Pi 5 rechazó la solicitud'}
            self.reply(error.code, detail)
        except (OSError, URLError):
            self.reply(503, {'error': 'No responde la Pi 5. Verifica su alimentación y conexión de red.'})

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
        if self.path == '/api/muestras/confirmar':
            if self.headers.get('X-Recybot-Review') != '1':
                return self.reply(403, {'error': 'Solicitud no permitida'})
            try:
                length = int(self.headers.get('Content-Length', '0'))
            except ValueError:
                return self.reply(400, {'error': 'Longitud incorrecta'})
            if not 0 < length <= 4096:
                return self.reply(413, {'error': 'Confirmación vacía o demasiado grande'})
            if self.headers.get('Content-Type', '').split(';', 1)[0] != 'application/json':
                return self.reply(415, {'error': 'Se requiere JSON'})
            payload = self.rfile.read(length)
            request = Request(
                AI + self.path,
                data=payload,
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': 'Bearer ' + read_token(),
                },
                method='POST',
            )
            return self.forward_ai(request, timeout=12)
        if self.path != '/api/identificar':
            return self.reply(404, {'error': 'Ruta desconocida'})
        # Browser must use same-origin JS with this header; no permissive CORS.
        if self.headers.get('X-Recybot-Capture') != '1':
            return self.reply(403, {'error': 'Solicitud no permitida'})
        if not LOCK.acquire(blocking=False):
            return self.reply(429, {'error': 'Ya se está analizando una captura'})
        try:
            content_type = self.headers.get('Content-Type', '').split(';', 1)[0]
            if content_type == 'image/jpeg':
                try:
                    frame = read_uploaded_frame(self.headers, self.rfile)
                except CaptureRequestError as error:
                    return self.reply(error.status, {'error': error.message})
            elif not content_type:
                try:
                    with urlopen(CAMERA + '/api/camara/frame', timeout=8) as camera:
                        frame = camera.read(MAX_FRAME_BYTES + 1)
                    if len(frame) > MAX_FRAME_BYTES:
                        return self.reply(413, {'error': 'Captura demasiado grande'})
                except (OSError, URLError):
                    return self.reply(503, {'error': 'La cámara de la Pi 3 no entrega una captura nueva'})
            else:
                return self.reply(415, {'error': 'La captura debe ser una imagen JPEG'})
            request = Request(AI + '/api/identificar', data=frame,
                              headers={'Content-Type': 'image/jpeg',
                                       'Authorization': 'Bearer ' + read_token()}, method='POST')
            self.forward_ai(request)
        finally:
            LOCK.release()


if __name__ == '__main__':
    handler = partial(Handler, directory=str(Path.home() / 'recybot-web'))
    ThreadingHTTPServer(('0.0.0.0', 8080), handler).serve_forever()
