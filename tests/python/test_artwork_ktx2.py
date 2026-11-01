"""KTX2 profile framing, original-byte equivalence, malformed input and export boundaries."""
from __future__ import annotations
import base64
import copy
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/'integrations/framerudiments'))
from bytefables_framerudiments.ktx2_arrays import encode_ktx2, decode_ktx2, encoded_length, DFD, KVD, IDENTIFIER
from tools.artwork_ktx2_bundle import export_ktx2_bundle, verify_ktx2_bundle, validate_manifest
from tools.artwork_native_benchmark import _json, _sha
from test_artwork_alpha_textures import packaged


def levels(size=16, layers=2):
    # Different colours per layer and level, so accidental ordering is observable.
    return tuple(b''.join(bytes((l+1, (layer+1)%256, 0, 255))*((size>>l)**2)
                          for layer in range(layers)) for l in range(size.bit_length()))


class Ktx2Codec(unittest.TestCase):
    def test_roundtrip_all_sizes_and_boundary_layer_counts(self):
        for size in (16,32,64,128):
            for layers_count in (1,2,256):
                raw=levels(size,layers_count);data=encode_ktx2(size,layers_count,raw)
                parsed=decode_ktx2(data)
                self.assertEqual((parsed.size,parsed.layers,parsed.levels),(size,layers_count,raw))
                self.assertEqual(len(data),encoded_length(size,layers_count))

    def test_independent_header_and_level_layout(self):
        data=encode_ktx2(16,2,levels())
        self.assertEqual(data[:12],IDENTIFIER)
        self.assertEqual(struct.unpack_from('<9I',data,12),(37,1,16,16,0,2,1,5,0))
        dfd_at,dfd_length,kvd_at,kvd_length=struct.unpack_from('<4I',data,48)
        self.assertEqual((dfd_at,dfd_length),(200,92))
        self.assertEqual(kvd_at,292)
        cursor=kvd_at+kvd_length
        for l in range(4,-1,-1):
            at,length,inflated=struct.unpack_from('<3Q',data,80+24*l)
            self.assertEqual((at,length,inflated),(cursor,(16>>l)**2*8,(16>>l)**2*8))
            self.assertEqual(data[at:at+4],bytes((l+1,1,0,255)))
            self.assertEqual(data[at+length//2:at+length//2+4],bytes((l+1,2,0,255)))
            cursor+=length
        self.assertEqual(cursor,len(data))

    def test_descriptor_and_nul_padded_metadata(self):
        self.assertEqual(struct.unpack_from('<IIHH',DFD),(92,0,2,88))
        self.assertEqual(DFD[12:28],bytes((1,0,1,1,0,0,0,0,4,0,0,0,0,0,0,0)))
        for i,ch in enumerate((0,1,2,15)):
            self.assertEqual(struct.unpack_from('<HBB4BII',DFD,28+i*16),(i*8,7,ch,0,0,0,0,0,255))
        cursor=0;keys=[];values={}
        while cursor<len(KVD):
            n=struct.unpack_from('<I',KVD,cursor)[0];entry=KVD[cursor+4:cursor+4+n]
            key,value=entry.split(b'\0',1);keys.append(key);values[key]=value
            self.assertTrue(value.endswith(b'\0'));self.assertEqual(KVD[cursor+4+n:cursor+4+((n+3)//4)*4],bytes(-n%4))
            cursor+=4+((n+3)//4)*4
        self.assertEqual(keys,sorted(keys));self.assertEqual(values[b'KTXorientation'],b'rd\0')

    def test_rejects_header_mutations_and_huge_lengths(self):
        original=encode_ktx2(16,2,levels())
        for offset,value in ((12,43),(16,4),(24,32),(28,1),(32,0),(36,6),(40,0),(44,1),(48,0),(52,0),(56,0),(60,0)):
            data=bytearray(original);struct.pack_into('<I',data,offset,value)
            with self.subTest(offset=offset),self.assertRaises(ValueError):decode_ktx2(bytes(data))
        for offset in (64,72,80,88,96):
            data=bytearray(original);struct.pack_into('<Q',data,offset,2**63+1)
            with self.subTest(offset=offset),self.assertRaises(ValueError):decode_ktx2(bytes(data))

    def test_rejects_descriptor_alpha_colour_metadata_and_padding_changes(self):
        original=encode_ktx2(16,2,levels())
        for offset in (0,200,200+14,200+15,200+31,292+8,292+len(KVD)-1):
            data=bytearray(original);data[offset]^=1
            with self.subTest(offset=offset),self.assertRaises(ValueError):decode_ktx2(bytes(data))

    def test_rejects_overlapping_or_misordered_levels(self):
        original=encode_ktx2(16,2,levels())
        for offset in (80,80+24,80+4*24):
            data=bytearray(original);struct.pack_into('<Q',data,offset,200)
            with self.assertRaises(ValueError):decode_ktx2(bytes(data))

    def test_rejects_all_truncations_and_trailing_bytes(self):
        data=encode_ktx2(16,1,levels(16,1))
        for end in range(len(data)):
            with self.assertRaises(ValueError):decode_ktx2(data[:end])
        with self.assertRaises(ValueError):decode_ktx2(data+b'\0')

    def test_rejects_bad_inputs_and_nonpremultiplied_pixels(self):
        for size,count in ((True,1),(8,1),(16,True),(16,0),(16,257),(2**32,1)):
            with self.assertRaises(ValueError):encode_ktx2(size,count,())
        for raw in ((),list(levels())[:-1],list(levels())+[b''],[b'bad']*5):
            with self.assertRaises(ValueError):encode_ktx2(16,2,raw)
        raw=list(levels());raw[0]=b'\xff\0\0\x01'+raw[0][4:]
        with self.assertRaises(ValueError):encode_ktx2(16,2,raw)
        data=bytearray(encode_ktx2(16,2,levels()));at=struct.unpack_from('<Q',data,80)[0];data[at:at+4]=b'\xff\0\0\x01'
        with self.assertRaises(ValueError):decode_ktx2(bytes(data))

    def test_cross_language_vector_is_frozen(self):
        vector=json.loads((ROOT/'tests/vectors/artwork-ktx2-v1.json').read_text())
        for record in vector['transport']['banks']:
            data=base64.b64decode(vector['files'][record['file']],validate=True)
            parsed=decode_ktx2(data);self.assertEqual(_sha(data),record['sha256'])
            self.assertEqual(encode_ktx2(parsed.size,parsed.layers,parsed.levels),data)
            for l,raw in enumerate(parsed.levels):
                original=vector['source']['banks'][record['index']]['levels'][l]
                self.assertEqual(_sha(raw),original['sha256'])


class Ktx2Bundle(unittest.TestCase):
    def export(self,root):
        _,alpha,source=packaged(root)
        out=root/'ktx2';doc=export_ktx2_bundle(alpha,out,confirm_public=True)
        return alpha,source,out,doc

    def test_roundtrip_and_repeatability_preserve_source_manifest_and_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);alpha,source,out,doc=self.export(root)
            self.assertTrue(verify_ktx2_bundle(out,source_bundle=alpha)['originalBytesCompared'])
            self.assertFalse(verify_ktx2_bundle(out)['originalBytesCompared'])
            self.assertEqual((out/'source-manifest.json').read_bytes(),(alpha/'manifest.json').read_bytes())
            self.assertEqual(export_ktx2_bundle(alpha,root/'again',confirm_public=True),doc)
            self.assertEqual(json.loads((out/'source-manifest.json').read_text())['sprites'],source['sprites'])

    def test_opt_in_existing_nested_output_and_failed_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);alpha,_,out,_=self.export(root)
            for target,confirm in ((root/'no',False),(out,True),(alpha/'nested',True)):
                with self.assertRaises(ValueError):export_ktx2_bundle(alpha,target,confirm_public=confirm)
            (alpha/'failure.json').write_text('{}')
            with self.assertRaises(ValueError):export_ktx2_bundle(alpha,root/'bad',confirm_public=True)
            self.assertFalse((root/'bad').exists())

    def test_source_and_bundle_tampering_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            alpha,source,out,doc=self.export(Path(tmp))
            for name in ('source-manifest.json',doc['banks'][0]['file'],'ktx2-runtime.js'):
                path=out/name;before=path.read_bytes();path.write_bytes(before+b'x')
                with self.assertRaises(ValueError):verify_ktx2_bundle(out)
                path.write_bytes(before)
            (out/'extra').write_text('unexpected')
            with self.assertRaises(ValueError):verify_ktx2_bundle(out)
            (out/'extra').unlink();(out/'failure.json').write_text('{}')
            with self.assertRaises(ValueError):verify_ktx2_bundle(out)

    def test_rehashed_ktx2_substitution_still_fails_original_mip_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            _,_,out,doc=self.export(Path(tmp));bank=doc['banks'][0];path=out/bank['file']
            data=bytearray(path.read_bytes());at=struct.unpack_from('<Q',data,80)[0]
            data[at:at+4]=bytes((1,1,1,255));path.write_bytes(data);bank['sha256']=_sha(data)
            (out/'manifest.json').write_bytes(_json(doc))
            with self.assertRaisesRegex(ValueError,'mip bytes'):verify_ktx2_bundle(out)

    def test_manifest_geometry_paths_and_public_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            _,source,_,doc=self.export(Path(tmp))
            for mutate in (lambda d:d.update(publicOnly=False),lambda d:d['banks'][0].update(file='../x'),
                           lambda d:d['banks'][0].update(byteLength=2**63),lambda d:d['banks'][0].update(index=True),
                           lambda d:d['sourceManifest'].update(file='https://bad/'),lambda d:d.update(extra=True)):
                bad=copy.deepcopy(doc);mutate(bad)
                with self.assertRaises(ValueError):validate_manifest(bad,source)

    def test_source_rebind_and_symlinks_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);alpha,_,out,_=self.export(root)
            (alpha/'manifest.json').write_bytes((alpha/'manifest.json').read_bytes()+b'\n')
            with self.assertRaises(ValueError):verify_ktx2_bundle(out,source_bundle=alpha)
            try:(root/'linked').symlink_to(out,target_is_directory=True)
            except (OSError,NotImplementedError):self.skipTest('Symlinks unavailable on platform')
            with self.assertRaises(ValueError):verify_ktx2_bundle(root/'linked')

    def test_cli_export_verify_and_failure_exit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);_,alpha,_=packaged(root);out=root/'cli'
            command=[sys.executable,str(ROOT/'scripts/export-artwork-ktx2.py'),'--confirm-public']
            for args in (['export','--bundle',str(alpha),'--output',str(out)],['verify','--bundle',str(out),'--source-bundle',str(alpha)]):
                result=subprocess.run(command+args,capture_output=True,text=True,timeout=30)
                self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(json.loads(result.stdout)['status'],'passed')
            result=subprocess.run(command+['verify','--bundle',str(root/'missing')],capture_output=True,text=True,timeout=30)
            self.assertEqual(result.returncode,1)


if __name__=='__main__':unittest.main()
