"""Comprueba credenciales y modelo sin mostrar secretos."""

import argparse
import json
from pathlib import Path

from roboflow_provider import DEFAULT_MODEL_ID, RoboflowProvider

BASE = Path(__file__).resolve().parent


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('image', type=Path)
    args = parser.parse_args()
    provider = RoboflowProvider(BASE / 'config' / 'roboflow-api-key')
    detections = provider.predict(args.image.read_bytes())
    print(json.dumps({
        'estado': 'conectado',
        'modelo': DEFAULT_MODEL_ID,
        'detecciones': [
            {
                'clase': detection['clase'],
                'confianza': detection['confianza'],
            }
            for detection in detections
        ],
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
