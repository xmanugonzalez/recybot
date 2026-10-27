"""Run on Pi 5 with its venv; verifies actual HTTP behavior and CPU inference."""
import io
import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from PIL import Image

token = (Path(__file__).resolve().parent / 'config/api-token').read_text().strip()


def send(data, expected, authorized=True):
    headers = {'Content-Type': 'image/jpeg'}
    if authorized:
        headers['Authorization'] = 'Bearer ' + token
    req = Request('http://127.0.0.1:8766/api/identificar', data=data, headers=headers)
    try:
        response = urlopen(req, timeout=45)
    except HTTPError as error:
        response = error
    with response:
        assert response.status == expected, (response.status, expected)
        return json.load(response)


send(b'invalid', 401, authorized=False)
send(b'invalid', 400)
send(b'', 413)
picture = io.BytesIO()
Image.new('RGB', (320, 320), 'black').save(picture, format='JPEG')
result = send(picture.getvalue(), 200)
assert result['categoria'] is None
assert result['requiere_confirmacion_material'] is True
assert result['detecciones'] == []
print('OK: autenticación, JPEG inválido, captura vacía e inferencia sin falsas categorías.')
