"""Clasificación visual alojada en OpenAI para Recybot."""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from learning import CLASES_RECYBOT

DEFAULT_API_URL = 'https://api.openai.com/v1/responses'
DEFAULT_MODEL = 'gpt-6-luna'
VALID_CLASSES = (*CLASES_RECYBOT.keys(), 'ninguno')
PROMPT = '''Clasifica el residuo principal de la fotografía.
Usa plastico para residuos plásticos, papel_carton para papel o cartón, metal para
residuos metálicos y otros para cualquier otro residuo, incluidos vidrio y orgánicos.
Usa ninguno solo si no hay un residuo claro o la imagen no permite clasificarlo.
No deduzcas el material solo por la forma sin evidencia visual suficiente.'''


def read_api_key(path: Path) -> str:
    environment_key = os.environ.get('OPENAI_API_KEY', '').strip()
    if environment_key:
        return environment_key
    try:
        key = path.read_text(encoding='utf-8').strip()
    except OSError as error:
        raise RuntimeError('Falta configurar la API key de OpenAI') from error
    if not key or key == 'PEGA_AQUI_TU_OPENAI_API_KEY':
        raise RuntimeError('Falta configurar la API key de OpenAI')
    return key


class OpenAIProvider:
    def __init__(
        self,
        api_key_path: Path,
        model: str = DEFAULT_MODEL,
        api_url: str = DEFAULT_API_URL,
    ):
        self.model = model
        self.api_key = read_api_key(api_key_path)
        self.api_url = api_url

    def predict(self, image: bytes) -> list[dict[str, Any]]:
        payload = {
            'model': self.model,
            'store': False,
            'reasoning': {'effort': 'none'},
            'max_output_tokens': 80,
            'input': [{
                'role': 'user',
                'content': [
                    {'type': 'input_text', 'text': PROMPT},
                    {
                        'type': 'input_image',
                        'image_url': (
                            'data:image/jpeg;base64,'
                            + base64.b64encode(image).decode('ascii')
                        ),
                        'detail': 'low',
                    },
                ],
            }],
            'text': {
                'format': {
                    'type': 'json_schema',
                    'name': 'clasificacion_residuo',
                    'strict': True,
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'clase': {'type': 'string', 'enum': list(VALID_CLASSES)},
                            'confianza': {'type': 'number', 'minimum': 0, 'maximum': 1},
                        },
                        'required': ['clase', 'confianza'],
                        'additionalProperties': False,
                    },
                },
            },
        }
        request = Request(
            self.api_url,
            data=json.dumps(payload).encode(),
            headers={
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json',
            },
            method='POST',
        )
        try:
            with urlopen(request, timeout=45) as response:
                result = json.load(response)
        except HTTPError as error:
            raise RuntimeError(f'OpenAI rechazó la imagen ({error.code})') from error
        except (OSError, URLError, TimeoutError) as error:
            raise RuntimeError('No se pudo conectar con OpenAI') from error

        classification = self._parse_classification(result)
        class_name = classification['clase']
        if class_name == 'ninguno':
            return []
        return [{
            'clase': class_name,
            'clase_origen': class_name,
            'confianza': round(float(classification['confianza']), 3),
            'requiere_revision': True,
            **CLASES_RECYBOT[class_name],
        }]

    @staticmethod
    def _parse_classification(result: Any) -> dict[str, Any]:
        if not isinstance(result, dict):
            raise RuntimeError('OpenAI devolvió una respuesta inválida')
        for output in result.get('output', []):
            if not isinstance(output, dict) or output.get('type') != 'message':
                continue
            for content in output.get('content', []):
                if not isinstance(content, dict) or content.get('type') != 'output_text':
                    continue
                try:
                    classification = json.loads(content['text'])
                    class_name = classification['clase']
                    confidence = float(classification['confianza'])
                except (json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
                    raise RuntimeError('OpenAI devolvió una clasificación inválida') from error
                if class_name not in VALID_CLASSES or not 0 <= confidence <= 1:
                    raise RuntimeError('OpenAI devolvió una clasificación inválida')
                return {'clase': class_name, 'confianza': confidence}
        raise RuntimeError('OpenAI no devolvió una clasificación')
