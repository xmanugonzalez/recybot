"""Pruebas del ensamblado del dataset YOLO."""

import json
import tempfile
import unittest
from pathlib import Path

import yaml

from build_dataset import ALIASES, CLASSES, build, normalized


class BuildDatasetTest(unittest.TestCase):
    def test_merges_public_and_legacy_paper_classes(self):
        for name in ('paper', 'cardboard', 'papel', 'carton', 'papel_carton'):
            with self.subTest(name=name):
                self.assertEqual(ALIASES[normalized(name)], 'papel_carton')

    def test_combines_public_and_confirmed_samples(self):
        temporary_root = Path.cwd() / 'tmp'
        temporary_root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=temporary_root) as temporary:
            root = Path(temporary)
            public = root / 'public'
            for split in ('train', 'val', 'test'):
                (public / split / 'images').mkdir(parents=True)
                (public / split / 'labels').mkdir(parents=True)
                (public / split / 'images' / f'{split}.jpg').write_bytes(b'image')
                (public / split / 'labels' / f'{split}.txt').write_text(
                    '0 0.5 0.5 0.4 0.4\n', encoding='utf-8'
                )
            public_config = {
                'path': str(public),
                'train': 'train/images',
                'val': 'val/images',
                'test': 'test/images',
                'names': ['plastic', 'glass', 'metal', 'paper', 'cardboard'],
            }
            public_yaml = public / 'data.yaml'
            public_yaml.write_text(yaml.safe_dump(public_config), encoding='utf-8')

            learning = root / 'learning' / 'inbox'
            (learning / 'images').mkdir(parents=True)
            (learning / 'metadata').mkdir(parents=True)
            (learning / 'images' / 'sample.jpg').write_bytes(b'local-image')
            (learning / 'metadata' / 'sample.json').write_text(json.dumps({
                'id': 'sample',
                'clase_confirmada': 'botella_vidrio',
                'ancho': 640,
                'alto': 480,
                'caja_xyxy': [64, 48, 320, 240],
            }), encoding='utf-8')

            output = root / 'combined'
            summary = build(public_yaml, root / 'learning', output)

            self.assertEqual(summary['imagenes_publicas'], 3)
            self.assertEqual(summary['muestras_locales'], 1)
            generated = yaml.safe_load((output / 'data.yaml').read_text(encoding='utf-8'))
            self.assertEqual(list(generated['names'].values()), CLASSES)
            local_labels = list(output.glob('*/labels/local_*.txt'))
            self.assertEqual(len(local_labels), 1)
            self.assertTrue(local_labels[0].read_text(encoding='utf-8').startswith('1 '))


if __name__ == '__main__':
    unittest.main()
