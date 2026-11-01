using System;
using System.Collections;
using System.Diagnostics;
using System.IO;
using System.Text;
using ByteFables.Textures.Core;
using UnityEngine;
using UnityEngine.Rendering;

namespace ByteFables.Textures
{
    [Serializable]
    public sealed class CompressedTextureDeviceResult
    {
        public string schema = "bytefables.unity-compressed-device-qualification.v1";
        public string status, runId, editorVersion, profile, gpuManifestSha256, referenceManifestSha256, sourceManifestSha256, error;
        public string runtimePlatform, graphicsApi, graphicsDevice, graphicsDeviceVersion, operatingSystem, scriptingBackend, colourSpace, renderPipeline, formatId, orientation;
        public bool playerExecuted, gpuExecuted, formatSupported, arraySupported, readbackExecuted, shaderExecuted, productionQualified, isEditor;
        public int sprites, banks, levels, readbackComparisons, shaderComparisons, orientationComparisons, skipped;
        public double readbackMeanAbsoluteError, readbackPsnrDb, shaderMeanAbsoluteError, shaderPsnrDb;
        public double topLeftMeanAbsoluteError, bottomUpMeanAbsoluteError;
        public int readbackMaxAbsoluteError, shaderMaxAbsoluteError;
        public long elapsedMilliseconds;
    }

    public sealed class CompressedTextureDeviceQualification : MonoBehaviour
    {
        [SerializeField] private Shader arrayShader;
        [SerializeField] private string expectedRunId, expectedVersion, expectedProfile, expectedPlatform, expectedGraphicsApi, expectedFormatId;
        [SerializeField] private string expectedGpuManifest, expectedReferenceManifest, expectedSourceManifest;

        public void Configure(Shader shader, string runId, string version, string profile, string platform, string graphicsApi,
            string formatId, string gpuManifest, string referenceManifest, string sourceManifest)
        {
            arrayShader = shader; expectedRunId = runId; expectedVersion = version; expectedProfile = profile;
            expectedPlatform = platform; expectedGraphicsApi = graphicsApi; expectedFormatId = formatId;
            expectedGpuManifest = gpuManifest; expectedReferenceManifest = referenceManifest; expectedSourceManifest = sourceManifest;
        }

        private static void Require(bool yes, string message) { if (!yes) throw new TextureContractException(message); }

        private sealed class ErrorAccumulator
        {
            public long Samples; public double Absolute, Square; public int Maximum;
            public void Add(byte[] expected, byte[] actual)
            {
                Require(expected != null && actual != null && expected.Length == actual.Length, "Compressed comparison byte count mismatch");
                for (int i = 0; i < expected.Length; i++)
                {
                    int d = Math.Abs(expected[i] - actual[i]); Samples++; Absolute += d; Square += d * d; if (d > Maximum) Maximum = d;
                }
            }
            public double Mean { get { return Samples == 0 ? 0.0 : Absolute / Samples; } }
            public double Psnr
            {
                get
                {
                    if (Samples == 0 || Square == 0) return 999.0;
                    double mse = Square / Samples; return 20.0 * Math.Log10(255.0 / Math.Sqrt(mse));
                }
            }
        }

        private IEnumerator Start()
        {
            Application.runInBackground = true; var watch = Stopwatch.StartNew();
            var report = new CompressedTextureDeviceResult { runId = expectedRunId, profile = expectedProfile, formatId = expectedFormatId, isEditor = Application.isEditor };
            yield return null; Exception failure = null; var work = RunChecks(report);
            while (true)
            {
                bool more = false; try { more = work.MoveNext(); } catch (Exception error) { failure = error; }
                if (failure != null || !more) break; yield return work.Current;
            }
            try { (work as IDisposable)?.Dispose(); } catch (Exception error) { if (failure == null) failure = error; }
            report.elapsedMilliseconds = watch.ElapsedMilliseconds; report.status = failure == null ? "passed" : "failed"; report.error = failure == null ? null : failure.ToString();
            try
            {
                string path = Environment.GetEnvironmentVariable("BYTEFABLES_COMPRESSED_REPORT");
                Require(!string.IsNullOrEmpty(path) && Path.IsPathRooted(path), "Absolute fresh compressed-device report path required");
                using (var stream = new FileStream(path, FileMode.CreateNew, FileAccess.Write, FileShare.None))
                {
                    byte[] bytes = new UTF8Encoding(false).GetBytes(JsonUtility.ToJson(report, true)); stream.Write(bytes, 0, bytes.Length); stream.Flush(true);
                }
            }
            catch (Exception error) { failure = error; }
            if (failure != null) UnityEngine.Debug.LogException(failure); Application.Quit(failure == null ? 0 : 1);
        }

