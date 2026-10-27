"""Sincroniza muestras confirmadas con Roboflow sin borrar la copia local."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree

from roboflow import Roboflow

PROJECT_ROOT = Path(__file__).resolve().parents[1]
AI_ROOT = PROJECT_ROOT / 'ai'
LEGACY_CLASSES = {'papel': 'papel_carton', 'carton': 'papel_carton'}


def normalized_class(metadata: dict) -> str:
    class_name = metadata['clase_confirmada']
    return LEGACY_CLASSES.get(class_name, class_name)


def write_voc(metadata: dict, image: Path, destination: Path) -> None:
    x1, y1, x2, y2 = (round(float(value)) for value in metadata['caja_xyxy'])
    annotation = ElementTree.Element('annotation')
    ElementTree.SubElement(annotation, 'filename').text = image.name
    size = ElementTree.SubElement(annotation, 'size')
    ElementTree.SubElement(size, 'width').text = str(metadata['ancho'])
    ElementTree.SubElement(size, 'height').text = str(metadata['alto'])
    ElementTree.SubElement(size, 'depth').text = '3'
    item = ElementTree.SubElement(annotation, 'object')
    ElementTree.SubElement(item, 'name').text = normalized_class(metadata)
    ElementTree.SubElement(item, 'pose').text = 'Unspecified'
    ElementTree.SubElement(item, 'truncated').text = '0'
    ElementTree.SubElement(item, 'difficult').text = '0'
    box = ElementTree.SubElement(item, 'bndbox')
    ElementTree.SubElement(box, 'xmin').text = str(x1)
    ElementTree.SubElement(box, 'ymin').text = str(y1)
    ElementTree.SubElement(box, 'xmax').text = str(x2)
    ElementTree.SubElement(box, 'ymax').text = str(y2)
    destination.parent.mkdir(parents=True, exist_ok=True)
    ElementTree.ElementTree(annotation).write(destination, encoding='utf-8', xml_declaration=True)


def has_person(metadata: dict) -> bool:
    return any(
        detection.get('clase') == 'person'
        for detection in metadata.get('detecciones_originales', [])
    )


def save_metadata(path: Path, metadata: dict) -> None:
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)


def candidates(learning_dir: Path) -> list[tuple[Path, dict]]:
    metadata_dir = learning_dir / 'inbox' / 'metadata'
    result = []
    for path in sorted(metadata_dir.glob('*.json')) if metadata_dir.exists() else []:
        metadata = json.loads(path.read_text(encoding='utf-8'))
        if metadata.get('roboflow', {}).get('sincronizada'):
            continue
        if not metadata.get('caja_xyxy') or has_person(metadata):
            continue
        result.append((path, metadata))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--learning-dir', type=Path, default=AI_ROOT / 'datos_aprendizaje')
    parser.add_argument('--api-key-path', type=Path, default=AI_ROOT / 'config' / 'roboflow-api-key')
    parser.add_argument('--workspace', default='ai-vision-lab-be6pb')
    parser.add_argument('--project', default='recybot-ai-7jhnn')
    parser.add_argument('--limit', type=int, default=25)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    pending = candidates(args.learning_dir)[:args.limit]
    if args.dry_run:
        print(json.dumps({'pendientes_para_subir': len(pending)}, ensure_ascii=False))
        return
    if not pending:
        print('No hay muestras confirmadas con caja pendientes de sincronización.')
        return

    key = args.api_key_path.read_text(encoding='utf-8').strip()
    project = Roboflow(api_key=key).workspace(args.workspace).project(args.project)
    uploaded = 0
    for metadata_path, metadata in pending:
        sample_id = metadata['id']
        image = args.learning_dir / 'inbox' / 'images' / f'{sample_id}.jpg'
        if not image.exists():
            continue
        annotation = args.learning_dir / 'outbox' / 'annotations' / f'{sample_id}.xml'
        write_voc(metadata, image, annotation)
        result = project.upload(
            image_path=str(image),
            annotation_path=str(annotation),
            split='train',
            batch_name='recybot-confirmadas',
            tag_names=['recybot', 'confirmada', normalized_class(metadata)],
            is_prediction=True,
            metadata={
                'recybot_sample_id': sample_id,
                'box_source': metadata.get('caja_origen', 'sin_caja'),
                'model_source': metadata.get('modo_modelo_origen', 'desconocido'),
            },
            num_retry_uploads=2,
        )
        metadata['roboflow'] = {
            'sincronizada': True,
            'sincronizada_utc': datetime.now(timezone.utc).isoformat(),
            'workspace': args.workspace,
            'project': args.project,
            'respuesta_recibida': bool(result),
        }
        save_metadata(metadata_path, metadata)
        uploaded += 1
    print(json.dumps({'sincronizadas': uploaded}, ensure_ascii=False))


if __name__ == '__main__':
    main()
