using System;
using System.Collections.Generic;
using System.Diagnostics;
using ByteFables.Textures.Core;
using UnityEngine;
using UnityEngine.Rendering;

namespace ByteFables.Textures
{
    [Serializable]
    public sealed class TextureGraphProbeResult
    {
        public int instances, uniqueSprites, banks, drawCalls, mip, width, height, pixelsCompared;
        public long submitMicroseconds, readbackMicroseconds, totalMicroseconds;
        public bool exactPixels;
        public string expectedSha256, actualSha256;
    }

    /// <summary>
    /// Deterministic instanced-node workload over imported Texture2DArray subassets.
    /// It is a qualification workload, not an FPS claim or a graph-layout engine.
    /// </summary>
    public static class TextureGraphBenchmark
    {
        private const int MaxSide = 2048;
        private const int BatchLimit = 1023;

        private static void Require(bool condition, string message)
        { if (!condition) throw new TextureContractException(message); }

        private static long Microseconds(long ticks)
        { return checked(ticks * 1000000L / Stopwatch.Frequency); }

        private static Mesh Quad()
        {
            var mesh = new Mesh { name = "ByteFables qualification quad" };
            mesh.vertices = new[] { new Vector3(0,0,0), new Vector3(1,0,0), new Vector3(1,1,0), new Vector3(0,1,0) };
            mesh.uv = new[] { new Vector2(0,0), new Vector2(1,0), new Vector2(1,1), new Vector2(0,1) };
            mesh.triangles = new[] { 0,1,2, 0,2,3 };
            mesh.UploadMeshData(false);
            return mesh;
        }

