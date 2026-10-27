"""Entrena y promueve un modelo solo cuando existen muestras nuevas suficientes."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from build_dataset import build


def ready_samples(learning_dir: Path) -> int:
    metadata_dir = learning_dir / 'inbox' / 'metadata'
    if not metadata_dir.exists():
        return 0
    total = 0
    for path in metadata_dir.glob('*.json'):
        try:
            metadata = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError):
            continue
        if metadata.get('caja_xyxy'):
            total += 1
    return total


def read_status(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return {}


def write_status(path: Path, status: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)


def metric(model_path: Path, data: Path) -> float:
    from ultralytics import YOLO

    metrics = YOLO(str(model_path)).val(data=str(data), split='test')
    return float(metrics.box.map)


def deploy(candidate: Path, destination: Path, version: str) -> Path | None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    backup = None
    if destination.exists():
        backup = destination.with_name(f'{destination.stem}.backup-{version}{destination.suffix}')
        shutil.copy2(destination, backup)
    temporary = destination.with_suffix('.tmp')
    shutil.copy2(candidate, temporary)
    temporary.replace(destination)
    return backup


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--public-data', type=Path, required=True)
    parser.add_argument('--learning-dir', type=Path, required=True)
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--base-model', type=Path, default=Path('yolov8n.pt'))
    parser.add_argument('--current-model', type=Path)
    parser.add_argument('--deploy-path', type=Path)
    parser.add_argument('--min-confirmed', type=int, default=100)
    parser.add_argument('--min-map', type=float, default=0.35)
    parser.add_argument('--min-improvement', type=float, default=0.005)
    parser.add_argument('--epochs', type=int, default=100)
    parser.add_argument('--patience', type=int, default=20)
    parser.add_argument('--imgsz', type=int, default=640)
    args = parser.parse_args()

    count = ready_samples(args.learning_dir)
    status_path = args.workspace / 'status.json'
    previous = read_status(status_path)
    previous_count = int(previous.get('muestras_procesadas', 0))
    if count < args.min_confirmed:
        print(f'Sin entrenamiento: {count}/{args.min_confirmed} muestras listas.')
        return
    if count <= previous_count:
        print('Sin entrenamiento: no hay nuevas muestras confirmadas.')
        return

    version = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    dataset_dir = args.workspace / 'data' / f'version-{count}-{version}'
    summary = build(args.public_data, args.learning_dir, dataset_dir)
    if summary['imagenes_publicas'] == 0:
        raise RuntimeError('El dataset público no aportó imágenes compatibles')

    from ultralytics import YOLO

    run_name = f'candidate-{count}-{version}'
    YOLO(str(args.base_model)).train(
        data=str(dataset_dir / 'data.yaml'),
        epochs=args.epochs,
        patience=args.patience,
        imgsz=args.imgsz,
        project=str(args.workspace / 'runs'),
        name=run_name,
        exist_ok=False,
        pretrained=True,
    )
    candidate = args.workspace / 'runs' / run_name / 'weights' / 'best.pt'
    candidate_map = metric(candidate, dataset_dir / 'data.yaml')

    baseline_map = None
    if args.current_model and args.current_model.exists():
        try:
            baseline_map = metric(args.current_model, dataset_dir / 'data.yaml')
        except Exception as error:
            print(f'El modelo vigente no es comparable con estas clases: {error}')

    promoted = (
        candidate_map >= args.min_map
        if baseline_map is None
        else candidate_map >= baseline_map + args.min_improvement
    )
    backup = None
    if promoted and args.deploy_path:
        backup = deploy(candidate, args.deploy_path, version)

    write_status(status_path, {
        'ultima_ejecucion_utc': datetime.now(timezone.utc).isoformat(),
        'muestras_procesadas': count,
        'dataset': str(dataset_dir),
        'candidato': str(candidate),
        'map_50_95_candidato': candidate_map,
        'map_50_95_anterior': baseline_map,
        'promovido': promoted,
        'desplegado_en': str(args.deploy_path) if promoted and args.deploy_path else None,
        'respaldo': str(backup) if backup else None,
    })
    print(
        f'Candidato mAP50-95={candidate_map:.4f}; '
        f'{"promovido" if promoted else "rechazado"}.'
    )


if __name__ == '__main__':
    main()
