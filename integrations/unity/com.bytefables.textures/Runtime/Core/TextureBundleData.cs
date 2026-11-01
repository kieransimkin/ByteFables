using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Globalization;
using System.Text;

namespace ByteFables.Textures.Core
{
    public sealed class TextureSprite
    {
        public string SpriteKey { get; private set; }
        public string DigestHex { get; private set; }
        public string Family { get; private set; }
        public string Palette { get; private set; }
        public int Complexity { get; private set; }
        public int BankIndex { get; private set; }
        public int LayerIndex { get; private set; }
        public IReadOnlyList<string> LevelHashes { get; private set; }
        internal TextureSprite(string key, string digest, string family, string palette, int complexity, int bank, int layer, string[] hashes)
        { SpriteKey = key; DigestHex = digest; Family = family; Palette = palette; Complexity = complexity; BankIndex = bank; LayerIndex = layer; LevelHashes = Array.AsReadOnly(hashes); }
    }

    /// <summary>Validated, immutable public texture metadata and private KTX2 byte snapshots.</summary>
    public sealed class TextureBundleData
    {
        public const string Schema = "bytefables.ktx2-alpha-bundle.v1";
        public const int DefaultPayloadBudget = 64 * 1024 * 1024;
        public const int MaximumPayloadBudget = 128 * 1024 * 1024;
        public string ManifestSha256 { get; private set; }
        public int NativeSize { get; private set; }
        public int PayloadBytes { get; private set; }
        public IReadOnlyList<Ktx2ArrayData> Banks { get; private set; }
        public IReadOnlyList<TextureSprite> Sprites { get; private set; }
        private readonly Dictionary<string, int> byKey;
        private TextureBundleData(string sha, int size, int bytes, List<Ktx2ArrayData> banks, List<TextureSprite> sprites)
        {
            ManifestSha256 = sha; NativeSize = size; PayloadBytes = bytes;
            Banks = banks.AsReadOnly(); Sprites = sprites.AsReadOnly(); byKey = new Dictionary<string, int>(StringComparer.Ordinal);
            for (int i = 0; i < sprites.Count; i++) byKey.Add(sprites[i].SpriteKey, i);
        }
        public TextureSprite Find(string fullSpriteKey)
        { int index; Checks.Require(fullSpriteKey != null && byKey.TryGetValue(fullSpriteKey, out index), "Unknown full sprite key"); return Sprites[byKey[fullSpriteKey]]; }

