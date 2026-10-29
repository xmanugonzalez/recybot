"""Combina un dataset YOLO público con muestras confirmadas de Recybot."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import unicodedata
from pathlib import Path

import yaml

CLASSES = ['plastico', 'papel_carton', 'metal', 'otros']
ALIASES = {
    'plastic': 'plastico',
    'plastico': 'plastico',
    'plastic bottle': 'plastico',
    'botella plastico': 'plastico',
    'botella_plastico': 'plastico',
    'paper': 'papel_carton',
    'papel': 'papel_carton',
    'cardboard': 'papel_carton',
    'carton': 'papel_carton',
    'papel carton': 'papel_carton',
    'papel_carton': 'papel_carton',
    'metal': 'metal',
    'can': 'metal',
    'lata': 'metal',
    'glass': 'otros',
    'vidrio': 'otros',
    'glass bottle': 'otros',
    'botella vidrio': 'otros',
    'botella_vidrio': 'otros',
    'organic': 'otros',
    'organico': 'otros',
    'food waste': 'otros',
    'otros': 'otros',
}
IMAGE_SUFFIXES = {'.jpg', '.jpeg', '.png', '.webp'}


def normalized(value: str) -> str:
    plain = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode()
    return ' '.join(plain.lower().replace('-', ' ').replace('_', ' ').split())


def class_names(config: dict) -> list[str]:
    names = config.get('names', [])
    if isinstance(names, dict):
        return [str(names[index]) for index in sorted(names, key=lambda item: int(item))]
    return [str(name) for name in names]


def image_paths(root: Path, value) -> list[Path]:
    values = value if isinstance(value, list) else [value]
    found: list[Path] = []
    for entry in values:
        path = Path(entry)
        path = path if path.is_absolute() else root / path
        if path.is_dir():
            found.extend(
                file for file in path.rglob('*')
                if file.is_file() and file.suffix.lower() in IMAGE_SUFFIXES
            )
        elif path.suffix == '.txt' and path.exists():
            for line in path.read_text(encoding='utf-8').splitlines():
                image = Path(line.strip())
                found.append(image if image.is_absolute() else root / image)
    return sorted(found)


def label_path(image: Path) -> Path:
    parts = list(image.parts)
    for index in range(len(parts) - 1, -1, -1):
        if parts[index] == 'images':
            parts[index] = 'labels'
            return Path(*parts).with_suffix('.txt')
    return image.with_suffix('.txt')


def target_paths(output: Path, split: str, prefix: str, image: Path) -> tuple[Path, Path]:
    digest = hashlib.sha256(str(image).encode()).hexdigest()[:10]
    stem = f'{prefix}_{digest}_{image.stem}'
    return (
        output / split / 'images' / f'{stem}{image.suffix.lower()}',
        output / split / 'labels' / f'{stem}.txt',
    )


def copy_public(config_path: Path, output: Path) -> int:
    config = yaml.safe_load(config_path.read_text(encoding='utf-8'))
    root_setting = Path(config.get('path', config_path.parent))
    root = root_setting if root_setting.is_absolute() else config_path.parent / root_setting
    names = class_names(config)
    mapping = {
        index: CLASSES.index(ALIASES[normalized(name)])
        for index, name in enumerate(names)
        if normalized(name) in ALIASES
    }
    copied = 0
    for split in ('train', 'val', 'test'):
        if split not in config:
            continue
        for image in image_paths(root, config[split]):
            source_label = label_path(image)
            if not image.exists() or not source_label.exists():
                continue
            converted = []
            compatible = True
            for line in source_label.read_text(encoding='utf-8').splitlines():
                values = line.split()
                if len(values) != 5:
                    compatible = False
                    break
                source_index = int(values[0])
                if source_index not in mapping:
                    compatible = False
                    break
                converted.append(' '.join([str(mapping[source_index]), *values[1:]]))
            if not compatible:
                continue
            target_image, target_label = target_paths(output, split, 'public', image)
            target_image.parent.mkdir(parents=True, exist_ok=True)
            target_label.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(image, target_image)
            target_label.write_text('\n'.join(converted) + ('\n' if converted else ''), encoding='utf-8')
            copied += 1
    return copied


def local_split(sample_id: str) -> str:
    bucket = int(hashlib.sha256(sample_id.encode()).hexdigest(), 16) % 10
    if bucket == 0:
        return 'test'
    if bucket <= 2:
        return 'val'
    return 'train'


def copy_confirmed(learning_dir: Path, output: Path) -> tuple[int, int]:
    copied = 0
    pending_box = 0
    metadata_dir = learning_dir / 'inbox' / 'metadata'
    for metadata_path in sorted(metadata_dir.glob('*.json')) if metadata_dir.exists() else []:
        metadata = json.loads(metadata_path.read_text(encoding='utf-8'))
        box = metadata.get('caja_xyxy')
        if not isinstance(box, list) or len(box) != 4:
            pending_box += 1
            continue
        class_name = ALIASES.get(normalized(str(metadata.get('clase_confirmada', ''))))
        if class_name not in CLASSES:
            continue
        width, height = float(metadata['ancho']), float(metadata['alto'])
        x1, y1, x2, y2 = (float(value) for value in box)
        center_x = ((x1 + x2) / 2) / width
        center_y = ((y1 + y2) / 2) / height
        box_width = (x2 - x1) / width
        box_height = (y2 - y1) / height
        if not all(0 <= value <= 1 for value in (center_x, center_y, box_width, box_height)):
            pending_box += 1
            continue
        sample_id = metadata['id']
        image = learning_dir / 'inbox' / 'images' / f'{sample_id}.jpg'
        if not image.exists():
            continue
        split = local_split(sample_id)
        target_image, target_label = target_paths(output, split, 'local', image)
        target_image.parent.mkdir(parents=True, exist_ok=True)
        target_label.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(image, target_image)
        target_label.write_text(
            f'{CLASSES.index(class_name)} {center_x:.6f} {center_y:.6f} '
            f'{box_width:.6f} {box_height:.6f}\n',
            encoding='utf-8',
        )
        copied += 1
    return copied, pending_box


def build(public_data: Path, learning_dir: Path, output: Path) -> dict[str, int]:
    if output.exists() and any(output.iterdir()):
        raise RuntimeError(f'La carpeta de salida debe estar vacía: {output}')
    public_count = copy_public(public_data, output)
    local_count, pending_box = copy_confirmed(learning_dir, output)
    dataset = {
        'path': str(output.resolve()),
        'train': 'train/images',
        'val': 'val/images',
        'test': 'test/images',
        'names': dict(enumerate(CLASSES)),
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / 'data.yaml').write_text(
        yaml.safe_dump(dataset, allow_unicode=True, sort_keys=False),
        encoding='utf-8',
    )
    summary = {
        'imagenes_publicas': public_count,
        'muestras_locales': local_count,
        'pendientes_de_caja': pending_box,
    }
    (output / 'resumen.json').write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--public-data', type=Path, required=True)
    parser.add_argument('--learning-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.public_data, args.learning_dir, args.output), ensure_ascii=False))


if __name__ == '__main__':
    main()