        private IEnumerator RunChecks(CompressedTextureDeviceResult report)
        {
            Require(!Application.isEditor, "Editor execution is not compressed-device evidence");
            Require(expectedRunId == Environment.GetEnvironmentVariable("BYTEFABLES_COMPRESSED_RUN_ID"), "Stale/substituted compressed player");
            report.editorVersion = Application.unityVersion; report.runtimePlatform = Application.platform.ToString(); report.graphicsApi = SystemInfo.graphicsDeviceType.ToString();
            report.graphicsDevice = SystemInfo.graphicsDeviceName; report.graphicsDeviceVersion = SystemInfo.graphicsDeviceVersion; report.operatingSystem = SystemInfo.operatingSystem;
            report.colourSpace = QualitySettings.activeColorSpace.ToString(); report.renderPipeline = GraphicsSettings.currentRenderPipeline == null ? "BuiltIn" : "SRP";
#if ENABLE_IL2CPP
            report.scriptingBackend = "IL2CPP";
#elif ENABLE_MONO
            report.scriptingBackend = "Mono";
#else
            report.scriptingBackend = "Unknown";
#endif
            Require(report.editorVersion == expectedVersion && report.runtimePlatform == expectedPlatform && report.graphicsApi == expectedGraphicsApi,
                "Compressed-device Unity/platform/API mismatch");
            Require(report.scriptingBackend == "IL2CPP" && report.colourSpace == "Linear" && report.renderPipeline == "BuiltIn",
                "Compressed-device v1 requires IL2CPP/Linear/Built-in");
            report.arraySupported = SystemInfo.supports2DArrayTextures; report.formatSupported = CompressedTextureFormatSelector.IsSupported(expectedFormatId);
            Require(report.arraySupported && report.formatSupported && SystemInfo.supportsAsyncGPUReadback && SystemInfo.graphicsDeviceType != GraphicsDeviceType.Null,
                "Requested compressed texture/readback capability is unavailable; no fallback/skip");
            Require(arrayShader != null && arrayShader.isSupported, "Compressed qualification shader missing or unsupported"); report.playerExecuted = true;

            string gpuPath = Path.Combine(Application.streamingAssetsPath, "ByteFablesGpuBlocks", "gpu.bfgpu");
            string referencePath = Path.Combine(Application.streamingAssetsPath, "ByteFablesReference", "artwork.bftextures");
            var blocks = GpuBlockTextureBundleDirectory.LoadDescriptor(gpuPath); var reference = TextureBundleDirectory.LoadDescriptor(referencePath);
            Require(blocks.ManifestSha256 == expectedGpuManifest && reference.ManifestSha256 == expectedReferenceManifest, "Compressed/reference manifest pin mismatch");
            Require(blocks.Sprites.Count == reference.Sprites.Count && blocks.NativeSize == reference.NativeSize, "Compressed/reference geometry mismatch");
            report.gpuManifestSha256 = blocks.ManifestSha256; report.referenceManifestSha256 = reference.ManifestSha256; report.sourceManifestSha256 = expectedSourceManifest;
            report.sprites = blocks.Sprites.Count; report.banks = blocks.FindFormat(expectedFormatId).Banks.Count; report.levels = reference.Banks[0].LevelCount;
            for (int i = 0; i < blocks.Sprites.Count; i++)
            {
                var a = blocks.Sprites[i]; var b = reference.Sprites[i]; Require(a.SpriteKey == b.SpriteKey && a.DigestHex == b.DigestHex && a.BankIndex == b.BankIndex && a.LayerIndex == b.LayerIndex,
                    "Compressed/reference identity mapping changed");
            }

            var readback = new ErrorAccumulator(); var top = new ErrorAccumulator(); var bottom = new ErrorAccumulator();
            int topVotes = 0, bottomVotes = 0;
            for (int bankIndex = 0; bankIndex < report.banks; bankIndex++)
            {
                var texture = CompressedTextureArrayUpload.Create(blocks, expectedFormatId, bankIndex, FilterMode.Point, keepReadable: false);
                try
                {
                    var original = reference.Banks[bankIndex];
                    for (int layer = 0; layer < original.Layers; layer++)
                    {
                        for (int mip = 0; mip < original.LevelCount; mip++)
                        {
                            int side = original.LevelSize(mip);
                            var request = AsyncGPUReadback.Request(texture, mip, 0, side, 0, side, layer, 1, TextureFormat.RGBA32);
                            request.WaitForCompletion(); Require(!request.hasError, "Compressed GPU readback failed"); var actual = request.GetData<byte>().ToArray();
                            var topExpected = original.CopyLayer(mip, layer, bottomUp: false); var bottomExpected = original.CopyLayer(mip, layer, bottomUp: true);
                            top.Add(topExpected, actual); bottom.Add(bottomExpected, actual); readback.Add(bottomExpected, actual); report.readbackComparisons++;
                            if (mip == 0 && OrientationSignal(topExpected, bottomExpected) > 1.0)
                            {
                                double tm = MeanAbsolute(topExpected, actual), bm = MeanAbsolute(bottomExpected, actual); report.orientationComparisons++;
                                if (bm < tm) bottomVotes++; else if (tm < bm) topVotes++;
                            }
                        }
                        yield return null;
                    }
                }
                finally { TextureArrayUpload.Destroy(texture); }
            }
            report.readbackExecuted = true; report.readbackMeanAbsoluteError = readback.Mean; report.readbackPsnrDb = readback.Psnr; report.readbackMaxAbsoluteError = readback.Maximum;
            report.topLeftMeanAbsoluteError = top.Mean; report.bottomUpMeanAbsoluteError = bottom.Mean;
            Require(report.orientationComparisons > 0, "Corpus contains no asymmetric orientation evidence");
            report.orientation = bottomVotes == report.orientationComparisons ? "bottom-up" : topVotes == report.orientationComparisons ? "top-left" :
                (topVotes == 0 && bottomVotes == 0 ? "ambiguous" : "mixed");

            var shaderMetrics = new ErrorAccumulator(); var material = new Material(arrayShader); int samples = Math.Min(16, blocks.Sprites.Count);
            try
            {
                using (var residency = new CompressedTextureArrayResidency(blocks, expectedFormatId, blocks.FindFormat(expectedFormatId).PayloadBytes))
                {
                    for (int sample = 0; sample < samples; sample++)
                    {
                        int spriteIndex = samples == 1 ? 0 : (int)Math.Round(sample * (blocks.Sprites.Count - 1.0) / (samples - 1.0));
                        var sprite = blocks.Sprites[spriteIndex]; using (var lease = residency.AcquireBank(sprite.BankIndex))
                        {
                            material.SetTexture("_Array", lease.Texture); material.SetFloat("_Layer", sprite.LayerIndex);
                            for (int mip = 0; mip < report.levels; mip++)
                            {
                                material.SetFloat("_Mip", mip); int side = reference.Banks[sprite.BankIndex].LevelSize(mip);
                                var expected = reference.Banks[sprite.BankIndex].CopyLayer(mip, sprite.LayerIndex, bottomUp: true);
                                foreach (var matte in new[] { new Color32(0,0,0,0), new Color32(0,0,0,255), new Color32(255,255,255,255) })
                                { shaderMetrics.Add(Composite(expected, matte), Draw(material, side, matte)); report.shaderComparisons++; }
                            }
                        }
                        yield return null;
                    }
                }
            }
            finally { TextureArrayUpload.Destroy(material); }
            report.shaderExecuted = true; report.shaderMeanAbsoluteError = shaderMetrics.Mean; report.shaderPsnrDb = shaderMetrics.Psnr; report.shaderMaxAbsoluteError = shaderMetrics.Maximum;
            report.productionQualified = report.orientation == "bottom-up"; report.gpuExecuted = true; yield return null;
        }