        public static TextureGraphProbeResult Run(TextureBundleAsset imported, TextureBundleData data,
            Shader shader, int instanceCount)
        {
            Require(imported != null && data != null && shader != null && shader.isSupported, "Graph benchmark inputs are unavailable");
            Require(instanceCount >= 1 && instanceCount <= 10000, "Graph benchmark instance count outside 1..10000");
            Require(imported.ManifestSha256 == data.ManifestSha256 && imported.SpriteCount == data.Sprites.Count,
                "Graph benchmark imported asset differs from source metadata");
            Require(SystemInfo.supportsInstancing && SystemInfo.supports2DArrayTextures, "Instancing and texture arrays are required");
            Require(data.Banks.Count > 0 && data.Sprites.Count > 0, "Graph benchmark needs at least one bank and sprite");

            int columns = Mathf.CeilToInt(Mathf.Sqrt(instanceCount));
            int rows = (instanceCount + columns - 1) / columns;
            int mip = 0, levelCount = data.Banks[0].LevelCount, tile = data.NativeSize;
            while (mip + 1 < levelCount && (columns * tile > MaxSide || rows * tile > MaxSide))
            { mip++; tile = data.NativeSize >> mip; }
            int width = columns * tile, height = rows * tile;
            Require(width >= 1 && height >= 1 && width <= MaxSide && height <= MaxSide, "Graph framebuffer exceeds qualification bounds");
            foreach (var bank in data.Banks)
                Require(bank.LevelCount == levelCount && bank.LevelSize(mip) == tile, "Graph banks have inconsistent mip geometry");

            var total = Stopwatch.StartNew();
            var expected = new byte[checked(width * height * 4)];
            var rects = new List<Vector4>[data.Banks.Count];
            var layers = new List<float>[data.Banks.Count];
            for (int b = 0; b < data.Banks.Count; b++) { rects[b] = new List<Vector4>(); layers[b] = new List<float>(); }

            for (int i = 0; i < instanceCount; i++)
            {
                var sprite = data.Sprites[i % data.Sprites.Count];
                int cellX = i % columns, cellY = i / columns;
                var source = data.Banks[sprite.BankIndex].CopyLayer(mip, sprite.LayerIndex, true);
                int stride = tile * 4;
                for (int row = 0; row < tile; row++)
                    Buffer.BlockCopy(source, row * stride, expected,
                        checked(((cellY * tile + row) * width + cellX * tile) * 4), stride);
                float x0 = -1f + 2f * (cellX * tile) / width;
                float y0 = -1f + 2f * (cellY * tile) / height;
                float x1 = -1f + 2f * ((cellX + 1) * tile) / width;
                float y1 = -1f + 2f * ((cellY + 1) * tile) / height;
                rects[sprite.BankIndex].Add(new Vector4(x0, y0, x1, y1));
                layers[sprite.BankIndex].Add(sprite.LayerIndex);
            }

            var target = new RenderTexture(width, height, 0, RenderTextureFormat.ARGB32, RenderTextureReadWrite.Linear)
                { antiAliasing = 1, useMipMap = false, autoGenerateMips = false, filterMode = FilterMode.Point };
            var read = new Texture2D(width, height, TextureFormat.RGBA32, false, true);
            var mesh = Quad(); var material = new Material(shader) { enableInstancing = true }; var command = new CommandBuffer { name = "ByteFables graph qualification" };
            var previous = RenderTexture.active; bool previousSrgb = GL.sRGBWrite; int drawCalls = 0;
            long submitUs = 0, readbackUs = 0; byte[] actual = null;
            try
            {
                Require(target.Create(), "Graph qualification render target allocation failed");
                command.SetRenderTarget(target);
                command.ClearRenderTarget(false, true, new Color(0,0,0,0));
                var matrices = new Matrix4x4[BatchLimit];
                for (int i = 0; i < matrices.Length; i++) matrices[i] = Matrix4x4.identity;
                for (int bankIndex = 0; bankIndex < rects.Length; bankIndex++)
                {
                    var bankRects = rects[bankIndex]; if (bankRects.Count == 0) continue;
                    var bankLayers = layers[bankIndex]; var texture = imported.GetBank(bankIndex);
                    texture.filterMode = FilterMode.Point; texture.wrapMode = TextureWrapMode.Clamp;
                    for (int start = 0; start < bankRects.Count; start += BatchLimit)
                    {
                        int count = Math.Min(BatchLimit, bankRects.Count - start);
                        var r = bankRects.GetRange(start, count).ToArray();
                        var l = bankLayers.GetRange(start, count).ToArray();
                        var block = new MaterialPropertyBlock();
                        block.SetTexture("_Array", texture); block.SetFloat("_Mip", mip);
                        block.SetVectorArray("_Rect", r); block.SetFloatArray("_Layer", l);
                        command.DrawMeshInstanced(mesh, 0, material, 0, matrices, count, block);
                        drawCalls++;
                    }
                }
                var submit = Stopwatch.StartNew();
                GL.sRGBWrite = false;
                Graphics.ExecuteCommandBuffer(command);
                submit.Stop(); submitUs = Microseconds(submit.ElapsedTicks);

                var readback = Stopwatch.StartNew();
                RenderTexture.active = target;
                read.ReadPixels(new Rect(0,0,width,height), 0, 0, false);
                actual = read.GetPixelData<byte>(0).ToArray();
                readback.Stop(); readbackUs = Microseconds(readback.ElapsedTicks);
            }
            finally
            {
                RenderTexture.active = previous; GL.sRGBWrite = previousSrgb;
                command.Release(); target.Release();
                TextureArrayUpload.Destroy(material); TextureArrayUpload.Destroy(mesh);
                TextureArrayUpload.Destroy(target); TextureArrayUpload.Destroy(read);
            }
            Require(actual != null && actual.Length == expected.Length, "Graph framebuffer readback length mismatch");
            bool same = true;
            for (int i = 0; i < expected.Length; i++) if (expected[i] != actual[i]) { same = false; break; }
            Require(same, "Graph instancing framebuffer differs from exact source mip tiles");
            total.Stop();
            return new TextureGraphProbeResult {
                instances = instanceCount, uniqueSprites = Math.Min(instanceCount, data.Sprites.Count),
                banks = data.Banks.Count, drawCalls = drawCalls, mip = mip, width = width, height = height,
                pixelsCompared = width * height, submitMicroseconds = submitUs, readbackMicroseconds = readbackUs,
                totalMicroseconds = Microseconds(total.ElapsedTicks), exactPixels = true,
                expectedSha256 = TextureHashes.Sha256(expected), actualSha256 = TextureHashes.Sha256(actual),
            };
        }
    }
}
