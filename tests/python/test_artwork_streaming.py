"""Streaming/residency contracts. Static Unity checks are NOT GPU execution evidence."""
from __future__ import annotations
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]


class WebStreamingSource(unittest.TestCase):
    def setUp(self):
        self.source = (ROOT / 'integrations/web/artwork-streaming/runtime.js').read_text(encoding='utf-8')

    def test_cache_has_bounded_lru_pinning_dedup_and_cleanup(self):
        for token in (
            "VERSION='bytefables.streaming-residency.v1'", 'class ResidencyCache', 'this.loading=new Map()', 'entry.refs++',
            "Residency budget is pinned by active leases", 'residentBytes',
            'peakResidentBytes', 'this.counters.evictions++', 'this.disposer(victim.value)',
            'waitWithSignal', 'signal.addEventListener', 'dispose()',
        ):
            self.assertIn(token, self.source)

    def test_http_loader_is_bank_scoped_bounded_and_integrity_checked(self):
        for token in (
            "credentials:'omit'", "redirect:'error'", "cache:'no-store'",
            "new URL('manifest.json',base)", "new URL('source-manifest.json',base)",
            "new URL(bank.file,base)", 'Streaming KTX2 bank checksum mismatch',
            'Streaming decoded level checksum mismatch', 'Streaming sprite mip checksum mismatch',
            'transport.banks.length-1', 'same-origin HTTP directory',
        ):
            self.assertIn(token, self.source)
        self.assertNotIn('eval(', self.source)
        self.assertNotIn('Function(', self.source)

    def test_streaming_consumes_existing_decoder_and_never_generates_artwork(self):
        self.assertIn('ByteFablesKtx2Textures', self.source)
        self.assertIn('api.decode(data)', self.source)
        for forbidden in ('ArtworkRenderer', 'mip_chain', 'generateArtwork', 'canvas.toDataURL'):
            self.assertNotIn(forbidden, self.source)


class UnityResidencySource(unittest.TestCase):
    def setUp(self):
        self.source = (ROOT / 'integrations/unity/com.bytefables.textures/Runtime/TextureArrayResidency.cs').read_text(encoding='utf-8')

    def test_unity_residency_is_bounded_lru_and_lease_pinned(self):
        for token in (
            'TextureBundleData.MaximumPayloadBudget', 'EvictFor', 'References != 0',
            'Texture residency budget is pinned by active leases', 'TextureBankLease',
            'TextureSpriteLease', 'peakResidentBytes', 'evictions++', 'SetBudget',
        ):
            self.assertIn(token, self.source)

    def test_unity_residency_uploads_existing_verified_banks_only(self):
        for token in ('TextureArrayUpload.Create(source.Banks[bankIndex]', 'source.Find(fullSpriteKey)', 'IEnumerator Prefetch', 'yield return null;'):
            self.assertIn(token, self.source)
        for forbidden in ('HttpClient', 'UnityWebRequest', 'BasisTranscoder', 'UastcDecoder', 'Ktx2ArrayData.Parse('):
            self.assertNotIn(forbidden, self.source)

    def test_dispose_defers_pinned_banks_but_releases_unpinned(self):
        self.assertIn('if (pair.Value.References == 0)', self.source)
        self.assertIn('if (disposed && entry.References == 0)', self.source)
        self.assertIn('TextureArrayUpload.Destroy', self.source)


class SeparationContract(unittest.TestCase):
    def test_uastc_and_streaming_are_separate_versioned_surfaces(self):
        codec = (ROOT / 'tools/artwork_ktx2_basis.py').read_text(encoding='utf-8')
        web = (ROOT / 'integrations/web/artwork-streaming/runtime.js').read_text(encoding='utf-8')
        self.assertIn("SCHEMA = 'bytefables.ktx2-uastc-bundle.v1'", codec)
        self.assertIn("PROFILE = 'bytefables.ktx2-uastc-zstd.v1'", codec)
        self.assertIn("KTX_VERSION = '4.4.2'", codec)
        self.assertNotIn('uastc', web.lower())
        self.assertNotIn('basis', web.lower())


if __name__ == '__main__':
    unittest.main()