        private static double MeanAbsolute(byte[] a, byte[] b)
        { Require(a.Length == b.Length, "Orientation byte count mismatch"); double total = 0; for (int i=0;i<a.Length;i++) total += Math.Abs(a[i]-b[i]); return total / a.Length; }
        private static double OrientationSignal(byte[] top, byte[] bottom) { return MeanAbsolute(top, bottom); }
        private static byte[] Composite(byte[] source, Color32 matte)
        {
            var result = new byte[source.Length]; byte[] background = { matte.r, matte.g, matte.b, matte.a };
            for (int p = 0; p < source.Length; p += 4) for (int c = 0; c < 4; c++) result[p+c] = (byte)(source[p+c] + (background[c]*(255-source[p+3])+127)/255);
            return result;
        }
        private static byte[] Draw(Material material, int side, Color32 clear)
        {
            var target = new RenderTexture(side, side, 0, RenderTextureFormat.ARGB32, RenderTextureReadWrite.Linear) { antiAliasing=1,useMipMap=false,autoGenerateMips=false };
            var read = new Texture2D(side, side, TextureFormat.RGBA32, false, true); var previous = RenderTexture.active; bool srgb = GL.sRGBWrite;
            try
            {
                Require(target.Create(), "Compressed render target allocation failed"); RenderTexture.active = target; GL.sRGBWrite = false; GL.Clear(false,true,clear);
                Graphics.Blit(null,target,material,0); RenderTexture.active = target; read.ReadPixels(new Rect(0,0,side,side),0,0,false); return read.GetPixelData<byte>(0).ToArray();
            }
            finally { RenderTexture.active=previous;GL.sRGBWrite=srgb;target.Release();TextureArrayUpload.Destroy(target);TextureArrayUpload.Destroy(read); }
        }
    }
}
