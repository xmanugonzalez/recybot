"""Inferencia local y captura de muestras confirmadas para Recybot."""
import io
import json
import os
import secrets
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from PIL import Image, UnidentifiedImageError

from learning import ActiveLearningStore, CLASES_RECYBOT, SampleNotFoundError
from openai_provider import DEFAULT_MODEL as DEFAULT_OPENAI_MODEL, OpenAIProvider
from roboflow_provider import DEFAULT_MODEL_ID, RoboflowProvider

os.environ.setdefault('OMP_NUM_THREADS', '1')
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
BASE = Path(__file__).resolve().parent
os.environ.setdefault('YOLO_CONFIG_DIR', str(BASE / 'config'))
LOCK = threading.Lock()
MAX_IMAGE = 2 * 1024 * 1024
MAX_JSON = 4096


def configured_path(variable, default):
    value = Path(os.environ.get(variable, default))
    return value if value.is_absolute() else BASE / value


MODEL_PATH = configured_path('RECYBOT_MODEL_PATH', 'modelos/yolov8n.pt')
MODEL_MODE = os.environ.get('RECYBOT_MODEL_MODE', 'prueba').lower()
INFERENCE_BACKEND = os.environ.get('RECYBOT_INFERENCE_BACKEND', 'local').lower()
CONFIDENCE = float(os.environ.get('RECYBOT_CONFIDENCE', '0.4'))
IMAGE_SIZE = int(os.environ.get('RECYBOT_IMAGE_SIZE', '320'))
DEVICE_LABEL = os.environ.get('RECYBOT_DEVICE_LABEL', 'Pi 5')
LEARNING_ROOT = configured_path('RECYBOT_LEARNING_DIR', 'datos_aprendizaje')
LEARNING_ENABLED = os.environ.get('RECYBOT_COLLECT_SAMPLES', 'true').lower() == 'true'
ROBOFLOW_API_KEY_PATH = configured_path('ROBOFLOW_API_KEY_PATH', 'config/roboflow-api-key')
ROBOFLOW_MODEL_ID = os.environ.get('ROBOFLOW_MODEL_ID', DEFAULT_MODEL_ID)
OPENAI_API_KEY_PATH = configured_path('OPENAI_API_KEY_PATH', 'config/openai-api-key')
OPENAI_MODEL = os.environ.get('OPENAI_MODEL', DEFAULT_OPENAI_MODEL)
SAMPLES = ActiveLearningStore(LEARNING_ROOT)
OPENAI = None
ROBOFLOW = None
LEGACY_MODEL_CLASSES = {
    'botella_plastico': 'plastico',
    'botella_vidrio': 'otros',
    'lata': 'metal',
}


def material_for(class_name):
    if MODEL_MODE != 'recybot':
        return None
    return CLASES_RECYBOT.get(class_name)


def predict_local(picture):
    result = MODEL.predict(
        picture,
        imgsz=IMAGE_SIZE,
        conf=CONFIDENCE,
        device='cpu',
        verbose=False,
    )[0]
    detections = []
    for box in result.boxes:
        source_class = result.names[int(box.cls.item())]
        class_name = LEGACY_MODEL_CLASSES.get(source_class, source_class)
        detection = {
            'clase': class_name,
            'confianza': round(float(box.conf.item()), 3),
            'xyxy': [round(value, 1) for value in box.xyxy[0].tolist()],
        }
        if class_name != source_class:
            detection['clase_origen'] = source_class
        material = material_for(class_name)
        if material:
            detection.update(material)
        detections.append(detection)
    return detections


