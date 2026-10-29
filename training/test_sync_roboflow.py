"""Pruebas de preparación para sincronización, sin llamadas externas."""

import json
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree

from sync_roboflow import candidates, write_voc


class SyncRoboflowTest(unittest.TestCase):
    def setUp(self):
        (Path.cwd() / 'tmp').mkdir(exist_ok=True)

    def test_creates_voc_annotation_with_recybot_class(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd() / 'tmp') as temporary:
            root = Path(temporary)
            image = root / 'sample.jpg'
            image.write_bytes(b'image')
            annotation = root / 'sample.xml'
            write_voc({
                'clase_confirmada': 'plastico',
                'ancho': 640,
                'alto': 480,
                'caja_xyxy': [10, 20, 300, 400],
            }, image, annotation)
            parsed = ElementTree.parse(annotation)
            self.assertEqual(parsed.findtext('object/name'), 'plastico')
            self.assertEqual(parsed.findtext('object/bndbox/xmax'), '300')

    def test_merges_legacy_paper_and_cardboard_annotations(self):
        for legacy_class in ('papel', 'carton'):
            with self.subTest(legacy_class=legacy_class):
                with tempfile.TemporaryDirectory(dir=Path.cwd() / 'tmp') as temporary:
                    root = Path(temporary)
                    image = root / 'sample.jpg'
                    image.write_bytes(b'image')
                    annotation = root / 'sample.xml'
                    write_voc({
                        'clase_confirmada': legacy_class,
                        'caja_xyxy': [1, 2, 30, 40],
                        'ancho': 100,
                        'alto': 100,
                    }, image, annotation)
                    parsed = ElementTree.parse(annotation)
                    self.assertEqual(parsed.findtext('object/name'), 'papel_carton')

    def test_excludes_people_and_already_synced_samples(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd() / 'tmp') as temporary:
            root = Path(temporary)
            metadata_dir = root / 'inbox' / 'metadata'
            metadata_dir.mkdir(parents=True)
            samples = {
                'ready': {'id': 'ready', 'caja_xyxy': [1, 1, 2, 2]},
                'person': {
                    'id': 'person',
                    'caja_xyxy': [1, 1, 2, 2],
                    'detecciones_originales': [{'clase': 'person'}],
                },
                'synced': {
                    'id': 'synced',
                    'caja_xyxy': [1, 1, 2, 2],
                    'roboflow': {'sincronizada': True},
                },
            }
            for name, metadata in samples.items():
                (metadata_dir / f'{name}.json').write_text(json.dumps(metadata), encoding='utf-8')
            self.assertEqual([metadata['id'] for _, metadata in candidates(root)], ['ready'])


if __name__ == '__main__':
    unittest.main()
