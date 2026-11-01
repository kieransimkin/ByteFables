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
    public sealed class TexturePlayerResult
    {
        public string schema = "bytefables.unity-player-qualification.v1";
        public string status, runId, editorVersion, manifestSha256, sentinelManifestSha256, error;
        public string runtimePlatform, graphicsApi, graphicsDevice, graphicsDeviceVersion, operatingSystem;
        public string scriptingBackend, colourSpace, renderPipeline;
        public bool playerExecuted, gpuExecuted, serializedAssetsExecuted, syntheticSentinelsExecuted, disposalExecuted, isEditor;
        public int banks, sprites, cpuComparisons, gpuComparisons, shaderComparisons, bindingComparisons, overlapComparisons, skipped;
        public int overlapByteTolerance = 1;
        public long elapsedMilliseconds;
    }

    /// <summary>Only attached to the isolated qualification scene. Never auto-starts in ordinary user projects.</summary>
    public sealed class TexturePlayerQualification : MonoBehaviour
    {
        [SerializeField] private TextureBundleAsset actual, sentinel;
        [SerializeField] private Shader arrayShader;
        [SerializeField] private string expectedRunId, expectedVersion, expectedManifest, expectedSentinelManifest;
        [SerializeField] private string expectedPlatform, expectedGraphicsApi;
        [SerializeField] private string expectedScriptingBackend, expectedColourSpace, expectedRenderPipeline;

        public void Configure(TextureBundleAsset artwork, TextureBundleAsset probes, Shader shader,
            string runId, string version, string manifest, string sentinelManifest, string platform, string graphicsApi,
            string scriptingBackend, string colourSpace, string renderPipeline)
        {
            actual = artwork; sentinel = probes; arrayShader = shader;
            expectedRunId = runId; expectedVersion = version; expectedManifest = manifest;
            expectedSentinelManifest = sentinelManifest; expectedPlatform = platform; expectedGraphicsApi = graphicsApi;
            expectedScriptingBackend = scriptingBackend; expectedColourSpace = colourSpace;
            expectedRenderPipeline = renderPipeline;
        }

        private static void Require(bool condition, string message)
        { if (!condition) throw new TextureContractException(message); }

        private IEnumerator Start()
        {
            Application.runInBackground = true;
            var watch = Stopwatch.StartNew();
            var report = new TexturePlayerResult { runId = expectedRunId, isEditor = Application.isEditor };
            // Give the player its first frame; WaitForEndOfFrame is intentionally not used in batch mode.
            yield return null;
            var work = RunChecks(report);
            Exception failure = null;
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
                string path = Environment.GetEnvironmentVariable("BYTEFABLES_PLAYER_REPORT");
                Require(!string.IsNullOrEmpty(path) && Path.IsPathRooted(path), "An absolute fresh player report path is required");
                // Do not overwrite even a failed or stale report. The runner owns the output directory.
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

        private IEnumerator RunChecks(TexturePlayerResult report)
        {
            Require(!Application.isEditor, "Editor execution is not player qualification");
            Require(expectedRunId == Environment.GetEnvironmentVariable("BYTEFABLES_PLAYER_RUN_ID"), "Stale or substituted player executable");
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
                SystemInfo.supports2DArrayTextures && SystemInfo.supportsAsyncGPUReadback,
                "Requested graphics API with array/readback support is required; no fallback/skip");
            Require(report.colourSpace == expectedColourSpace && report.renderPipeline == expectedRenderPipeline &&
                report.scriptingBackend == expectedScriptingBackend,
                "Runtime scripting backend, colour space or render pipeline differs from the pinned profile");
            Require(arrayShader != null && arrayShader.isSupported, "Serialized array shader was stripped or is unsupported");
            report.playerExecuted = true;
            var data = TextureBundleDirectory.LoadDescriptor(Path.Combine(Application.streamingAssetsPath, "ByteFablesFixture/artwork.bftextures"));
            var probes = TextureBundleDirectory.LoadDescriptor(Path.Combine(Application.streamingAssetsPath, "ByteFablesSentinel/artwork.bftextures"));
            Require(data.ManifestSha256 == expectedManifest && probes.ManifestSha256 == expectedSentinelManifest,
                "Bundled StreamingAssets source differs from build pins");
            Require(probes.NativeSize == 16 && probes.Sprites.Count == 4, "Wrong orientation/alpha probe corpus");
            report.manifestSha256 = data.ManifestSha256; report.sentinelManifestSha256 = probes.ManifestSha256;
            report.banks = data.Banks.Count; report.sprites = data.Sprites.Count;
            var checks = TexturePlayerReadback.Qualify(actual, data, arrayShader, report);
            try { while (checks.MoveNext()) yield return checks.Current; }
            finally { (checks as IDisposable)?.Dispose(); }
            checks = TexturePlayerReadback.Qualify(sentinel, probes, arrayShader, report);
            try { while (checks.MoveNext()) yield return checks.Current; }
            finally { (checks as IDisposable)?.Dispose(); }
            report.serializedAssetsExecuted = true;
            TexturePlayerReadback.Overlap(probes, arrayShader, report);
            report.syntheticSentinelsExecuted = true;
            var owner = new UploadedTextureBundle(probes);
            owner.Dispose(); owner.Dispose();
            bool disposed = false;
            try { owner.GetBank(0); } catch (ObjectDisposedException) { disposed = true; }
            Require(disposed, "Disposed runtime bundle remained usable");
            report.disposalExecuted = true; report.gpuExecuted = true;
            yield return null;
        }
    }
}
