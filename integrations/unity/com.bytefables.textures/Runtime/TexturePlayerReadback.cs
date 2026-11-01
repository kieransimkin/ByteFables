using System;
using ByteFables.Textures.Core;
using UnityEngine;
using UnityEngine.Rendering;

namespace ByteFables.Textures
{
    // Player-safe GPU acceptance probes. No UnityEditor dependency and no artwork generator.
    public static class TexturePlayerReadback
    {
        private static void Require(bool condition, string message)
        { if (!condition) throw new TextureContractException(message); }
        private static void Same(byte[] expected, byte[] actual, string label, int tolerance = 0)
        {
            Require(expected.Length == actual.Length, label + ": wrong byte count");
            for (int i = 0; i < expected.Length; i++)
                Require(Math.Abs(expected[i] - actual[i]) <= tolerance, label + ": pixel byte mismatch at " + i);
        }
        public static System.Collections.IEnumerator Qualify(TextureBundleAsset imported,
            TextureBundleData data, Shader shader, TexturePlayerResult report)
        {
            Require(imported != null && imported.ManifestSha256 == data.ManifestSha256 &&
                imported.SpriteCount == data.Sprites.Count && imported.BankCount == data.Banks.Count &&
                imported.NativeSize == data.NativeSize, "Built asset differs from the pinned source");
            for (int i = 0; i < data.Sprites.Count; i++)
            {
                var binding = imported.Find(data.Sprites[i].SpriteKey);
                Require(binding.DigestHex == data.Sprites[i].DigestHex && binding.BankIndex == data.Sprites[i].BankIndex && binding.LayerIndex == data.Sprites[i].LayerIndex,
                    "Serialized identity binding changed");
                Require(binding.Family == data.Sprites[i].Family && binding.Palette == data.Sprites[i].Palette &&
                    binding.Complexity == data.Sprites[i].Complexity, "Serialized style binding changed");
                report.bindingComparisons++;
            }
            Require(shader != null && shader.isSupported, "Array shader is missing or unsupported");
            var material = new Material(shader);
            try
            {
                for (int bank = 0; bank < data.Banks.Count; bank++)
                {
                    var original = data.Banks[bank];
                    var cpu = TextureArrayUpload.Create(original, FilterMode.Point, keepReadable: true);
                    try
                    {
                        var gpu = imported.GetBank(bank); gpu.filterMode = FilterMode.Point;
                        Require(!gpu.isReadable && gpu.mipmapCount == original.LevelCount && gpu.depth == original.Layers, "Imported bank settings changed");
                        material.SetTexture("_Array", gpu);
                        for (int layer = 0; layer < original.Layers; layer++)
                        {
                            material.SetFloat("_Layer", layer);
                            for (int mip = 0; mip < original.LevelCount; mip++)
                            {
                                int side = original.LevelSize(mip); var expected = original.CopyLayer(mip, layer, bottomUp: true);
                                Same(expected, cpu.GetPixelData<byte>(mip, layer).ToArray(), "CPU upload"); report.cpuComparisons++;
                                var request = AsyncGPUReadback.Request(gpu, mip, 0, side, 0, side, layer, 1, TextureFormat.RGBA32);
                                request.WaitForCompletion(); Require(!request.hasError, "GPU array readback failed");
                                Same(expected, request.GetData<byte>().ToArray(), "GPU raw mip/layer"); report.gpuComparisons++;
                                material.SetFloat("_Mip", mip);
                                foreach (var matte in new[] { new Color32(0,0,0,0), new Color32(0,0,0,255), new Color32(255,255,255,255) })
                                {
                                    Same(Composite(expected, matte), Draw(material, side, matte), "Shader orientation/matte"); report.shaderComparisons++;
                                }
                            }
                            // Destroy() is deferred in a player. Release per-layer temporary GPU
                            // resources before advancing; do not accumulate an entire corpus.
                            yield return null;
                        }
                    }
                    finally { TextureArrayUpload.Destroy(cpu); }
                }
            }
            finally { TextureArrayUpload.Destroy(material); }
        }
        private static byte[] Composite(byte[] source, Color32 matte)
        {
            var result = new byte[source.Length]; byte[] background = { matte.r, matte.g, matte.b, matte.a };
            for (int p = 0; p < source.Length; p += 4)
                for (int c = 0; c < 4; c++) result[p+c] = (byte)(source[p+c] + (background[c]*(255-source[p+3])+127)/255);
            return result;
        }
        private static byte[] Draw(Material material, int side, Color32 clear, Action afterFirst = null)
        {
            var target = new RenderTexture(side, side, 0, RenderTextureFormat.ARGB32, RenderTextureReadWrite.Linear)
                { antiAliasing = 1, useMipMap = false, autoGenerateMips = false };
            var read = new Texture2D(side, side, TextureFormat.RGBA32, false, true);
            var previous = RenderTexture.active; bool srgb = GL.sRGBWrite;
            try
            {
                Require(target.Create(), "Render target allocation failed"); RenderTexture.active = target; GL.sRGBWrite = false;
                GL.Clear(false, true, clear);
                Graphics.Blit(null, target, material, 0);
                if (afterFirst != null) { afterFirst(); Graphics.Blit(null, target, material, 0); }
                RenderTexture.active = target; read.ReadPixels(new Rect(0,0,side,side), 0, 0, false);
                return read.GetPixelData<byte>(0).ToArray();
            }
            finally { RenderTexture.active = previous; GL.sRGBWrite = srgb; target.Release(); TextureArrayUpload.Destroy(target); TextureArrayUpload.Destroy(read); }
        }
        public static void Overlap(TextureBundleData sentinel, Shader shader, TexturePlayerResult report)
        {
            using (var uploaded = new UploadedTextureBundle(sentinel))
            {
                var material = new Material(shader);
                try
                {
                    foreach (var order in new[] { new[] {0,1}, new[] {1,0}, new[] {1,2} })
                    {
                        var a = sentinel.Sprites[order[0]]; var b = sentinel.Sprites[order[1]];
                        var first = sentinel.Banks[a.BankIndex].CopyLayer(0, a.LayerIndex, true);
                        var second = sentinel.Banks[b.BankIndex].CopyLayer(0, b.LayerIndex, true);
                        var expected = new byte[first.Length];
                        for (int p = 0; p < first.Length; p += 4)
                            for (int c = 0; c < 4; c++) expected[p+c] = (byte)(second[p+c] + (first[p+c]*(255-second[p+3])+127)/255);
                        material.SetTexture("_Array", uploaded.GetBank(a.BankIndex)); material.SetFloat("_Layer", a.LayerIndex); material.SetFloat("_Mip", 0);
                        var result = Draw(material, 16, new Color32(0,0,0,0), () => { material.SetTexture("_Array", uploaded.GetBank(b.BankIndex)); material.SetFloat("_Layer", b.LayerIndex); });
                        // Normalized framebuffer blend arithmetic may round differently by one byte.
                        Same(expected, result, "Overlapping source-over order", 1); report.overlapComparisons++;
                    }
                }
                finally { TextureArrayUpload.Destroy(material); }
            }
        }
    }
}
