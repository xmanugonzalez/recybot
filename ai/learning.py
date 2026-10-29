"""Almacenamiento seguro de muestras confirmadas para aprendizaje activo."""

from __future__ import annotations

import json
import secrets
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CLASES_RECYBOT = {
    'plastico': {'categoria': 'Plástico', 'destino': 'plastico'},
    'papel_carton': {'categoria': 'Papel / Cartón', 'destino': 'papel_carton'},
    'metal': {'categoria': 'Metal', 'destino': 'metal'},
    'otros': {'categoria': 'Otros', 'destino': 'otros'},
}
GENERIC_BOX_CLASSES = {'bottle', 'wine glass', 'cup', 'bowl', 'book'}


@dataclass(frozen=True)
class PendingSample:
    image: bytes
    width: int
    height: int
    detections: list[dict[str, Any]]
    model_mode: str
    created_at: float


class SampleNotFoundError(KeyError):
    """La muestra no existe o ya venció."""


class ActiveLearningStore:
    def __init__(self, root: Path, ttl_seconds: int = 1800, max_pending: int = 20):
        self.root = root
        self.ttl_seconds = ttl_seconds
        self.max_pending = max_pending
        self._pending: dict[str, PendingSample] = {}
        self._lock = threading.Lock()

    def add_pending(
        self,
        image: bytes,
        width: int,
        height: int,
        detections: list[dict[str, Any]],
        model_mode: str,
    ) -> str:
        now = time.time()
        with self._lock:
            self._discard_expired(now)
            while len(self._pending) >= self.max_pending:
                oldest = min(self._pending, key=lambda key: self._pending[key].created_at)
                self._pending.pop(oldest)
            sample_id = secrets.token_urlsafe(18)
            self._pending[sample_id] = PendingSample(
                image=image,
                width=width,
                height=height,
                detections=detections,
                model_mode=model_mode,
                created_at=now,
            )
        return sample_id

    def confirm(self, sample_id: str, class_name: str) -> dict[str, Any]:
        if class_name not in CLASES_RECYBOT:
            raise ValueError('Clase de residuo desconocida')

        now = time.time()
        with self._lock:
            self._discard_expired(now)
            sample = self._pending.pop(sample_id, None)
        if sample is None:
            raise SampleNotFoundError(sample_id)

        candidate = self._best_box(sample)
        confirmed_at = datetime.now(timezone.utc).isoformat()
        metadata = {
            'id': sample_id,
            'clase_confirmada': class_name,
            **CLASES_RECYBOT[class_name],
            'ancho': sample.width,
            'alto': sample.height,
            'caja_xyxy': candidate['xyxy'] if candidate else None,
            'caja_origen': 'deteccion_modelo' if candidate else None,
            'requiere_revisar_caja': candidate is None,
            'detecciones_originales': sample.detections,
            'modo_modelo_origen': sample.model_mode,
            'confirmado_utc': confirmed_at,
        }

        images = self.root / 'inbox' / 'images'
        labels = self.root / 'inbox' / 'metadata'
        images.mkdir(parents=True, exist_ok=True)
        labels.mkdir(parents=True, exist_ok=True)
        image_path = images / f'{sample_id}.jpg'
        metadata_path = labels / f'{sample_id}.json'
        image_temporary = image_path.with_suffix('.tmp')
        metadata_temporary = metadata_path.with_suffix('.tmp')
        try:
            image_temporary.write_bytes(sample.image)
            metadata_temporary.write_text(
                json.dumps(metadata, ensure_ascii=False, indent=2),
                encoding='utf-8',
            )
            image_temporary.replace(image_path)
            metadata_temporary.replace(metadata_path)
        except OSError:
            with self._lock:
                self._pending.setdefault(sample_id, sample)
            raise

        return {
            'muestra_id': sample_id,
            'guardada': True,
            'requiere_revisar_caja': metadata['requiere_revisar_caja'],
        }

    def _discard_expired(self, now: float) -> None:
        expired = [
            key for key, sample in self._pending.items()
            if now - sample.created_at > self.ttl_seconds
        ]
        for key in expired:
            self._pending.pop(key, None)

    @staticmethod
    def _best_box(sample: PendingSample) -> dict[str, Any] | None:
        valid = []
        for detection in sample.detections:
            class_name = detection.get('clase')
            if sample.model_mode == 'prueba' and class_name not in GENERIC_BOX_CLASSES:
                continue
            if sample.model_mode == 'recybot' and class_name not in CLASES_RECYBOT:
                continue
            box = detection.get('xyxy')
            if not isinstance(box, list) or len(box) != 4:
                continue
            x1, y1, x2, y2 = (float(value) for value in box)
            if 0 <= x1 < x2 <= sample.width and 0 <= y1 < y2 <= sample.height:
                valid.append(detection)
        return max(valid, key=lambda item: float(item.get('confianza', 0)), default=None)