def predict_openai_with_roboflow_fallback(image):
    provider_results = {}
    provider_times = {}
    provider_start = time.perf_counter()
    try:
        provider_results['openai'] = OPENAI.predict(image)
        provider_times['openai'] = round((time.perf_counter() - provider_start) * 1000)
        return 'openai', provider_results, provider_times
    except Exception as error:
        provider_times['openai'] = round((time.perf_counter() - provider_start) * 1000)
        print(f'OpenAI no disponible; se usará Roboflow: {error}', flush=True)

    provider_start = time.perf_counter()
    try:
        provider_results['roboflow'] = ROBOFLOW.predict(image)
        provider_times['roboflow'] = round((time.perf_counter() - provider_start) * 1000)
        return 'roboflow', provider_results, provider_times
    except Exception as error:
        provider_times['roboflow'] = round((time.perf_counter() - provider_start) * 1000)
        print(f'Roboflow tampoco está disponible: {error}', flush=True)
        raise RuntimeError('OpenAI y Roboflow no están disponibles') from error


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

    def authorized(self):
        return secrets.compare_digest(
            self.headers.get('Authorization', ''),
            'Bearer ' + TOKEN,
        )

    def content_length(self):
        try:
            return int(self.headers.get('Content-Length', '0'))
        except ValueError:
            return -1

    def do_GET(self):
        if self.path != '/api/salud':
            return self.reply(404, {'error': 'Ruta desconocida'})
        self.reply(200, {
            'estado': 'listo',
            'backend': INFERENCE_BACKEND,
            'modelo_local': MODEL_PATH.name if INFERENCE_BACKEND in ('local', 'comparar') else None,
            'modelo_openai': OPENAI_MODEL if INFERENCE_BACKEND == 'openai' else None,
            'modelo_roboflow': ROBOFLOW_MODEL_ID if INFERENCE_BACKEND != 'local' else None,
            'modo_modelo': 'recybot' if INFERENCE_BACKEND in ('openai', 'roboflow') else MODEL_MODE,
            'clasificacion_material': INFERENCE_BACKEND != 'local' or MODEL_MODE == 'recybot',
            'aprendizaje_activo': LEARNING_ENABLED,
        })

    def do_POST(self):
        if self.path not in ('/api/identificar', '/api/muestras/confirmar'):
            return self.reply(404, {'error': 'Ruta desconocida'})
        if not self.authorized():
            return self.reply(401, {'error': 'Acceso no autorizado'})
        if self.path == '/api/muestras/confirmar':
            return self.confirm_sample()
        return self.identify()

    def identify(self):
        length = self.content_length()
        if not 0 < length <= MAX_IMAGE:
            return self.reply(413, {'error': 'Imagen vacía o demasiado grande'})
        if self.headers.get('Content-Type') != 'image/jpeg':
            return self.reply(415, {'error': 'Se requiere JPEG'})
        if not LOCK.acquire(blocking=False):
            return self.reply(429, {'error': f'{DEVICE_LABEL} está procesando otra imagen'})
        try:
            temperature = Path('/sys/class/thermal/thermal_zone0/temp')
            if temperature.exists() and int(temperature.read_text()) >= 80000:
                return self.reply(503, {'error': 'Equipo caliente: esperar antes de reintentar'})
            raw = self.rfile.read(length)
            try:
                with Image.open(io.BytesIO(raw)) as source:
                    if source.width * source.height > 1920 * 1080:
                        return self.reply(413, {'error': 'Resolución demasiado grande'})
                    width, height = source.size
                    picture = source.convert('RGB')
            except (UnidentifiedImageError, OSError, ValueError):
                return self.reply(400, {'error': 'Imagen inválida'})

            start = time.perf_counter()
            provider_results = {}
            provider_times = {}
            if INFERENCE_BACKEND == 'openai':
                try:
                    primary_provider, provider_results, provider_times = (
                        predict_openai_with_roboflow_fallback(raw)
                    )
                except RuntimeError as error:
                    return self.reply(503, {'error': str(error)})
            if INFERENCE_BACKEND in ('local', 'comparar'):
                provider_start = time.perf_counter()
                provider_results['local'] = predict_local(picture)
                provider_times['local'] = round((time.perf_counter() - provider_start) * 1000)
            if INFERENCE_BACKEND in ('roboflow', 'comparar'):
                provider_start = time.perf_counter()
                try:
                    provider_results['roboflow'] = ROBOFLOW.predict(raw)
                    provider_times['roboflow'] = round((time.perf_counter() - provider_start) * 1000)
                except Exception as error:
                    print(f'Roboflow no disponible: {error}', flush=True)
                    if INFERENCE_BACKEND == 'roboflow':
                        return self.reply(503, {'error': str(error)})

            if INFERENCE_BACKEND != 'openai':
                primary_provider = (
                    'roboflow'
                    if 'roboflow' in provider_results and INFERENCE_BACKEND != 'local'
                    else 'local'
                )
            detections = provider_results[primary_provider]
            active_mode = 'recybot' if primary_provider in ('openai', 'roboflow') else MODEL_MODE

            sample_id = None
            if LEARNING_ENABLED:
                sample_id = SAMPLES.add_pending(
                    raw,
                    width,
                    height,
                    detections,
                    active_mode,
                )
            primary = next(
                (item for item in detections if item.get('categoria')),
                None,
            )
            self.reply(200, {
                'timestamp_utc': datetime.now(timezone.utc).isoformat(),
                'backend': primary_provider,
                'modelo': {
                    'openai': OPENAI_MODEL,
                    'roboflow': ROBOFLOW_MODEL_ID,
                    'local': MODEL_PATH.name,
                }[primary_provider],
                'modo_modelo': active_mode,
                'procesado_en': DEVICE_LABEL,
                'tiempo_ms': round((time.perf_counter() - start) * 1000),
                'tiempos_proveedores_ms': provider_times,
                'detecciones': detections,
                'categoria': primary['categoria'] if primary else None,
                'destino': primary['destino'] if primary else None,
                'requiere_confirmacion_material': True,
                'muestra_id': sample_id,
                'fallback_usado': INFERENCE_BACKEND == 'openai' and primary_provider == 'roboflow',
                'resultados_proveedores': provider_results if INFERENCE_BACKEND == 'comparar' else None,
            })
        except Exception:
            import traceback
            traceback.print_exc()
            self.reply(500, {'error': 'No se pudo procesar la imagen'})
        finally:
            LOCK.release()

    def confirm_sample(self):
        if not LEARNING_ENABLED:
            return self.reply(503, {'error': 'La recolección de muestras está desactivada'})
        length = self.content_length()
        if not 0 < length <= MAX_JSON:
            return self.reply(413, {'error': 'Confirmación vacía o demasiado grande'})
        content_type = self.headers.get('Content-Type', '').split(';', 1)[0]
        if content_type != 'application/json':
            return self.reply(415, {'error': 'Se requiere JSON'})
        try:
            payload = json.loads(self.rfile.read(length))
            sample_id = payload['muestra_id']
            class_name = payload['clase']
            if not isinstance(sample_id, str) or not isinstance(class_name, str):
                raise ValueError
            result = SAMPLES.confirm(sample_id, class_name)
        except SampleNotFoundError:
            return self.reply(404, {'error': 'La captura venció; realiza una nueva detección'})
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            return self.reply(400, {'error': 'Confirmación inválida'})
        except OSError:
            return self.reply(500, {'error': 'No se pudo guardar la muestra localmente'})
        self.reply(201, result)


