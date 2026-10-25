"""Optional smoke against the REAL FrameRudiments registry if already installed.

No fake native render claim when the FrameRudiments runtime is absent.
"""
from importlib.util import find_spec
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'integrations' / 'framerudiments'))
from bytefables_framerudiments import register_bytefables_renderers


@unittest.skipUnless(find_spec('framerudiments'), 'FrameRudiments host not installed')
class NativeHostSmoke(unittest.TestCase):
    def test_real_registry_can_create_public_generator(self):
        from framerudiments import default_renderers
        registry = register_bytefables_renderers(default_renderers())
        renderer, identity = registry.create('bytefables-pixel-v1', (64,64), {
            'bridge_version': 'bytefables.framerudiments.layer.v1',
            'digest_hex': '00' * 32, 'palette': 'neon'
        })
        self.assertEqual(renderer.render(None).mode, 'RGBA')
        self.assertEqual(identity['name'], 'bytefables-pixel-v1')
        self.assertIn('source', identity)
