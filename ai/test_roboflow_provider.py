"""Pruebas que no realizan llamadas externas ni exponen la API key."""

import base64
import io
import json
import tempfile
import unittest
from os import environ
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError
from urllib.parse import parse_qs, urlparse

from roboflow_provider import CLASS_MAPPING, DEFAULT_MODEL_ID, RoboflowProvider


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


class RoboflowProviderTest(unittest.TestCase):
    test_root = Path(__file__).resolve().parent

    def test_public_model_is_pinned(self):
        self.assertEqual(DEFAULT_MODEL_ID, 'ee4016/3')

    def test_reads_api_key_from_environment(self):
        with patch.dict(environ, {'ROBOFLOW_API_KEY': 'clave-desde-entorno'}):
            provider = RoboflowProvider(Path('archivo-que-no-existe'))
        self.assertEqual(provider.api_key, 'clave-desde-entorno')

    def test_maps_public_classes_to_recybot(self):
        self.assertEqual(CLASS_MAPPING, {
            'plastic': 'botella_plastico',
            'glass': 'botella_vidrio',
            'metal': 'lata',
            'paper': 'papel_carton',
            'cardboard': 'papel_carton',
        })

    def test_merges_paper_and_cardboard(self):
        self.assertEqual(CLASS_MAPPING['paper'], 'papel_carton')
        self.assertEqual(CLASS_MAPPING['cardboard'], 'papel_carton')

    def create_provider(self, directory):
        key_path = Path(directory) / 'key'
        key_path.write_text('clave-privada-de-prueba', encoding='utf-8')
        return RoboflowProvider(key_path)

    def test_sends_one_request_without_active_learning(self):
        payload = {
            'predictions': [{
                'class': 'plastic',
                'confidence': 0.87,
                'x': 50,
                'y': 60,
                'width': 40,
                'height': 20,
            }],
        }
        with tempfile.TemporaryDirectory(dir=self.test_root) as directory:
            provider = self.create_provider(directory)
            with patch('roboflow_provider.urlopen', return_value=FakeResponse(
                json.dumps(payload).encode(),
            )) as request_mock:
                detections = provider.predict(b'imagen-jpeg')

        self.assertEqual(request_mock.call_count, 1)
        request = request_mock.call_args.args[0]
        query = parse_qs(urlparse(request.full_url).query)
        self.assertEqual(query['disable_active_learning'], ['true'])
        self.assertEqual(query['api_key'], ['clave-privada-de-prueba'])
        self.assertIsNone(request.get_header('Authorization'))
        self.assertEqual(request.get_header('Content-type'), 'application/x-www-form-urlencoded')
        self.assertEqual(request.data, base64.b64encode(b'imagen-jpeg'))
        self.assertEqual(detections[0]['clase'], 'botella_plastico')

    def test_does_not_retry_connection_errors(self):
        with tempfile.TemporaryDirectory(dir=self.test_root) as directory:
            provider = self.create_provider(directory)
            with patch('roboflow_provider.urlopen', side_effect=URLError('sin red')) as request_mock:
                with self.assertRaisesRegex(RuntimeError, 'conectar con Roboflow'):
                    provider.predict(b'imagen-jpeg')
        self.assertEqual(request_mock.call_count, 1)


if __name__ == '__main__':
    unittest.main()
