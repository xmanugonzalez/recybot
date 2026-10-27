"""Pruebas unitarias del almacenamiento de aprendizaje activo."""

import json
import tempfile
import unittest
from pathlib import Path

from learning import ActiveLearningStore, SampleNotFoundError


class ActiveLearningStoreTest(unittest.TestCase):
    def setUp(self):
        temporary_root = Path.cwd() / 'tmp'
        temporary_root.mkdir(exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=temporary_root)
        self.root = Path(self.temporary.name)
        self.store = ActiveLearningStore(self.root)

    def tearDown(self):
        self.temporary.cleanup()

    def test_confirm_saves_image_label_and_best_box(self):
        sample_id = self.store.add_pending(
            b'jpeg-test',
            640,
            480,
            [
                {'clase': 'cup', 'confianza': 0.41, 'xyxy': [1, 2, 30, 40]},
                {'clase': 'bottle', 'confianza': 0.91, 'xyxy': [10, 20, 300, 420]},
            ],
            'prueba',
        )

        result = self.store.confirm(sample_id, 'botella_vidrio')

        self.assertTrue(result['guardada'])
        self.assertFalse(result['requiere_revisar_caja'])
        metadata = json.loads(
            (self.root / 'inbox' / 'metadata' / f'{sample_id}.json').read_text(encoding='utf-8')
        )
        self.assertEqual(metadata['clase_confirmada'], 'botella_vidrio')
        self.assertEqual(metadata['destino'], 'vidrio')
        self.assertEqual(metadata['caja_xyxy'], [10, 20, 300, 420])
        self.assertEqual(
            (self.root / 'inbox' / 'images' / f'{sample_id}.jpg').read_bytes(),
            b'jpeg-test',
        )

    def test_without_detection_requires_box_review(self):
        sample_id = self.store.add_pending(b'jpeg-test', 320, 320, [], 'prueba')
        result = self.store.confirm(sample_id, 'papel_carton')
        self.assertTrue(result['requiere_revisar_caja'])

    def test_sample_can_only_be_confirmed_once(self):
        sample_id = self.store.add_pending(b'jpeg-test', 320, 320, [], 'prueba')
        self.store.confirm(sample_id, 'papel_carton')
        with self.assertRaises(SampleNotFoundError):
            self.store.confirm(sample_id, 'papel_carton')

    def test_rejects_unknown_class(self):
        sample_id = self.store.add_pending(b'jpeg-test', 320, 320, [], 'prueba')
        with self.assertRaises(ValueError):
            self.store.confirm(sample_id, 'organico')


if __name__ == '__main__':
    unittest.main()