if __name__ == '__main__':
    if MODEL_MODE not in ('prueba', 'recybot'):
        raise RuntimeError('RECYBOT_MODEL_MODE debe ser prueba o recybot')
    if not 0 < CONFIDENCE <= 1:
        raise RuntimeError('RECYBOT_CONFIDENCE debe estar entre 0 y 1')
    if INFERENCE_BACKEND not in ('local', 'openai', 'roboflow', 'comparar'):
        raise RuntimeError(
            'RECYBOT_INFERENCE_BACKEND debe ser local, openai, roboflow o comparar'
        )
    TOKEN = (BASE / 'config' / 'api-token').read_text().strip()
    if len(TOKEN) < 32:
        raise RuntimeError('Token de acceso inválido')
    if INFERENCE_BACKEND in ('local', 'comparar'):
        import torch
        from ultralytics import YOLO
        torch.set_num_threads(1)
        MODEL = YOLO(str(MODEL_PATH))
        MODEL.add_callback('on_predict_start', lambda predictor: torch.set_num_threads(1))
    if INFERENCE_BACKEND in ('roboflow', 'comparar'):
        ROBOFLOW = RoboflowProvider(ROBOFLOW_API_KEY_PATH, ROBOFLOW_MODEL_ID)
    if INFERENCE_BACKEND == 'openai':
        OPENAI = OpenAIProvider(OPENAI_API_KEY_PATH, OPENAI_MODEL)
        ROBOFLOW = RoboflowProvider(ROBOFLOW_API_KEY_PATH, ROBOFLOW_MODEL_ID)
    print(f'Recybot IA listo en puerto 8766 (backend {INFERENCE_BACKEND})', flush=True)
    ThreadingHTTPServer(('0.0.0.0', 8766), Handler).serve_forever()
