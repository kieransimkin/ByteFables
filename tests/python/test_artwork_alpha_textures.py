"""Independent mip arithmetic, hostile bundle inputs and verified-source packaging.

Native drawing is not mocked as a production result: the small source bundles
below come from explicitly synthetic test evidence, as in existing export tests.
"""
from __future__ import annotations
import copy
import json
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT)); sys.path.insert(0,str(ROOT/'integrations/framerudiments'))
from bytefables_framerudiments.alpha_mips import mip_chain, validate_premultiplied, PROFILE
from tools.artwork_alpha_textures import export_alpha_textures, verify_alpha_textures, validate_manifest, key_for
from tools.artwork_asset_bundle import AssetBundleError
from tools.artwork_native_benchmark import _json, _sha
from test_artwork_transparent_bundle import export as transparent_fixture


def independent_mip(image, level):
    # Deliberately use direct original-pixel area summation, not implementation's
    # unrounded-sum hierarchy. Covers nonbinary alpha and per-level rounding.
    stride=2**level; side=image.width//stride; area=stride*stride; result=[]
    for y in range(side):
        for x in range(side):
            pixels=[image.getpixel((x*stride+dx,y*stride+dy)) for dy in range(stride) for dx in range(stride)]
            channels=[(sum(p[c]*p[3] for p in pixels)+(255*area)//2)//(255*area) for c in range(3)]
            channels.append((sum(p[3] for p in pixels)+area//2)//area)
            result.extend(channels)
    return bytes(result)


def packaged(root, *, capacity=1):
    _,_,source,_=transparent_fixture(root,sizes=(16,32),formats=('png',))
    output=root/'array'
    doc=export_alpha_textures(source,output,confirm_public=True,native_size=16,layers_per_bank=capacity)
    return source,output,doc


class IsolatedMipArithmetic(unittest.TestCase):
    def test_every_level_matches_independent_area_sum(self):
        rng=random.Random(287)
        for size in (16,32,64,128):
            with Image.frombytes('RGBA',(size,size),rng.randbytes(size*size*4)) as image:
                chain=mip_chain(image)
                self.assertEqual(len(chain),size.bit_length())
                for level,data in enumerate(chain):
                    self.assertEqual(data,independent_mip(image,level))
                    validate_premultiplied(data)

    def test_hidden_rgb_cannot_bleed_into_mips(self):
        with Image.new('RGBA',(16,16),(0,0,255,0)) as image:
            image.putpixel((0,0),(255,0,0,255))
            chain=mip_chain(image)
            self.assertEqual(chain[1][:4],bytes((64,0,0,64)))
            self.assertEqual(chain[-1],bytes((1,0,0,1)))
            self.assertTrue(all(all(data[i+2]==0 for i in range(0,len(data),4)) for data in chain))

    def test_preserves_original_source_and_labels_pm_quantisation(self):
        with Image.new('RGBA',(16,16),(173,87,211,73)) as image:
            raw=image.tobytes();data=mip_chain(image)[0]
            self.assertEqual(image.tobytes(),raw)
            self.assertEqual(data[:4],bytes((50,25,60,73)))
            self.assertNotEqual(data,raw)  # This is not a lossless source transport claim.

    def test_half_up_rounding_is_not_cascaded(self):
        with Image.new('RGBA',(16,16)) as image:
            image.putpixel((0,0),(255,255,255,2))
            levels=mip_chain(image)
            self.assertEqual(levels[1][:4],bytes((1,1,1,1)))
            self.assertEqual(levels[2][:4],bytes((0,0,0,0)))

    def test_each_sprite_is_independent_through_one_pixel(self):
        for colour in ((255,0,0,255),(0,0,255,255),(0,255,0,127)):
            with Image.new('RGBA',(32,32),colour) as image:
                data=mip_chain(image)
                expected=bytes((colour[0]*colour[3]//255,colour[1]*colour[3]//255,colour[2]*colour[3]//255,colour[3]))
                self.assertEqual(data[-1],expected)
                self.assertEqual(data[0],expected*(32*32))

    def test_rejects_non_rgba_and_unsupported_sizes(self):
        for mode,size in [('RGB',(16,16)),('RGBA',(16,32)),('RGBA',(8,8)),('RGBA',(256,256))]:
            with Image.new(mode,size) as image:
                with self.assertRaises(ValueError):mip_chain(image)
        with self.assertRaises(ValueError):mip_chain(None)
        for raw in (b'1',bytes((255,0,0,2)),bytearray(4)):
            with self.assertRaises(ValueError):validate_premultiplied(raw)


class AlphaArrayBundle(unittest.TestCase):
    def test_roundtrip_all_levels_and_source_recomputation(self):
        with tempfile.TemporaryDirectory() as tmp:
            source,out,doc=packaged(Path(tmp))
            self.assertEqual(doc['spriteCount'],2);self.assertEqual(len(doc['banks']),2)
            self.assertEqual(doc['levelCount'],5)
            result=verify_alpha_textures(out,source_bundle=source)
            self.assertTrue(result['sourceRecomputed'])
            self.assertFalse(verify_alpha_textures(out)['sourceRecomputed'])
            for sprite in doc['sprites']:self.assertEqual(sprite['spriteKey'],key_for(sprite))

    def test_bank_repacking_does_not_change_sprite_keys_or_mips(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source,out,first=packaged(root)
            second=export_alpha_textures(source,root/'other',confirm_public=True,native_size=16,layers_per_bank=2)
            self.assertEqual([s['spriteKey'] for s in first['sprites']],[s['spriteKey'] for s in second['sprites']])
            self.assertEqual([s['levelSha256'] for s in first['sprites']],[s['levelSha256'] for s in second['sprites']])
            self.assertEqual(first['payloadBytes'],second['payloadBytes'])
            self.assertNotEqual(len(first['banks']),len(second['banks']))

    def test_same_inputs_repeat_identically(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source,out,a=packaged(root)
            b=export_alpha_textures(source,root/'again',confirm_public=True,native_size=16,layers_per_bank=1)
            self.assertEqual(a,b)
            self.assertEqual((out/'manifest.json').read_bytes(),(root/'again/manifest.json').read_bytes())

    def test_opt_in_no_overwrite_and_missing_size(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source,out,_=packaged(root)
            for kwargs in ({},{'confirm_public':True,'native_size':64},{'confirm_public':True,'layers_per_bank':True},
                           {'confirm_public':True,'native_size':True},{'confirm_public':True,'layers_per_bank':257}):
                with self.assertRaises(ValueError):export_alpha_textures(source,root/'bad',**kwargs)
                self.assertFalse((root/'bad').exists())
            with self.assertRaises(ValueError):export_alpha_textures(source,out,confirm_public=True,native_size=16)
            with self.assertRaises(ValueError):export_alpha_textures(source,source/'child',confirm_public=True,native_size=16)

    def test_payload_and_viewer_tampering_and_failure_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            source,out,doc=packaged(Path(tmp))
            for path in [out/doc['banks'][0]['levels'][0]['file'],out/'runtime.js']:
                before=path.read_bytes();path.write_bytes(before+b'x')
                with self.assertRaises(ValueError):verify_alpha_textures(out)
                path.write_bytes(before)
            (out/'unlisted.txt').write_text('surprise')
            with self.assertRaises(ValueError):verify_alpha_textures(out)
            (out/'unlisted.txt').unlink();(out/'failure.json').write_text('{}')
            with self.assertRaises(ValueError):verify_alpha_textures(out)

    def test_strict_manifest_geometry_alpha_and_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            _,_,doc=packaged(Path(tmp))
            mutations=[lambda d:d.update(nativeSize=65536),lambda d:d.update(spriteCount=True),
                lambda d:d.update(payloadBytes=0),lambda d:d.update(publicOnly=False),lambda d:d.update(levelCount=True),
                lambda d:d['sampling'].update(alpha='straight'),lambda d:d['banks'][0]['levels'][0].update(file='../bad'),
                lambda d:d['banks'][0]['levels'][0].update(size=32),lambda d:d['sprites'][0].update(layerIndex=200),
                lambda d:d['sprites'][0].update(spriteKey='bfalpha1-'+'0'*64),lambda d:d['sprites'].reverse(),
                lambda d:d['sprites'][0].update(levelSha256=['0'*64]),lambda d:d.update(injected='ignored?')]
            for mutate in mutations:
                changed=copy.deepcopy(doc);mutate(changed)
                with self.assertRaises((ValueError,TypeError)):validate_manifest(changed)

    def test_recomputed_source_detects_rehashed_mip_substitution(self):
        with tempfile.TemporaryDirectory() as tmp:
            source,out,doc=packaged(Path(tmp))
            rec=doc['banks'][0]['levels'][-1];path=out/rec['file']
            data=bytes((255,0,0,255));path.write_bytes(data);rec['sha256']=_sha(data)
            doc['sprites'][0]['levelSha256'][-1]=_sha(data)
            (out/'manifest.json').write_bytes(_json(doc))
            self.assertEqual(verify_alpha_textures(out)['status'],'passed')  # Unsigned consistency, NOT authenticity.
            with self.assertRaisesRegex(ValueError,'recomputation'):verify_alpha_textures(out,source_bundle=source)

    def test_invalid_pm_is_rejected_even_with_rehashed_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            _,out,doc=packaged(Path(tmp))
            rec=doc['banks'][0]['levels'][-1];data=bytes((255,0,0,1))
            (out/rec['file']).write_bytes(data);rec['sha256']=_sha(data);doc['sprites'][0]['levelSha256'][-1]=_sha(data)
            (out/'manifest.json').write_bytes(_json(doc))
            with self.assertRaisesRegex(ValueError,'premultiplied'):verify_alpha_textures(out)

    def test_output_failure_never_publishes_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source,_,_=packaged(root);out=root/'failed'
            with patch('tools.artwork_alpha_textures.mip_chain',side_effect=ValueError('test interruption')):
                with self.assertRaises(ValueError):export_alpha_textures(source,out,confirm_public=True,native_size=16)
            self.assertTrue((out/'failure.json').exists());self.assertFalse((out/'manifest.json').exists())

    def test_linked_input_or_output_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source,out,_=packaged(root)
            try:(root/'link').symlink_to(source,target_is_directory=True)
            except (OSError,NotImplementedError):self.skipTest('OS does not permit symlinks')
            with self.assertRaises(ValueError):export_alpha_textures(root/'link',root/'new',confirm_public=True,native_size=16)
            with self.assertRaises(ValueError):export_alpha_textures(source,root/'link/new',confirm_public=True,native_size=16)

    def test_source_changes_fail_before_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source,_,_=packaged(root);(source/'index.html').write_bytes(b'changed')
            with self.assertRaises(ValueError):export_alpha_textures(source,root/'new',confirm_public=True,native_size=16)
            self.assertFalse((root/'new').exists())

    def test_cli_export_verify_and_nonzero_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source,_,_=packaged(root);script=ROOT/'scripts/export-artwork-alpha-textures.py'
            cmd=[sys.executable,str(script),'--confirm-public']
            run=subprocess.run(cmd+['export','--bundle',str(source),'--output',str(root/'cli'),'--native-size','16'],capture_output=True,text=True)
            self.assertEqual(run.returncode,0,run.stderr)
            run=subprocess.run(cmd+['verify','--bundle',str(root/'cli'),'--source-bundle',str(source)],capture_output=True,text=True)
            self.assertEqual(run.returncode,0,run.stderr);self.assertTrue(json.loads(run.stdout)['sourceRecomputed'])
            self.assertNotEqual(subprocess.run(cmd+['verify','--bundle',str(root/'missing')],capture_output=True).returncode,0)


if __name__=='__main__':unittest.main()
