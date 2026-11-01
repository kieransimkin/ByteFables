using System;

namespace ByteFables.Textures.Core
{
    /// <summary>A snapshot of one exact ByteFables KTX2 v1 bank, not a general KTX2 decoder.</summary>
    public sealed class Ktx2ArrayData
    {
        public const string Profile = "bytefables.ktx2-rgba8-array.v1";
        public const int MaxContainerBytes = 32 * 1024 * 1024;
        private static readonly byte[] Magic = { 0xab, 0x4b, 0x54, 0x58, 0x20, 0x32, 0x30, 0xbb, 13, 10, 26, 10 };
        private static readonly byte[] Dfd = Convert.FromBase64String("XAAAAAAAAAACAFgAAQABAQAAAAAEAAAAAAAAAAAABwAAAAAAAAAAAP8AAAAIAAcBAAAAAAAAAAD/AAAAEAAHAgAAAAAAAAAA/wAAABgABw8AAAAAAAAAAP8AAAA=");
        private static readonly byte[] Kvd = Convert.FromBase64String("EgAAAEtUWG9yaWVudGF0aW9uAHJkAAAAJwAAAEtUWHdyaXRlcgBCeXRlRmFibGVzIEtUWDIgdHJhbnNwb3J0IHYxAAA2AAAAb3JnLmJ5dGVmYWJsZXMucHJvZmlsZQBieXRlZmFibGVzLmt0eDItcmdiYTgtYXJyYXkudjEAAAA=");
        private readonly byte[] bytes;
        private readonly int[] offsets;
        public int Size { get; private set; }
        public int Layers { get; private set; }
        public int LevelCount { get { return offsets.Length; } }
        public string FileSha256 { get; private set; }
        private Ktx2ArrayData(byte[] bytes, int size, int layers, int[] offsets, string sha)
        { this.bytes = bytes; Size = size; Layers = layers; this.offsets = offsets; FileSha256 = sha; }

        internal static int LevelsFor(int size)
        {
            Checks.Require(size == 16 || size == 32 || size == 64 || size == 128, "Unsupported native texture size");
            int levels = 0; for (int s = size; s > 0; s >>= 1) levels++; return levels;
        }
        public static int EncodedLength(int size, int layers)
        {
            int count = LevelsFor(size);
            Checks.Require(layers >= 1 && layers <= 256, "Invalid layer count");
            int length = 80 + 24 * count + Dfd.Length + Kvd.Length;
            for (int l = 0; l < count; l++) length = checked(length + (size >> l) * (size >> l) * layers * 4);
            return length;
        }
        private static uint U32(byte[] b, int p)
        { return (uint)b[p] | (uint)b[p + 1] << 8 | (uint)b[p + 2] << 16 | (uint)b[p + 3] << 24; }
        private static ulong U64(byte[] b, int p) { return U32(b, p) | (ulong)U32(b, p + 4) << 32; }
        private static bool EqualAt(byte[] b, int at, byte[] expected)
        {
            if (at < 0 || at > b.Length - expected.Length) return false;
            for (int i = 0; i < expected.Length; i++) if (b[at + i] != expected[i]) return false;
            return true;
        }
        public static Ktx2ArrayData Parse(byte[] input, string expectedSha256 = null)
        {
            Checks.Require(input != null && input.Length >= 80 && input.Length <= MaxContainerBytes, "Invalid KTX2 byte budget");
            var b = (byte[])input.Clone(); // The caller cannot mutate accepted bytes later.
            string sha = TextureHashes.Sha256(b);
            if (expectedSha256 != null) Checks.Require(Checks.IsHash(expectedSha256) && sha == expectedSha256, "KTX2 checksum mismatch");
            Checks.Require(EqualAt(b, 0, Magic), "Invalid KTX2 identifier");
            uint width = U32(b, 20), layers = U32(b, 32);
            Checks.Require(width == 16 || width == 32 || width == 64 || width == 128, "Invalid KTX2 size");
            Checks.Require(layers >= 1 && layers <= 256, "Invalid KTX2 layers");
            int size = (int)width, depth = (int)layers, count = LevelsFor(size);
            Checks.Require(U32(b, 12) == 37 && U32(b, 16) == 1 && U32(b, 24) == width && U32(b, 28) == 0 &&
                U32(b, 36) == 1 && U32(b, 40) == count && U32(b, 44) == 0 && U64(b, 64) == 0 && U64(b, 72) == 0,
                "Unsupported KTX2 format, dimensions, compression or mip count");
            Checks.Require(b.Length == EncodedLength(size, depth), "Truncated or trailing KTX2 data");
            int dfd = 80 + 24 * count, kvd = dfd + Dfd.Length;
            Checks.Require(U32(b, 48) == dfd && U32(b, 52) == Dfd.Length && U32(b, 56) == kvd && U32(b, 60) == Kvd.Length &&
                EqualAt(b, dfd, Dfd) && EqualAt(b, kvd, Kvd), "KTX2 descriptor/alpha/orientation mismatch");
            int cursor = kvd + Kvd.Length; var offsets = new int[count];
            for (int level = count - 1; level >= 0; level--)
            {
                int side = size >> level, length = side * side * depth * 4, index = 80 + level * 24;
                Checks.Require(U64(b, index) == (ulong)cursor && U64(b, index + 8) == (ulong)length && U64(b, index + 16) == (ulong)length,
                    "KTX2 noncanonical or overlapping level index");
                offsets[level] = cursor;
                for (int p = cursor; p < cursor + length; p += 4)
                    Checks.Require(b[p] <= b[p + 3] && b[p + 1] <= b[p + 3] && b[p + 2] <= b[p + 3], "Invalid premultiplied pixel");
                cursor += length;
            }
            Checks.Require(cursor == b.Length, "KTX2 length mismatch");
            return new Ktx2ArrayData(b, size, depth, offsets, sha);
        }
        public int LevelSize(int level)
        { Checks.Require(level >= 0 && level < LevelCount, "Invalid mip index"); return Size >> level; }
        private int LayerOffset(int level, int layer)
        { int s = LevelSize(level); Checks.Require(layer >= 0 && layer < Layers, "Invalid layer index"); return offsets[level] + layer * s * s * 4; }
        public string LevelSha256(int level)
        { int s = LevelSize(level); return Checks.Hash(bytes, offsets[level], s * s * Layers * 4); }
        public string LayerSha256(int level, int layer)
        { int at = LayerOffset(level, layer), side = LevelSize(level); return Checks.Hash(bytes, at, side * side * 4); }
        /// <summary>Return a new buffer, optionally reversed to Unity's bottom-left CPU row order.</summary>
        public byte[] CopyLayer(int level, int layer, bool bottomUp = false)
        {
            int source = LayerOffset(level, layer), side = LevelSize(level), stride = side * 4;
            var output = new byte[side * stride];
            for (int row = 0; row < side; row++)
                Buffer.BlockCopy(bytes, source + row * stride, output, (bottomUp ? side - 1 - row : row) * stride, stride);
            return output;
        }
    }
}
