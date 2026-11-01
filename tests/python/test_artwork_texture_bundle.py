"""Lossless texture packing contracts. Synthetic fixtures are not native-host evidence."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'integrations' / 'framerudiments'))
from bytefables_framerudiments.texture_atlas import (
    layout, extrude, encode_page, decode_page, verify_page, TextureAtlasError,
)
from tools.artwork_texture_bundle import (
    export_texture_bundle, verify_texture_bundle, validate_manifest,
    AssetBundleError, sprite_key, _json, _sha,
)
from tools.artwork_asset_bundle import export_asset_bundle
from test_artwork_image_assets import write_test_evidence


class TexturePixels(unittest.TestCase):
    def test_1000_slots_are_bounded_nonoverlapping_and_uvs_are_exact(self):
        plan = layout(1000, 64, 1024, 2)
        self.assertEqual(plan['pageCount'], 5)
        occupied = set()
        for slot in plan['slots']:
            p = slot['pageIndex']; x, y, r, b = slot['rect']
            self.assertEqual((r-x,b-y), (64,64))
            self.assertTrue(2 <= x < r <= 1022 and 2 <= y < b <= 1022)
            self.assertNotIn((p,x,y), occupied); occupied.add((p,x,y))
            self.assertEqual(slot['uvTopLeft'], [x/1024,y/1024,r/1024,b/1024])
            self.assertEqual(slot['uvBottomLeft'], [x/1024,1-b/1024,r/1024,1-y/1024])

    def test_numeric_geometry_and_resource_boundaries(self):
        for args in [(0,16), (8193,16), (True,16), (1,17), (1,16,100), (1,64,64),
                     (1,16,64,0), (1,16,8192), (8192,128,4096)]:
            with self.subTest(args=args), self.assertRaises(TextureAtlasError): layout(*args)

    def test_extrusion_preserves_every_edge_corner_and_interior(self):
        with Image.new('RGBA',(16,16)) as tile:
            for y in range(16):
                for x in range(16): tile.putpixel((x,y),(x*13,y*11,x+y,255))
            with extrude(tile,3) as padded:
                self.assertEqual(padded.size,(22,22))
                for y in range(22):
                    for x in range(22):
                        self.assertEqual(padded.getpixel((x,y)),tile.getpixel((min(15,max(0,x-3)),min(15,max(0,y-3)))))

    def test_png_decode_rejects_truncation_crc_and_trailing_bytes(self):
        with Image.new('RGBA',(64,64),(1,2,3,255)) as im:
            data=encode_page(im)
            with decode_page(data,64) as decoded: self.assertEqual(decoded.tobytes(),im.tobytes())
        changed=bytearray(data);changed[35]^=1
        for bad in [bytes(changed),data[:-1],data+b'\0']:
            with self.assertRaises((TextureAtlasError,OSError)): decode_page(bad,64)
        with self.assertRaises(TextureAtlasError): decode_page(data,128)

    def test_zero_rgb_in_transparent_unused_area_is_checked(self):
        with Image.new('RGBA',(64,64)) as image:
            image.putpixel((63,63),(44,0,0,0))
            with self.assertRaisesRegex(TextureAtlasError,'unused'): verify_page(image,[],2)


class TextureBundle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.root=Path(cls.temp.name)
        suite,benchmark=write_test_evidence(cls.root/'evidence',sizes=(16,32),count=10)
        cls.source=cls.root/'assets'
        export_asset_bundle(suite,benchmark,cls.source,confirm_public=True,formats=('png',))

    @classmethod
    def tearDownClass(cls): cls.temp.cleanup()

    def setUp(self):
        self.temp_out=tempfile.TemporaryDirectory();self.out=Path(self.temp_out.name)/'texture'
    def tearDown(self):self.temp_out.cleanup()
    def export(self,**kwargs):
        return export_texture_bundle(self.source,self.out,confirm_public=True,native_size=16,page_size=64,**kwargs)
    def write_manifest(self,m): (self.out/'manifest.json').write_bytes(_json(m))

    def test_real_roundtrip_pagination_and_source_comparison(self):
        manifest=self.export()
        self.assertEqual(len(manifest['pages']),2)
        self.assertEqual(manifest['spriteCount'],10)
        self.assertFalse(verify_texture_bundle(self.out)['sourceCompared'])
        checked=verify_texture_bundle(self.out,source_bundle=self.source)
        self.assertTrue(checked['decodedPixelsVerified'] and checked['guttersVerified'] and checked['sourceCompared'])

    def test_reproducible_bytes_and_sprite_keys_survive_repacking(self):
        first=self.export()
        other=self.out.parent/'other'
        second=export_texture_bundle(self.source,other,confirm_public=True,native_size=16,page_size=64)
        self.assertEqual(first,second)
        self.assertEqual((self.out/'pages/page-000.png').read_bytes(),(other/'pages/page-000.png').read_bytes())
        packed=export_texture_bundle(self.source,self.out.parent/'larger',confirm_public=True,native_size=16,page_size=128,padding=4)
        self.assertEqual([s['spriteKey'] for s in first['sprites']],[s['spriteKey'] for s in packed['sprites']])

    def test_no_consent_no_overwrite_and_no_source_child_output(self):
        with self.assertRaisesRegex(AssetBundleError,'confirm-public'): export_texture_bundle(self.source,self.out)
        self.assertFalse(self.out.exists())
        self.export()
        with self.assertRaisesRegex(AssetBundleError,'new directory'): self.export()
        with self.assertRaisesRegex(AssetBundleError,'outside'): export_texture_bundle(self.source,self.source/'nested',confirm_public=True)

    def test_missing_native_size_is_not_resampled(self):
        with self.assertRaisesRegex(AssetBundleError,'missing'): export_texture_bundle(self.source,self.out,confirm_public=True,native_size=128)
        self.assertFalse(self.out.exists())

    def test_invalid_manifest_identity_uv_and_bounds(self):
        original=self.export()
        for change in [lambda m:m['sprites'][0].update(rect=[0,0,16,16]),
                       lambda m:m['sprites'][0].update(uvTopLeft=[0,0,1,1]),
                       lambda m:m['sprites'][0].update(digestHex='f'*64),
                       lambda m:m['sprites'][0].update(pageIndex=True),
                       lambda m:m.update(sampling={**m['sampling'],'mipmaps':True}),
                       lambda m:m['pages'][0].update(file='../outside.png'),
                       lambda m:m.update(spriteCount=9000000),
                       lambda m:m['sprites'].reverse()]:
            m=copy.deepcopy(original);change(m)
            with self.assertRaises((AssetBundleError,TextureAtlasError)):validate_manifest(m)

    def test_duplicate_identity_rejected_even_with_recomputed_key(self):
        m=self.export();a,b=m['sprites'][:2]
        for k in ('digestHex','family','palette','complexity','sourceFile'):b[k]=a[k]
        b['spriteKey']=sprite_key(b)
        with self.assertRaisesRegex(AssetBundleError,'Duplicate'):validate_manifest(m)

    def test_page_byte_tampering_fails(self):
        self.export();p=self.out/'pages/page-000.png';p.write_bytes(p.read_bytes()+b'x')
        with self.assertRaisesRegex(AssetBundleError,'checksum'):verify_texture_bundle(self.out)

    def test_gutter_tampering_fails_even_after_rehashing_page(self):
        m=self.export();page=m['pages'][0];p=self.out/page['file']
        with decode_page(p.read_bytes(),64) as image:
            image.putpixel((0,0),(255,0,255,255));data=encode_page(image)
            page['rgbaSha256']=_sha(image.tobytes())
        p.write_bytes(data);page.update(sha256=_sha(data),byteLength=len(data));self.write_manifest(m)
        with self.assertRaisesRegex(TextureAtlasError,'gutter'):verify_texture_bundle(self.out)

    def test_viewer_extra_files_and_manifest_source_pin(self):
        m=self.export()
        p=self.out/'runtime.js';saved=p.read_bytes();p.write_bytes(saved+b'\n')
        with self.assertRaisesRegex(AssetBundleError,'Viewer'):verify_texture_bundle(self.out)
        p.write_bytes(saved);(self.out/'stray.txt').write_text('unexpected')
        with self.assertRaisesRegex(AssetBundleError,'Unexpected'):verify_texture_bundle(self.out)
        (self.out/'stray.txt').unlink();m['sourceManifestSha256']='0'*64;self.write_manifest(m)
        with self.assertRaisesRegex(AssetBundleError,'Source manifest'):verify_texture_bundle(self.out,source_bundle=self.source)

    def test_failed_export_never_leaves_success_marker(self):
        with patch('tools.artwork_texture_bundle.encode_page',side_effect=TextureAtlasError('test fault')):
            with self.assertRaises(TextureAtlasError):self.export()
        self.assertFalse((self.out/'manifest.json').exists());self.assertTrue((self.out/'failure.json').exists())
        with self.assertRaisesRegex(AssetBundleError,'failed'):verify_texture_bundle(self.out)

    def test_symlink_pages_are_rejected(self):
        self.export();p=self.out/'pages/page-000.png';data=p.read_bytes();p.unlink()
        target=self.out.parent/'outside.png';target.write_bytes(data)
        try:p.symlink_to(target)
        except OSError:self.skipTest('Symlink creation unavailable')
        with self.assertRaisesRegex(AssetBundleError,'Symlink'):verify_texture_bundle(self.out)

    def test_cli_returns_nonzero_for_invalid_size_and_success_for_real_images(self):
        script=str(ROOT/'scripts/export-artwork-textures.py')
        run=subprocess.run([sys.executable,script,'--confirm-public','export','--bundle',str(self.source),
            '--output',str(self.out),'--native-size','16','--page-size','64'],capture_output=True,text=True)
        self.assertEqual(run.returncode,0,run.stderr);self.assertEqual(json.loads(run.stdout)['sprites'],10)
        run=subprocess.run([sys.executable,script,'--confirm-public','verify','--bundle',str(self.out),
                            '--source-bundle',str(self.source)],capture_output=True,text=True)
        self.assertEqual(run.returncode,0,run.stderr);self.assertTrue(json.loads(run.stdout)['sourceCompared'])
        bad=subprocess.run([sys.executable,script,'--confirm-public','export','--bundle',str(self.source),
            '--output',str(self.out.parent/'invalid'),'--native-size','17'],capture_output=True,text=True)
        self.assertNotEqual(bad.returncode,0)


if __name__=='__main__':unittest.main()
