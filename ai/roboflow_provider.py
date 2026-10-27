"""Proveedor de inferencia alojada de Roboflow para el arranque de Recybot."""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from learning import CLASES_RECYBOT

DEFAULT_API_URL = 'https://serverless.roboflow.com'
DEFAULT_MODEL_ID = 'ee4016/3'
CLASS_MAPPING = {
    'plastic': 'botella_plastico',
    'glass': 'botella_vidrio',
    'metal': 'lata',
    'paper': 'papel_carton',
    'cardboard': 'papel_carton',
}


def read_api_key(path: Path) -> str:
    environment_key = os.environ.get('ROBOFLOW_API_KEY', '').strip()
    if environment_key:
        return environment_key
    key = path.read_text(encoding='utf-8').strip()
    if not key or key == 'PEGA_AQUI_TU_PRIVATE_API_KEY':
        raise RuntimeError('Falta configurar la Private API Key de Roboflow')
    return key


class RoboflowProvider:
    def __init__(self, api_key_path: Path, model_id: str = DEFAULT_MODEL_ID):
        self.model_id = model_id
        self.api_key = read_api_key(api_key_path)
        parts = model_id.split('/')
        if len(parts) != 2 or not all(parts):
            raise ValueError('ROBOFLOW_MODEL_ID debe usar el formato proyecto/version')
        project, version = (quote(part, safe='-_') for part in parts)
        query = urlencode({
            'api_key': self.api_key,
            'disable_active_learning': 'true',
        })
        self.url = f'{DEFAULT_API_URL}/{project}/{version}?{query}'

    def predict(self, image: bytes) -> list[dict[str, Any]]:
        request = Request(
            self.url,
            data=base64.b64encode(image),
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            method='POST',
        )
        try:
            with urlopen(request, timeout=45) as response:
                result = json.load(response)
        except HTTPError as error:
            raise RuntimeError(f'Roboflow rechazó la imagen ({error.code})') from error
        except (OSError, URLError, TimeoutError) as error:
            raise RuntimeError('No se pudo conectar con Roboflow') from error
        predictions = result.get('predictions', []) if isinstance(result, dict) else []
        detections = []
        for prediction in predictions:
            source_class = str(prediction.get('class', '')).lower().strip()
            class_name = CLASS_MAPPING.get(source_class)
            x = float(prediction['x'])
            y = float(prediction['y'])
            width = float(prediction['width'])
            height = float(prediction['height'])
            detection = {
                'clase': class_name or source_class,
                'clase_origen': source_class,
                'confianza': round(float(prediction['confidence']), 3),
                'xyxy': [
                    round(x - width / 2, 1),
                    round(y - height / 2, 1),
                    round(x + width / 2, 1),
                    round(y + height / 2, 1),
                ],
            }
            if class_name:
                detection.update(CLASES_RECYBOT[class_name])
            else:
                detection['requiere_revision'] = True
            detections.append(detection)
        return detections
