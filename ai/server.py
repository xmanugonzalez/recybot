"""Pi 5: bounded, serialized CPU inference. No camera or motor control."""
import io
import json
import os
import secrets
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

os.environ.setdefault('OMP_NUM_THREADS', '1')
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
BASE = Path(__file__).resolve().parent
os.environ.setdefault('YOLO_CONFIG_DIR', str(BASE / 'config'))
LOCK = threading.Lock()
MAX_IMAGE = 2 * 1024 * 1024


class Handler(BaseHTTPRequestHandler):
    def setup(self):
        super().setup()
        self.connection.settimeout(20)

    def reply(self, status, data):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path != '/api/salud':
            return self.reply(404, {'error': 'Ruta desconocida'})
        self.reply(200, {'estado': 'listo', 'modelo': 'yolov8n.pt',
                         'clasificacion_material': False})

    def do_POST(self):
        if self.path != '/api/identificar':
            return self.reply(404, {'error': 'Ruta desconocida'})
        if not secrets.compare_digest(self.headers.get('Authorization', ''), 'Bearer ' + TOKEN):
            return self.reply(401, {'error': 'Acceso no autorizado'})
        try:
            length = int(self.headers.get('Content-Length', '0'))
        except ValueError:
            return self.reply(400, {'error': 'Longitud incorrecta'})
        if not 0 < length <= MAX_IMAGE:
            return self.reply(413, {'error': 'Imagen vacía o demasiado grande'})
        if self.headers.get('Content-Type') != 'image/jpeg':
            return self.reply(415, {'error': 'Se requiere JPEG'})
        if not LOCK.acquire(blocking=False):
            return self.reply(429, {'error': 'La Pi 5 está procesando otra imagen'})
        try:
            temperature = Path('/sys/class/thermal/thermal_zone0/temp')
            if temperature.exists() and int(temperature.read_text()) >= 80000:
                return self.reply(503, {'error': 'Pi 5 caliente: esperar antes de reintentar'})
            raw = self.rfile.read(length)
            from PIL import Image, UnidentifiedImageError
            try:
                with Image.open(io.BytesIO(raw)) as picture:
                    if picture.width * picture.height > 1920 * 1080:
                        return self.reply(413, {'error': 'Resolución demasiado grande'})
                    picture = picture.convert('RGB')
            except (UnidentifiedImageError, OSError, ValueError):
                return self.reply(400, {'error': 'Imagen inválida'})
            start = time.perf_counter()
            result = MODEL.predict(picture, imgsz=320, conf=0.4, device='cpu', verbose=False)[0]
            detections = [{'clase': result.names[int(box.cls.item())],
                           'confianza': round(float(box.conf.item()), 3),
                           'xyxy': [round(v, 1) for v in box.xyxy[0].tolist()]}
                          for box in result.boxes]
            self.reply(200, {'timestamp_utc': datetime.now(timezone.utc).isoformat(),
                             'modelo': 'yolov8n.pt', 'procesado_en': 'Pi 5',
                             'tiempo_ms': round((time.perf_counter() - start) * 1000),
                             'detecciones': detections, 'categoria': None,
                             'requiere_confirmacion_material': True})
        except Exception:
            import traceback
            traceback.print_exc()
            self.reply(500, {'error': 'No se pudo procesar la imagen en la Pi 5'})
        finally:
            LOCK.release()


if __name__ == '__main__':
    TOKEN = (BASE / 'config' / 'api-token').read_text().strip()
    if len(TOKEN) < 32:
        raise RuntimeError('Token de acceso inválido')
    import torch
    from ultralytics import YOLO
    torch.set_num_threads(1)
    MODEL = YOLO(str(BASE / 'modelos' / 'yolov8n.pt'))
    MODEL.add_callback('on_predict_start', lambda predictor: torch.set_num_threads(1))
    print('Recybot IA listo en puerto 8766', flush=True)
    ThreadingHTTPServer(('0.0.0.0', 8766), Handler).serve_forever()
