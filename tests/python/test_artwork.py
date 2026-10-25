"""Artwork source generators: deterministic RGBA pixels inside FrameRudiments."""
import hashlib
import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'integrations'/'framerudiments'))
from bytefables_framerudiments.artwork import ArtworkRenderer

ROOT={'bridge_version':'bytefables.framerudiments.layer.v1',
      'digest_hex':'17'*32,'palette':'neon','style':'sigil','complexity':4}

class ArtworkTests(unittest.TestCase):
    def test_four_generators_render_distinct_repeatable_pixels(self):
        seen=set()
        for family in ('sigil','constellation','heraldry','topography'):
            with self.subTest(family=family):
                opts={**ROOT,'style':family}
                a=ArtworkRenderer((128,128),opts).render(None)
                b=ArtworkRenderer((128,128),opts).render(None)
                self.assertEqual(a.tobytes(),b.tobytes())
                self.assertEqual(a.size,(128,128))
                self.assertEqual(a.mode,'RGBA')
                self.assertIsNotNone(a.getbbox())
                seen.add(hashlib.sha256(a.tobytes()).hexdigest())
        self.assertEqual(len(seen),4)

    def test_digest_palette_and_complexity_change_artwork(self):
        a=ArtworkRenderer((96,96),ROOT).render(None).tobytes()
        b=ArtworkRenderer((96,96),{**ROOT,'digest_hex':'18'*32}).render(None).tobytes()
        c=ArtworkRenderer((96,96),{**ROOT,'palette':'mono'}).render(None).tobytes()
        d=ArtworkRenderer((96,96),{**ROOT,'complexity':7}).render(None).tobytes()
        self.assertNotEqual(a,b)
        self.assertNotEqual(a,c)
        self.assertNotEqual(a,d)

    def test_safety_limits_and_input_validation(self):
        for opts in ({**ROOT,'digest_hex':'00'*31},{**ROOT,'complexity':0},
                     {**ROOT,'complexity':9},{**ROOT,'style':'script'},
                     {**ROOT,'palette':'invalid'},{**ROOT,'command':'rm -rf /'},
                     {**ROOT,'digest_hex':'g'*64}):
            with self.subTest(opts=opts):
                with self.assertRaises(ValueError): ArtworkRenderer((128,128),opts)
        with self.assertRaises(ValueError):ArtworkRenderer((4096,4096),ROOT)

    def test_small_icons_are_not_blank(self):
        for family in ('sigil','constellation','heraldry','topography'):
            a=ArtworkRenderer((32,32),{**ROOT,'style':family}).render(None)
            self.assertIsNotNone(a.getbbox())
