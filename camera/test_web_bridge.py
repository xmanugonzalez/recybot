"""Pruebas de configuración del puente sin cámara, red ni credenciales reales."""

import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import web_bridge


class WebBridgeTest(unittest.TestCase):
    test_root = Path(__file__).resolve().parent

    def test_reads_private_token_from_configured_path(self):
        with tempfile.TemporaryDirectory(dir=self.test_root) as directory:
            path = Path(directory) / 'api-token'
            path.write_text('a' * 32, encoding='utf-8')
            with patch.object(web_bridge, 'TOKEN_PATH', path):
                self.assertEqual(web_bridge.read_token(), 'a' * 32)

    def test_rejects_short_token(self):
        with tempfile.TemporaryDirectory(dir=self.test_root) as directory:
            path = Path(directory) / 'api-token'
            path.write_text('corto', encoding='utf-8')
            with patch.object(web_bridge, 'TOKEN_PATH', path):
                with self.assertRaisesRegex(RuntimeError, 'Token de acceso inválido'):
                    web_bridge.read_token()

    def test_reads_one_uploaded_jpeg(self):
        frame = b'jpeg-de-celular'
        headers = {'Content-Length': str(len(frame))}

        self.assertEqual(web_bridge.read_uploaded_frame(headers, BytesIO(frame)), frame)

    def test_rejects_oversized_uploaded_jpeg_before_reading(self):
        headers = {'Content-Length': str(web_bridge.MAX_FRAME_BYTES + 1)}

        with self.assertRaisesRegex(web_bridge.CaptureRequestError, 'demasiado grande') as error:
            web_bridge.read_uploaded_frame(headers, BytesIO())

        self.assertEqual(error.exception.status, 413)


if __name__ == '__main__':
    unittest.main()
