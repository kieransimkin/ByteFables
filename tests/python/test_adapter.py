"""Synthetic public-only generator tests; host compositor acceptance is separate."""
import hashlib
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'integrations' / 'framerudiments'))

from bytefables_framerudiments import register_bytefables_renderers
from bytefables_framerudiments.renderers import (
    PixelRenderer, MatrixRenderer, VectorSceneRenderer, BRIDGE_VERSION
)


class FakeRegistry:
    def __init__(self):
        self.factories = {}

    def register(self, name, factory):
        if name in self.factories:
            raise ValueError('duplicate')
        self.factories[name] = factory


class TestByteFablesFrameRudiments(unittest.TestCase):
    def test_native_registration_contract_and_deterministic_identity(self):
        registry = register_bytefables_renderers(FakeRegistry())
        self.assertEqual(set(registry.factories), {
            'bytefables-pixel-v1', 'bytefables-matrix-v1', 'bytefables-scene-v1',
            'bytefables-fractal-v1'
        })
        self.assertRaises(ValueError, register_bytefables_renderers, registry)
        options = { 'bridge_version': BRIDGE_VERSION, 'palette': 'neon',
                    'digest_hex': '00' * 32 }
        renderer = PixelRenderer((128, 96), options)
        a, b = renderer.render(None), renderer.render(None)
        self.assertEqual(a.size, (128, 96))
        self.assertEqual(a.mode, 'RGBA')
        self.assertEqual(a.tobytes(), b.tobytes())
        self.assertGreater(a.getbbox()[2], 0)
        self.assertNotEqual(a.tobytes(), PixelRenderer((128, 96), {
            **options, 'digest_hex': '10' * 32
        }).render(None).tobytes())
        self.assertRaises(ValueError, PixelRenderer, (128,128), {
            **options, 'digest_hex':'00' * 31 })
        self.assertRaises(ValueError, PixelRenderer, (128,128), {
            **options, 'new_effect':'glow' })
        self.assertEqual(hashlib.sha256(a.tobytes()).hexdigest(),
            '72b397f8a7343990e8a894a04a7ff35ad94a5a96bfb9a78b53c68df99e960b81')

    def test_public_matrix_is_exacted_pixels_and_has_blank_quiet_zone(self):
        spec = {'bridge_version': BRIDGE_VERSION, 'format_id':'test/matrix',
            'width':3, 'height':2, 'quiet_zone':2, 'modules':'101010'}
        img = MatrixRenderer((70, 60), spec).render(None)
        self.assertEqual(img.size, (70, 60))
        self.assertEqual(img.getpixel((0,0)), (255,255,255,255))
        self.assertEqual(img.getpixel((23,22)), (0,0,0,255))
        self.assertEqual(img.getpixel((33,22)), (255,255,255,255))
        for bad in ['10101x', '0000000', '1010']:
            self.assertRaises(ValueError, MatrixRenderer, (70,60), {**spec,'modules':bad})
        self.assertRaises(ValueError, MatrixRenderer, (1,1), spec)
        self.assertRaises(ValueError, MatrixRenderer, (70,60), {**spec,'format_id':'../bad'})

    def test_scene_primitives_and_closed_path(self):
        spec = {'bridge_version': BRIDGE_VERSION,
            'scene': {'width': 100, 'height': 100, 'primitives': [
                {'kind': 'rect', 'x':0,'y':0,'width':10,'height':10,'fill':'#ff0000'},
                {'kind': 'circle','cx':50,'cy':50,'radius':10,'fill':'#00ff00'},
                {'kind': 'line','x1':0,'y1':99,'x2':99,'y2':99,
                 'strokeWidth':1,'stroke':'#0000ff'},
                {'kind': 'path','d':'M20 20L30 20L30 30L20 30Z', 'fill':'#abcdef'}
            ]}}
        image = VectorSceneRenderer((100,100),spec).render(None)
        self.assertEqual(image.getpixel((5,5)), (255,0,0,255))
        self.assertEqual(image.getpixel((50,50)), (0,255,0,255))
        self.assertEqual(image.getpixel((25,25)), (171,205,239,255))
        self.assertEqual(image.getpixel((99,99)), (0,0,255,255))
        invalid = json.loads(json.dumps(spec))
        invalid['scene']['primitives'][3]['d'] = 'M1 2L3 4'
        self.assertRaises(ValueError, VectorSceneRenderer((100,100),invalid).render, None)
        invalid['scene']['primitives'][3]['d'] = 'M1 2L3 4<script>'
        self.assertRaises(ValueError, VectorSceneRenderer, (100,100),invalid)


class TestCrossLanguageFixture(unittest.TestCase):
    def test_typescript_fragment_fixture_loads_in_framerudiments_factories(self):
        fixture = json.loads((Path(__file__).resolve().parents[1] /
            'vectors' / 'framerudiments-v1.json').read_text())
        registry = register_bytefables_renderers(FakeRegistry()).factories
        for name, size in [('identity',(128,128)), ('matrix',(70,60)), ('scene',(100,100))]:
            layer = fixture[name]
            self.assertEqual(layer['type'], 'rudiment')
            self.assertEqual(layer['bounds'][2]-layer['bounds'][0], size[0])
            self.assertEqual(layer['bounds'][3]-layer['bounds'][1], size[1])
            renderer = registry[layer['renderer']](size, layer['style'])
            image = renderer.render(None)
            self.assertEqual(image.mode, 'RGBA')
            self.assertEqual(image.size, size)


if __name__ == '__main__':
    unittest.main()
