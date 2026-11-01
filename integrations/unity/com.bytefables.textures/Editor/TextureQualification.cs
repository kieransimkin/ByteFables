using System;
using System.Diagnostics;
using System.IO;
using ByteFables.Textures.Core;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

namespace ByteFables.Textures.Editor
{
    /// <summary>Synchronous executeMethod acceptance gate; no NUnit package, license automation or GPU skip.</summary>
    public static class TextureQualification
    {
        [Serializable]
        private sealed class Report
        {
            public string schema = "bytefables.unity-qualification.v1";
            public string status, editorVersion, graphicsApi, graphicsDevice, manifestSha256, error;
            public int banks, sprites, cpuComparisons, gpuComparisons, shaderComparisons, overlapComparisons, skipped;
            public long elapsedMilliseconds;
            public bool unityExecuted = true, gpuExecuted, syntheticSentinelsExecuted;
            public int overlapByteTolerance = 1;
        }
        private static void Require(bool condition, string message)
        { if (!condition) throw new TextureContractException(message); }
        private static void Same(byte[] expected, byte[] actual, string label, int tolerance = 0)
        {
            Require(expected.Length == actual.Length, label + ": wrong byte count");
            for (int i = 0; i < expected.Length; i++)
                Require(Math.Abs(expected[i] - actual[i]) <= tolerance, label + ": pixel byte mismatch at " + i);
        }
        public static void RunFromCommandLine()
        {
            string reportPath = Environment.GetEnvironmentVariable("BYTEFABLES_UNITY_REPORT");
            var watch = Stopwatch.StartNew(); var report = new Report();
            try
            {
                Require(!string.IsNullOrEmpty(reportPath) && !File.Exists(reportPath), "Fresh report path required");
                Directory.SetCurrentDirectory(Path.GetDirectoryName(Application.dataPath));
                report.editorVersion = Application.unityVersion;
                Require(report.editorVersion == Environment.GetEnvironmentVariable("BYTEFABLES_UNITY_EDITOR_VERSION"), "Editor version differs from requested qualification baseline");
                report.graphicsApi = SystemInfo.graphicsDeviceType.ToString(); report.graphicsDevice = SystemInfo.graphicsDeviceName;
                Require(SystemInfo.graphicsDeviceType != GraphicsDeviceType.Null && SystemInfo.supports2DArrayTextures && SystemInfo.supportsAsyncGPUReadback,
                    "A real texture-array graphics device with GPU readback is required; this test cannot skip");
                string descriptor = Environment.GetEnvironmentVariable("BYTEFABLES_UNITY_DESCRIPTOR");
                string sentinel = Environment.GetEnvironmentVariable("BYTEFABLES_UNITY_SENTINEL");
                Require(!string.IsNullOrEmpty(descriptor) && !string.IsNullOrEmpty(sentinel), "Actual and synthetic descriptors required");
                var data = TextureBundleDirectory.LoadDescriptor(descriptor);
                report.manifestSha256 = data.ManifestSha256; report.banks = data.Banks.Count; report.sprites = data.Sprites.Count;
                Qualify(descriptor, data, report);
                var sentinels = TextureBundleDirectory.LoadDescriptor(sentinel);
                Require(sentinels.Sprites.Count == 4 && sentinels.NativeSize == 16, "Wrong synthetic sentinel corpus");
                Qualify(sentinel, sentinels, report);
                Overlap(sentinels, report);
                // Runtime ownership must not retain usable arrays after disposal.
                var owner = new UploadedTextureBundle(sentinels); owner.Dispose(); owner.Dispose();
                bool disposed = false; try { owner.GetBank(0); } catch (ObjectDisposedException) { disposed = true; }
                Require(disposed, "Disposed bundle remained usable");
                report.gpuExecuted = true; report.syntheticSentinelsExecuted = true; report.status = "passed";
                report.elapsedMilliseconds = watch.ElapsedMilliseconds;
                File.WriteAllText(reportPath, JsonUtility.ToJson(report, true));
                UnityEngine.Debug.Log("ByteFables Unity qualification passed: " + reportPath);
            }
            catch (Exception error)
            {
                report.status = "failed"; report.error = error.ToString(); report.elapsedMilliseconds = watch.ElapsedMilliseconds;
                if (!string.IsNullOrEmpty(reportPath) && !File.Exists(reportPath)) File.WriteAllText(reportPath, JsonUtility.ToJson(report, true));
                UnityEngine.Debug.LogException(error); EditorApplication.Exit(1);
            }
        }
        private static void Qualify(string descriptor, TextureBundleData data, Report report)
        {
            // The runner stages descriptors under Assets. Test the actual ScriptedImporter, not a mock.
            Require(descriptor.StartsWith("Assets/", StringComparison.Ordinal), "Qualification descriptor must be in the project Assets folder");
            AssetDatabase.ImportAsset(descriptor, ImportAssetOptions.ForceSynchronousImport | ImportAssetOptions.ForceUpdate);
            var imported = AssetDatabase.LoadAssetAtPath<TextureBundleAsset>(descriptor);
            Require(imported != null && imported.ManifestSha256 == data.ManifestSha256 && imported.SpriteCount == data.Sprites.Count && imported.BankCount == data.Banks.Count,
                "Imported main asset differs from verified source");
            for (int i = 0; i < data.Sprites.Count; i++)
            {
                var binding = imported.Find(data.Sprites[i].SpriteKey);
                Require(binding.DigestHex == data.Sprites[i].DigestHex && binding.BankIndex == data.Sprites[i].BankIndex && binding.LayerIndex == data.Sprites[i].LayerIndex,
                    "Serialized identity binding changed");
            }
            var shader = Shader.Find("ByteFables/Premultiplied Array");
            Require(shader != null && shader.isSupported, "Array shader is missing or unsupported");
            var material = new Material(shader);
            try
            {
                for (int bank = 0; bank < data.Banks.Count; bank++)
                {
                    var original = data.Banks[bank];
                    var cpu = TextureArrayUpload.Create(original, FilterMode.Point, keepReadable: true);
                    var gpu = imported.GetBank(bank); gpu.filterMode = FilterMode.Point;
                    Require(!gpu.isReadable && gpu.mipmapCount == original.LevelCount && gpu.depth == original.Layers, "Imported bank settings changed");
                    try
                    {
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
        private static void Overlap(TextureBundleData sentinel, Report report)
        {
            using (var uploaded = new UploadedTextureBundle(sentinel))
            {
                var material = new Material(Shader.Find("ByteFables/Premultiplied Array"));
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
