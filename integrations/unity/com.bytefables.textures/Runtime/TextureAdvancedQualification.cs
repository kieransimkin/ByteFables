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
    public sealed class TextureAdvancedResult
    {
        public string schema = "bytefables.unity-advanced-player-qualification.v1";
        public string status, runId, editorVersion, profile, manifestSha256, sentinelManifestSha256, error;
        public string runtimePlatform, graphicsApi, graphicsDevice, graphicsDeviceVersion, operatingSystem;
        public string scriptingBackend, colourSpace, renderPipeline;
        public bool playerExecuted, gpuExecuted, serializedAssetsExecuted, syntheticSentinelsExecuted;
        public bool disposalExecuted, graphExecuted, isEditor;
        public int banks, sprites, cpuComparisons, gpuComparisons, shaderComparisons;
        public int bindingComparisons, overlapComparisons, skipped;
        public int overlapByteTolerance = 1;
        public TextureGraphProbeResult[] graphResults;
        public long elapsedMilliseconds;
    }

    /// <summary>Advanced isolated-player acceptance. Never auto-starts in ordinary projects.</summary>
    public sealed class TextureAdvancedQualification : MonoBehaviour
    {
        [SerializeField] private TextureBundleAsset actual, sentinel;
        [SerializeField] private Shader arrayShader, graphShader;
        [SerializeField] private string expectedRunId, expectedVersion, expectedProfile;
        [SerializeField] private string expectedManifest, expectedSentinelManifest;
        [SerializeField] private string expectedPlatform, expectedGraphicsApi;
        [SerializeField] private string expectedScriptingBackend, expectedColourSpace, expectedRenderPipeline;
        [SerializeField] private int[] graphCounts;

        public void Configure(TextureBundleAsset artwork, TextureBundleAsset probes, Shader shader, Shader instancedShader,
            string runId, string version, string profile, string manifest, string sentinelManifest,
            string platform, string graphicsApi, string scriptingBackend, string colourSpace,
            string renderPipeline, int[] counts)
        {
            actual = artwork; sentinel = probes; arrayShader = shader; graphShader = instancedShader;
            expectedRunId = runId; expectedVersion = version; expectedProfile = profile;
            expectedManifest = manifest; expectedSentinelManifest = sentinelManifest;
            expectedPlatform = platform; expectedGraphicsApi = graphicsApi;
            expectedScriptingBackend = scriptingBackend; expectedColourSpace = colourSpace;
            expectedRenderPipeline = renderPipeline; graphCounts = counts == null ? null : (int[])counts.Clone();
        }

        private static void Require(bool condition, string message)
        { if (!condition) throw new TextureContractException(message); }

        private IEnumerator Start()
        {
            Application.runInBackground = true;
            var watch = Stopwatch.StartNew();
            var report = new TextureAdvancedResult { runId = expectedRunId, profile = expectedProfile, isEditor = Application.isEditor };
            yield return null;
            var work = RunChecks(report); Exception failure = null;
            while (true)
            {
                bool more = false;
                try { more = work.MoveNext(); }
                catch (Exception error) { failure = error; }
                if (failure != null || !more) break;
                yield return work.Current;
            }
            try { (work as IDisposable)?.Dispose(); }
            catch (Exception error) { if (failure == null) failure = error; }
            report.elapsedMilliseconds = watch.ElapsedMilliseconds;
            report.status = failure == null ? "passed" : "failed";
            report.error = failure == null ? null : failure.ToString();
            try
            {
                string path = Environment.GetEnvironmentVariable("BYTEFABLES_ADVANCED_REPORT");
                Require(!string.IsNullOrEmpty(path) && Path.IsPathRooted(path), "An absolute fresh advanced report path is required");
                using (var stream = new FileStream(path, FileMode.CreateNew, FileAccess.Write, FileShare.None))
                {
                    byte[] bytes = new UTF8Encoding(false).GetBytes(JsonUtility.ToJson(report, true));
                    stream.Write(bytes, 0, bytes.Length); stream.Flush(true);
                }
            }
            catch (Exception error) { failure = error; }
            if (failure != null) UnityEngine.Debug.LogException(failure);
            Application.Quit(failure == null ? 0 : 1);
        }

        private IEnumerator RunChecks(TextureAdvancedResult report)
        {
            Require(!Application.isEditor, "Editor execution is not advanced player qualification");
            Require(expectedRunId == Environment.GetEnvironmentVariable("BYTEFABLES_ADVANCED_RUN_ID"),
                "Stale or substituted advanced player executable");
            Require(expectedProfile == "windows-d3d11-il2cpp-linear" || expectedProfile == "windows-d3d12-il2cpp-linear" ||
                expectedProfile == "linux-vulkan-il2cpp-linear", "Unknown advanced profile");
            Require(graphCounts != null && graphCounts.Length >= 1 && graphCounts.Length <= 3,
                "Advanced profile requires bounded graph counts");
            for (int i = 0; i < graphCounts.Length; i++)
                Require(graphCounts[i] >= 1 && graphCounts[i] <= 10000 && (i == 0 || graphCounts[i] > graphCounts[i-1]),
                    "Graph counts must be strictly increasing in 1..10000");

            report.editorVersion = Application.unityVersion;
            report.runtimePlatform = Application.platform.ToString();
            report.graphicsApi = SystemInfo.graphicsDeviceType.ToString();
            report.graphicsDevice = SystemInfo.graphicsDeviceName;
            report.graphicsDeviceVersion = SystemInfo.graphicsDeviceVersion;
            report.operatingSystem = SystemInfo.operatingSystem;
            report.colourSpace = QualitySettings.activeColorSpace.ToString();
            report.renderPipeline = GraphicsSettings.currentRenderPipeline == null ? "BuiltIn" : "SRP";
#if ENABLE_IL2CPP
            report.scriptingBackend = "IL2CPP";
#elif ENABLE_MONO
            report.scriptingBackend = "Mono";
#else
            report.scriptingBackend = "Unknown";
#endif
            Require(report.editorVersion == expectedVersion && report.runtimePlatform == expectedPlatform,
                "Wrong Unity version or runtime platform");
            Require(report.graphicsApi == expectedGraphicsApi && SystemInfo.graphicsDeviceType != GraphicsDeviceType.Null &&
                SystemInfo.supports2DArrayTextures && SystemInfo.supportsAsyncGPUReadback && SystemInfo.supportsInstancing,
                "Requested graphics API with array/readback/instancing support is required; no fallback/skip");
            Require(report.scriptingBackend == expectedScriptingBackend && report.scriptingBackend == "IL2CPP",
                "Advanced profile requires a real IL2CPP player");
            Require(report.colourSpace == expectedColourSpace && report.colourSpace == "Linear",
                "Advanced profile requires active Linear colour space");
            Require(report.renderPipeline == expectedRenderPipeline && report.renderPipeline == "BuiltIn",
                "This advanced version isolates IL2CPP/Linear under Built-in rendering");
            Require(arrayShader != null && arrayShader.isSupported && graphShader != null && graphShader.isSupported,
                "Serialized qualification shaders were stripped or unsupported");
            report.playerExecuted = true;

            var data = TextureBundleDirectory.LoadDescriptor(Path.Combine(Application.streamingAssetsPath, "ByteFablesFixture/artwork.bftextures"));
            var probes = TextureBundleDirectory.LoadDescriptor(Path.Combine(Application.streamingAssetsPath, "ByteFablesSentinel/artwork.bftextures"));
            Require(data.ManifestSha256 == expectedManifest && probes.ManifestSha256 == expectedSentinelManifest,
                "Bundled StreamingAssets source differs from advanced build pins");
            Require(probes.NativeSize == 16 && probes.Sprites.Count == 4, "Wrong orientation/alpha probe corpus");
            report.manifestSha256 = data.ManifestSha256; report.sentinelManifestSha256 = probes.ManifestSha256;
            report.banks = data.Banks.Count; report.sprites = data.Sprites.Count;

            var baseReport = new TexturePlayerResult();
            var checks = TexturePlayerReadback.Qualify(actual, data, arrayShader, baseReport);
            try { while (checks.MoveNext()) yield return checks.Current; }
            finally { (checks as IDisposable)?.Dispose(); }
            checks = TexturePlayerReadback.Qualify(sentinel, probes, arrayShader, baseReport);
            try { while (checks.MoveNext()) yield return checks.Current; }
            finally { (checks as IDisposable)?.Dispose(); }
            report.serializedAssetsExecuted = true;
            TexturePlayerReadback.Overlap(probes, arrayShader, baseReport);
            report.syntheticSentinelsExecuted = true;
            report.cpuComparisons = baseReport.cpuComparisons; report.gpuComparisons = baseReport.gpuComparisons;
            report.shaderComparisons = baseReport.shaderComparisons; report.bindingComparisons = baseReport.bindingComparisons;
            report.overlapComparisons = baseReport.overlapComparisons; report.overlapByteTolerance = baseReport.overlapByteTolerance;

            var owner = new UploadedTextureBundle(probes); owner.Dispose(); owner.Dispose();
            bool disposed = false; try { owner.GetBank(0); } catch (ObjectDisposedException) { disposed = true; }
            Require(disposed, "Disposed runtime bundle remained usable"); report.disposalExecuted = true;

            report.graphResults = new TextureGraphProbeResult[graphCounts.Length];
            for (int i = 0; i < graphCounts.Length; i++)
            {
                report.graphResults[i] = TextureGraphBenchmark.Run(actual, data, graphShader, graphCounts[i]);
                yield return null;
            }
            report.graphExecuted = true; report.gpuExecuted = true;
            yield return null;
        }
    }
}
