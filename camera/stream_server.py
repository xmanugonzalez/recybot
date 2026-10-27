#!/usr/bin/python3

"""Serve the Raspberry Pi camera as a local MJPEG stream."""

import io
import json
import logging
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from camera_server import main as unified_main


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


salida = SalidaDeVideo()


class ManejadorCamara(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/api/camara/frame':
            with salida.condicion:
                previa = salida.secuencia
                nueva = salida.condicion.wait_for(lambda: salida.secuencia > previa, timeout=5)
                imagen = salida.imagen
            if not nueva or imagen is None:
                self.send_error(503, 'No llega una imagen nueva de la camara')
                return
            self.send_response(200)
            self.send_header('Content-Type', 'image/jpeg')
            self.send_header('Content-Length', str(len(imagen)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(imagen)
            return

        if self.path == '/api/camara/status':
            contenido = json.dumps(
                {
                    'estado': 'activa',
                    'ancho': 640,
                    'alto': 480,
                }
            ).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(contenido)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(contenido)
            return

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
                with salida.condicion:
                    salida.condicion.wait_for(
                        lambda: salida.secuencia != ultima_secuencia,
                        timeout=5,
                    )

                    if salida.secuencia == ultima_secuencia:
                        continue

                    imagen = salida.imagen
                    ultima_secuencia = salida.secuencia

                self.wfile.write(b'--FRAME\r\n')
                self.wfile.write(b'Content-Type: image/jpeg\r\n')
                self.wfile.write(f'Content-Length: {len(imagen)}\r\n\r\n'.encode())
                self.wfile.write(imagen)
                self.wfile.write(b'\r\n')
        except (BrokenPipeError, ConnectionResetError, TimeoutError):
            pass
        except OSError:
            pass

    def log_message(self, formato, *argumentos):
        logging.info('%s - %s', self.address_string(), formato % argumentos)


def main():
    from picamera2 import Picamera2
    from picamera2.encoders import MJPEGEncoder
    from picamera2.outputs import FileOutput

    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    camara = Picamera2()
    configuracion = camara.create_video_configuration(
        main={'size': (640, 480)},
        controls={'FrameRate': 15},
    )
    camara.configure(configuracion)
    camara.start_recording(MJPEGEncoder(), FileOutput(salida))

    servidor = ThreadingHTTPServer(('127.0.0.1', 8765), ManejadorCamara)
    servidor.daemon_threads = True

    logging.info('Cámara activa en http://127.0.0.1:8765/api/camara/stream')

    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        servidor.server_close()
        camara.stop_recording()
        camara.close()


if __name__ == '__main__':
    unified_main()
