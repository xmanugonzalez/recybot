"""Pruebas del servidor de cámara sin abrir hardware real."""

import threading
import time
import unittest
from unittest.mock import MagicMock, patch

import camera_server
from camera_server import (
    FuenteOpenCV,
    FuentePicamera2,
    SalidaDeVideo,
    corregir_orientacion,
    crear_fuente,
)


class CameraServerTest(unittest.TestCase):
    def test_selects_both_supported_backends_lazily(self):
        output = SalidaDeVideo()
        self.assertIsInstance(crear_fuente('opencv', output), FuenteOpenCV)
        self.assertIsInstance(crear_fuente('picamera2', output), FuentePicamera2)

    def test_rejects_unknown_backend(self):
        with self.assertRaisesRegex(RuntimeError, 'opencv o picamera2'):
            crear_fuente('desconocido', SalidaDeVideo())

    def test_waits_for_exactly_one_new_frame(self):
        output = SalidaDeVideo()

        def publish():
            time.sleep(0.02)
            output.write(b'jpeg')

        thread = threading.Thread(target=publish)
        thread.start()
        new, image, sequence = output.esperar_imagen_nueva(0, timeout=1)
        thread.join()

        self.assertTrue(new)
        self.assertEqual(image, b'jpeg')
        self.assertEqual(sequence, 1)

    def test_horizontal_flip_is_configurable(self):
        cv2 = MagicMock()
        cv2.flip.return_value = 'corregida'
        with patch.object(camera_server, 'CAMERA_FLIP_HORIZONTAL', True):
            image = corregir_orientacion('original', cv2)
        self.assertEqual(image, 'corregida')
        cv2.flip.assert_called_once_with('original', 1)


if __name__ == '__main__':
    unittest.main()
