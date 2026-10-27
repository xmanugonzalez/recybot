#!/usr/bin/python3

"""Sirve una cámara OpenCV o Picamera2 como MJPEG y fotogramas JPEG."""

import io
import json
import logging
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


CAMERA_BACKEND = os.environ.get('RECYBOT_CAMERA_BACKEND', 'picamera2').lower()
CAMERA_INDEX = int(os.environ.get('RECYBOT_CAMERA_INDEX', '0'))
CAMERA_WIDTH = int(os.environ.get('RECYBOT_CAMERA_WIDTH', '640'))
CAMERA_HEIGHT = int(os.environ.get('RECYBOT_CAMERA_HEIGHT', '480'))
CAMERA_FPS = int(os.environ.get('RECYBOT_CAMERA_FPS', '15'))
CAMERA_FLIP_HORIZONTAL = os.environ.get(
    'RECYBOT_CAMERA_FLIP_HORIZONTAL',
    'false',
).lower() == 'true'


def corregir_orientacion(imagen, cv2):
    return cv2.flip(imagen, 1) if CAMERA_FLIP_HORIZONTAL else imagen


class SalidaDeVideo(io.BufferedIOBase):
    def __init__(self):
        self.condicion = threading.Condition()
        self.imagen = None
        self.secuencia = 0

    def write(self, imagen):
        with self.condicion:
            self.imagen = bytes(imagen)
            self.secuencia += 1
            self.condicion.notify_all()
        return len(imagen)

    def esperar_imagen_nueva(self, secuencia_previa, timeout=5):
        with self.condicion:
            nueva = self.condicion.wait_for(
                lambda: self.secuencia > secuencia_previa,
                timeout=timeout,
            )
            return nueva, self.imagen, self.secuencia


class FuentePicamera2:
    nombre = 'picamera2'

    def __init__(self, salida):
        self.salida = salida
        self.camara = None

    def iniciar(self):
        from picamera2 import Picamera2
        from picamera2.encoders import MJPEGEncoder
        from picamera2.outputs import FileOutput

        self.camara = Picamera2()
        opciones = {
            'main': {'size': (CAMERA_WIDTH, CAMERA_HEIGHT)},
            'controls': {'FrameRate': CAMERA_FPS},
        }
        if CAMERA_FLIP_HORIZONTAL:
            from libcamera import Transform
            opciones['transform'] = Transform(hflip=True)
        configuracion = self.camara.create_video_configuration(
            **opciones,
        )
        self.camara.configure(configuracion)
        self.camara.start_recording(MJPEGEncoder(), FileOutput(self.salida))

    def detener(self):
        if self.camara is not None:
            self.camara.stop_recording()
            self.camara.close()


class FuenteOpenCV:
    nombre = 'opencv'

    def __init__(self, salida):
        self.salida = salida
        self.captura = None
        self.hilo = None
        self.detener_evento = threading.Event()
        self.error = ''

    def iniciar(self):
        import cv2

        backends = [cv2.CAP_ANY]
        if os.name == 'nt':
            backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]
        for backend in backends:
            captura = cv2.VideoCapture(CAMERA_INDEX, backend)
            if captura.isOpened():
                self.captura = captura
                break
            captura.release()
        if self.captura is None:
            raise RuntimeError(f'No se pudo abrir la webcam con índice {CAMERA_INDEX}')
        self.captura.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
        self.captura.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
        self.captura.set(cv2.CAP_PROP_FPS, CAMERA_FPS)
        self.hilo = threading.Thread(target=self._capturar, daemon=True)
        self.hilo.start()

    def _capturar(self):
        import cv2

        while not self.detener_evento.is_set():
            disponible, imagen = self.captura.read()
            if not disponible:
                self.error = 'La webcam dejó de entregar imágenes'
                time.sleep(0.1)
                continue
            imagen = corregir_orientacion(imagen, cv2)
            codificada, jpeg = cv2.imencode('.jpg', imagen, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if not codificada:
                self.error = 'No se pudo codificar el fotograma de la webcam'
                continue
            self.error = ''
            self.salida.write(jpeg.tobytes())

    def detener(self):
        self.detener_evento.set()
        if self.captura is not None:
            self.captura.release()
        if self.hilo is not None:
            self.hilo.join(timeout=2)


def crear_fuente(nombre, salida):
    if nombre == 'opencv':
        return FuenteOpenCV(salida)
    if nombre == 'picamera2':
        return FuentePicamera2(salida)
    raise RuntimeError('RECYBOT_CAMERA_BACKEND debe ser opencv o picamera2')


salida = SalidaDeVideo()
fuente = crear_fuente(CAMERA_BACKEND, salida)


class ManejadorCamara(BaseHTTPRequestHandler):
    def enviar_json(self, estado, datos):
        contenido = json.dumps(datos, ensure_ascii=False).encode()
        self.send_response(estado)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(contenido)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(contenido)

    def do_GET(self):
        if self.path == '/api/camara/frame':
            nueva, imagen, _ = salida.esperar_imagen_nueva(salida.secuencia, timeout=5)
            if not nueva or imagen is None:
                self.send_error(503, 'No llega una imagen nueva de la cámara')
                return
            self.send_response(200)
            self.send_header('Content-Type', 'image/jpeg')
            self.send_header('Content-Length', str(len(imagen)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(imagen)
            return

        if self.path == '/api/camara/status':
            error = getattr(fuente, 'error', '')
            return self.enviar_json(200 if not error else 503, {
                'estado': 'activa' if not error else 'error',
                'backend': fuente.nombre,
                'indice': CAMERA_INDEX if fuente.nombre == 'opencv' else None,
                'ancho': CAMERA_WIDTH,
                'alto': CAMERA_HEIGHT,
                'volteo_horizontal': CAMERA_FLIP_HORIZONTAL,
                'error': error or None,
            })

        if self.path != '/api/camara/stream':
            self.send_error(404)
            return

        self.send_response(200)
        self.send_header('Age', '0')
        self.send_header('Cache-Control', 'no-cache, private')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
        self.end_headers()
        ultima_secuencia = -1

        try:
            while True:
                nueva, imagen, ultima = salida.esperar_imagen_nueva(ultima_secuencia, timeout=5)
                if not nueva or imagen is None:
                    continue
                ultima_secuencia = ultima
                self.wfile.write(b'--FRAME\r\n')
                self.wfile.write(b'Content-Type: image/jpeg\r\n')
                self.wfile.write(f'Content-Length: {len(imagen)}\r\n\r\n'.encode())
                self.wfile.write(imagen)
                self.wfile.write(b'\r\n')
        except (BrokenPipeError, ConnectionResetError, TimeoutError, OSError):
            pass

    def log_message(self, formato, *argumentos):
        logging.info('%s - %s', self.address_string(), formato % argumentos)


def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    fuente.iniciar()
    servidor = ThreadingHTTPServer(('127.0.0.1', 8765), ManejadorCamara)
    servidor.daemon_threads = True
    logging.info('Cámara %s activa en http://127.0.0.1:8765/api/camara/stream', fuente.nombre)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        servidor.server_close()
        fuente.detener()


if __name__ == '__main__':
    main()
