"""Pruebas del proveedor OpenAI sin realizar llamadas externas."""

import io
import json
import tempfile
import unittest
from os import environ
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.error import URLError

from openai_provider import DEFAULT_MODEL, OpenAIProvider


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


class OpenAIProviderTest(unittest.TestCase):
    test_root = Path(__file__).resolve().parent

    def create_provider(self, directory):
        key_path = Path(directory) / 'key'
        key_path.write_text('clave-openai-de-prueba', encoding='utf-8')
        return OpenAIProvider(key_path)

    def test_uses_luna_by_default(self):
        self.assertEqual(DEFAULT_MODEL, 'gpt-6-luna')

    def test_reads_api_key_from_environment(self):
        with patch.dict(environ, {'OPENAI_API_KEY': 'clave-desde-entorno'}):
            provider = OpenAIProvider(Path('archivo-que-no-existe'))
        self.assertEqual(provider.api_key, 'clave-desde-entorno')

    def test_sends_low_detail_image_and_maps_class(self):
        response = {
            'output': [{
                'type': 'message',
                'content': [{
                    'type': 'output_text',
                    'text': json.dumps({'clase': 'metal', 'confianza': 0.91}),
                }],
            }],
        }
        with tempfile.TemporaryDirectory(dir=self.test_root) as directory:
            provider = self.create_provider(directory)
            with patch('openai_provider.urlopen', return_value=FakeResponse(
                json.dumps(response).encode(),
            )) as request_mock:
                detections = provider.predict(b'imagen-jpeg')

        request = request_mock.call_args.args[0]
        payload = json.loads(request.data)
        image_input = payload['input'][0]['content'][1]
        self.assertEqual(payload['model'], 'gpt-6-luna')
        self.assertEqual(payload['reasoning'], {'effort': 'none'})
        self.assertFalse(payload['store'])
        self.assertEqual(image_input['detail'], 'low')
        self.assertTrue(image_input['image_url'].startswith('data:image/jpeg;base64,'))
        self.assertEqual(payload['text']['format']['type'], 'json_schema')
        self.assertEqual(
            payload['text']['format']['schema']['properties']['clase']['enum'],
            ['plastico', 'papel_carton', 'metal', 'otros', 'ninguno'],
        )
        self.assertEqual(request.get_header('Authorization'), 'Bearer clave-openai-de-prueba')
        self.assertEqual(detections[0]['clase'], 'metal')
        self.assertEqual(detections[0]['categoria'], 'Metal')
        self.assertNotIn('xyxy', detections[0])

    def test_none_returns_no_detections(self):
        response = {
            'output': [{
                'type': 'message',
                'content': [{
                    'type': 'output_text',
                    'text': json.dumps({'clase': 'ninguno', 'confianza': 0.8}),
                }],
            }],
        }
        with tempfile.TemporaryDirectory(dir=self.test_root) as directory:
            provider = self.create_provider(directory)
            with patch('openai_provider.urlopen', return_value=FakeResponse(
                json.dumps(response).encode(),
            )):
                self.assertEqual(provider.predict(b'imagen-jpeg'), [])

    def test_rejects_invalid_response(self):
        with tempfile.TemporaryDirectory(dir=self.test_root) as directory:
            provider = self.create_provider(directory)
            with patch('openai_provider.urlopen', return_value=FakeResponse(b'{}')):
                with self.assertRaisesRegex(RuntimeError, 'no devolvió una clasificación'):
                    provider.predict(b'imagen-jpeg')

    def test_does_not_retry_connection_errors(self):
        with tempfile.TemporaryDirectory(dir=self.test_root) as directory:
            provider = self.create_provider(directory)
            with patch('openai_provider.urlopen', side_effect=URLError('sin red')) as request_mock:
                with self.assertRaisesRegex(RuntimeError, 'conectar con OpenAI'):
                    provider.predict(b'imagen-jpeg')
        self.assertEqual(request_mock.call_count, 1)

    def test_falls_back_to_roboflow_only_when_openai_fails(self):
        import server

        openai = Mock()
        openai.predict.side_effect = RuntimeError('sin OpenAI')
        roboflow = Mock()
        roboflow.predict.return_value = [{'clase': 'otros'}]
        with patch.object(server, 'OPENAI', openai), patch.object(server, 'ROBOFLOW', roboflow):
            provider, results, _ = server.predict_openai_with_roboflow_fallback(b'imagen')
        self.assertEqual(provider, 'roboflow')
        self.assertEqual(results['roboflow'][0]['clase'], 'otros')
        roboflow.predict.assert_called_once_with(b'imagen')

    def test_does_not_call_roboflow_after_valid_openai_result(self):
        import server

        openai = Mock()
        openai.predict.return_value = []
        roboflow = Mock()
        with patch.object(server, 'OPENAI', openai), patch.object(server, 'ROBOFLOW', roboflow):
            provider, results, _ = server.predict_openai_with_roboflow_fallback(b'imagen')
        self.assertEqual(provider, 'openai')
        self.assertEqual(results['openai'], [])
        roboflow.predict.assert_not_called()

    def test_reports_when_both_providers_fail(self):
        import server

        openai = Mock()
        openai.predict.side_effect = RuntimeError('sin OpenAI')
        roboflow = Mock()
        roboflow.predict.side_effect = RuntimeError('sin Roboflow')
        with patch.object(server, 'OPENAI', openai), patch.object(server, 'ROBOFLOW', roboflow):
            with self.assertRaisesRegex(
                RuntimeError,
                'OpenAI y Roboflow no están disponibles',
            ):
                server.predict_openai_with_roboflow_fallback(b'imagen')


if __name__ == '__main__':
    unittest.main()