        private static void PublicContract(Dictionary<string, object> map, string schema, string profile)
        {
            J.Eq(J.Get(map, "schema"), schema); J.Eq(J.Get(map, "profile"), profile); J.Eq(J.Get(map, "status"), "passed");
            J.Bool(J.Get(map, "publicOnly"), true); J.Eq(J.Get(map, "guarantee"), "presentation-only");
        }
        private static void ViewerMetadata(object input, string[] names)
        {
            var list = J.Arr(input); Checks.Require(list.Count == names.Length, "Viewer inventory mismatch");
            for (int i = 0; i < names.Length; i++)
            { var f = J.Obj(list[i]); J.Keys(f, "file", "sha256", "byteLength"); J.Eq(J.Get(f, "file"), names[i]); J.Hash(J.Get(f, "sha256")); J.Int(J.Get(f, "byteLength"), 1, 256 * 1024); }
        }
        private static byte[] Read(Func<string, int, byte[]> reader, string name, int length, string sha)
        {
            var data = reader(name, length);
            Checks.Require(data != null && data.Length == length, "File byte count mismatch: " + name);
            var snapshot = (byte[])data.Clone();
            Checks.Require(TextureHashes.Sha256(snapshot) == sha, "File checksum mismatch: " + name); return snapshot;
        }
        private static string Text(Dictionary<string, object> map, string key) { return J.Str(J.Get(map, key)); }
        private static int Number(Dictionary<string, object> map, string key, int low, int high) { return J.Int(J.Get(map, key), low, high); }
        private static string Hash(Dictionary<string, object> map, string key) { return J.Hash(J.Get(map, key)); }
        private static string CanonicalKey(string digest, string family, string palette, int complexity, int size, string sourceHash)
        {
            // These fields are restricted to ASCII enums/digits/hex before interpolation.
            string json = "{\n  \"profile\": \"bytefables.premultiplied-area-mips.v1\",\n  \"digestHex\": \"" + digest +
                "\",\n  \"family\": \"" + family + "\",\n  \"palette\": \"" + palette + "\",\n  \"complexity\": " + complexity.ToString(CultureInfo.InvariantCulture) +
                ",\n  \"nativeSize\": " + size.ToString(CultureInfo.InvariantCulture) + ",\n  \"sourceRGBAsha256\": \"" + sourceHash + "\"\n}\n";
            return "bfalpha1-" + TextureHashes.Sha256(Encoding.UTF8.GetBytes(json));
        }
        /// <summary>Read only canonical source-manifest/bank paths. Never reads or executes web viewer files.</summary>
        public static TextureBundleData Load(byte[] manifestBytes, Func<string, int, byte[]> readFile,
            string expectedManifestSha256 = null, int maxPayloadBytes = DefaultPayloadBudget)
        {
            if (readFile == null) throw new ArgumentNullException(nameof(readFile));
            Checks.Require(maxPayloadBytes >= 1 && maxPayloadBytes <= MaximumPayloadBudget, "Invalid payload budget");
            Checks.Require(manifestBytes != null && manifestBytes.Length <= StrictJson.MaxBytes, "Invalid manifest size");
            var snapshot = (byte[])manifestBytes.Clone(); string sha = TextureHashes.Sha256(snapshot);
            if (expectedManifestSha256 != null) Checks.Require(Checks.IsHash(expectedManifestSha256) && expectedManifestSha256 == sha, "Manifest pin mismatch");
            var transport = J.Obj(StrictJson.Parse(snapshot));
            J.Keys(transport, "schema", "profile", "status", "publicOnly", "guarantee", "sourceManifest", "banks", "viewerFiles");
            PublicContract(transport, Schema, Ktx2ArrayData.Profile);
            var record = J.Obj(J.Get(transport, "sourceManifest")); J.Keys(record, "file", "byteLength", "sha256");
            J.Eq(J.Get(record, "file"), "source-manifest.json");
            var source = J.Obj(StrictJson.Parse(Read(readFile, "source-manifest.json", Number(record, "byteLength", 1, StrictJson.MaxBytes), Hash(record, "sha256"))));
            J.Keys(source, "schema", "profile", "status", "publicOnly", "guarantee", "nativeSize", "layersPerBank", "spriteCount", "levelCount", "payloadBytes", "sourceManifestSha256", "sampling", "banks", "sprites", "viewerFiles");
            PublicContract(source, "bytefables.alpha-texture-array-bundle.v1", "bytefables.premultiplied-area-mips.v1");
            int size = Number(source, "nativeSize", 16, 128), levels = Ktx2ArrayData.LevelsFor(size);
            int capacity = Number(source, "layersPerBank", 1, 256), count = Number(source, "spriteCount", 1, 1024);
            Checks.Require(Number(source, "levelCount", 1, 8) == levels, "Mip count mismatch"); Hash(source, "sourceManifestSha256");
            int payload = 0; for (int l = 0; l < levels; l++) payload = checked(payload + (size >> l) * (size >> l) * 4 * count);
            Checks.Require(Number(source, "payloadBytes", 1, maxPayloadBytes) == payload, "Payload budget mismatch");
            var sampling = J.Obj(J.Get(source, "sampling"));
            J.Keys(sampling, "storage", "alpha", "origin", "colourSpace", "wrap", "filters", "mipSource", "generatedOnGPU");
            J.Eq(J.Get(sampling, "storage"), "RGBA8"); J.Eq(J.Get(sampling, "alpha"), "premultiplied"); J.Eq(J.Get(sampling, "origin"), "top-left");
            J.Eq(J.Get(sampling, "colourSpace"), "stored-samples-no-transfer"); J.Eq(J.Get(sampling, "wrap"), "clamp-to-edge");
            J.Eq(J.Get(sampling, "mipSource"), "isolated-original-area"); J.Bool(J.Get(sampling, "generatedOnGPU"), false);
            var filters = J.Arr(J.Get(sampling, "filters")); Checks.Require(filters.Count == 2, "Filter count mismatch"); J.Eq(filters[0], "nearest"); J.Eq(filters[1], "linear-mipmap-linear");
            var originals = J.Arr(J.Get(source, "banks")); var wrappers = J.Arr(J.Get(transport, "banks"));
            Checks.Require(originals.Count == (count + capacity - 1) / capacity && wrappers.Count == originals.Count, "Bank count mismatch");
            // Validate identity metadata before opening banks; each bank path is fixed before its read.
            var sprites = new List<TextureSprite>(); var entries = J.Arr(J.Get(source, "sprites"));
            Checks.Require(entries.Count == count, "Sprite count mismatch"); string previous = null;
            var families = new HashSet<string> { "sigil", "constellation", "heraldry", "topography", "crystal", "mandala", "cellular", "branching", "orbital" };
            var palettes = new HashSet<string> { "neon", "pastel", "mono" };
            for (int i = 0; i < count; i++)
            {
                var s = J.Obj(entries[i]); J.Keys(s, "spriteKey", "digestHex", "family", "palette", "complexity", "nativeSize", "bankIndex", "layerIndex", "sourceFile", "sourceFileSha256", "sourceRGBAsha256", "levelSha256");
                string digest = Hash(s, "digestHex"), family = Text(s, "family"), palette = Text(s, "palette");
                Checks.Require(families.Contains(family) && palettes.Contains(palette), "Unknown sprite family/palette");
                int complexity = Number(s, "complexity", 1, 8); string order = family + "/" + palette + "/" + complexity + "/" + digest;
                Checks.Require(previous == null || string.CompareOrdinal(previous, order) < 0, "Duplicate or unsorted sprites"); previous = order;
                Checks.Require(Number(s, "nativeSize", 16, 128) == size && Number(s, "bankIndex", 0, originals.Count - 1) == i / capacity &&
                    Number(s, "layerIndex", 0, 255) == i % capacity, "Sprite placement mismatch");
                string key = CanonicalKey(digest, family, palette, complexity, size, Hash(s, "sourceRGBAsha256"));
                Checks.Require(Text(s, "spriteKey") == key, "Sprite key mismatch"); Hash(s, "sourceFileSha256");
                J.Eq(J.Get(s, "sourceFile"), "assets/" + family + "-" + palette + "-c" + complexity + "/" + digest + "/" + size + ".png");
                var hashes = J.Arr(J.Get(s, "levelSha256")); Checks.Require(hashes.Count == levels, "Per-sprite mip count mismatch");
                var strings = new string[levels]; for (int l = 0; l < levels; l++) strings[l] = J.Hash(hashes[l]);
                sprites.Add(new TextureSprite(key, digest, family, palette, complexity, i / capacity, i % capacity, strings));
            }
            ViewerMetadata(J.Get(transport, "viewerFiles"), new[] { "index.html", "alpha-runtime.js", "ktx2-runtime.js", "demo.js", "demo.css" });
            ViewerMetadata(J.Get(source, "viewerFiles"), new[] { "index.html", "runtime.js", "demo.js", "demo.css" });
            var banks = new List<Ktx2ArrayData>();
            for (int b = 0; b < originals.Count; b++)
            {
                var original = J.Obj(originals[b]); var wrapper = J.Obj(wrappers[b]);
                J.Keys(original, "index", "layerCount", "levels"); J.Keys(wrapper, "index", "layerCount", "file", "byteLength", "sha256");
                int layers = Math.Min(capacity, count - b * capacity);
                Checks.Require(Number(original, "index", 0, 1023) == b && Number(wrapper, "index", 0, 1023) == b &&
                    Number(original, "layerCount", 1, 256) == layers && Number(wrapper, "layerCount", 1, 256) == layers, "Bank index/layers mismatch");
                string path = "banks/bank-" + b.ToString("D3", CultureInfo.InvariantCulture) + ".ktx2"; J.Eq(J.Get(wrapper, "file"), path);
                int length = Number(wrapper, "byteLength", 1, Ktx2ArrayData.MaxContainerBytes);
                Checks.Require(length == Ktx2ArrayData.EncodedLength(size, layers), "Bank byte count mismatch");
                var mipRecords = J.Arr(J.Get(original, "levels")); Checks.Require(mipRecords.Count == levels, "Original level count mismatch");
                var mipHashes = new string[levels];
                for (int l = 0; l < levels; l++)
                {
                    var r = J.Obj(mipRecords[l]); J.Keys(r, "level", "size", "file", "byteLength", "sha256"); int side = size >> l;
                    Checks.Require(Number(r, "level", 0, 7) == l && Number(r, "size", 1, 128) == side &&
                        Number(r, "byteLength", 1, MaximumPayloadBudget) == side * side * layers * 4, "Invalid mip metadata");
                    J.Eq(J.Get(r, "file"), "levels/bank-" + b.ToString("D3", CultureInfo.InvariantCulture) + "-mip-" + l.ToString("D2", CultureInfo.InvariantCulture) + ".rgba"); mipHashes[l] = Hash(r, "sha256");
                }
                var parsed = Ktx2ArrayData.Parse(Read(readFile, path, length, Hash(wrapper, "sha256")));
                Checks.Require(parsed.Size == size && parsed.Layers == layers, "Container/manifest geometry mismatch");
                for (int l = 0; l < levels; l++)
                {
                    Checks.Require(parsed.LevelSha256(l) == mipHashes[l], "Level hash mismatch");
                    for (int layer = 0; layer < layers; layer++)
                        Checks.Require(parsed.LayerSha256(l, layer) == sprites[b * capacity + layer].LevelHashes[l], "Sprite layer hash mismatch");
                }
                banks.Add(parsed);
            }
            return new TextureBundleData(sha, size, payload, banks, sprites);
        }
    }
}
