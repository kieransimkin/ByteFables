using System;
using System.Diagnostics;
using System.IO;
using System.Text;
using ByteFables.Textures.Core;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;

namespace ByteFables.Textures.Editor
{
    /// <summary>Builds only a runner-owned fresh project. It does not alter an existing user's project.</summary>
    public static class TexturePlayerBuild
    {
        [Serializable]
        private sealed class Request
        {
            public string schema, runId, editorVersion, target, runtimePlatform, graphicsApi;
            public string scriptingBackend, colourSpace, renderPipeline, manifestSha256, sentinelManifestSha256;
            public string buildPath, buildReportPath;
        }
        [Serializable]
        private sealed class Result
        {
            public string schema = "bytefables.unity-player-build.v1";
            public string status, runId, editorVersion, target, graphicsApi, scriptingBackend, colourSpace, renderPipeline;
            public string manifestSha256, sentinelManifestSha256, error;
            public bool buildSucceeded, developmentBuild;
            public int errors;
            public long elapsedMilliseconds;
            public ulong totalSize;
        }
        private static void Require(bool condition, string message)
        { if (!condition) throw new TextureContractException(message); }

        private static bool SamePath(string a, string b)
        {
            var comparison = Environment.OSVersion.Platform == PlatformID.Win32NT
                ? StringComparison.OrdinalIgnoreCase : StringComparison.Ordinal;
            return string.Equals(Path.GetFullPath(a), Path.GetFullPath(b), comparison);
        }

        public static void RunFromCommandLine()
        {
            var result = new Result(); var watch = Stopwatch.StartNew(); Request request = null; string safeReportPath = null;
            try
            {
                string requestPath = Environment.GetEnvironmentVariable("BYTEFABLES_PLAYER_REQUEST");
                string projectRoot = Path.GetFullPath(Path.Combine(Application.dataPath, ".."));
                Require(SamePath(requestPath, Path.Combine(projectRoot, "player-request.json")), "Runner-owned request required");
                Require(new FileInfo(requestPath).Length <= 16384, "Build request too large");
                Directory.SetCurrentDirectory(projectRoot);
                request = JsonUtility.FromJson<Request>(File.ReadAllText(requestPath));
                Require(request.schema == "bytefables.unity-player-request.v1" &&
                    System.Text.RegularExpressions.Regex.IsMatch(request.runId ?? "", "^[a-f0-9]{32}$"), "Invalid request");
                Require(request.editorVersion == Application.unityVersion, "Unity version differs from pinned build request");
                bool monoGamma = request.scriptingBackend == "Mono" && request.colourSpace == "Gamma";
                bool il2cppLinear = request.scriptingBackend == "IL2CPP" && request.colourSpace == "Linear";
                Require((monoGamma || il2cppLinear) && request.renderPipeline == "BuiltIn",
                    "Only Built-in/Gamma/Mono and Built-in/Linear/IL2CPP desktop profiles are defined");
                bool windows = request.target == "StandaloneWindows64";
                Require(windows || request.target == "StandaloneLinux64", "Unsupported target");
                Require(Application.platform == (windows ? RuntimePlatform.WindowsEditor : RuntimePlatform.LinuxEditor), "Native build-and-run host required");
                Require(request.runtimePlatform == (windows ? "WindowsPlayer" : "LinuxPlayer") &&
                    request.graphicsApi == (windows ? "Direct3D11" : "Vulkan"), "Target/API mismatch");
                var target = windows ? BuildTarget.StandaloneWindows64 : BuildTarget.StandaloneLinux64;
                var graphics = windows ? GraphicsDeviceType.Direct3D11 : GraphicsDeviceType.Vulkan;
                Require(EditorUserBuildSettings.activeBuildTarget == target, "Start Unity with the requested -buildTarget");
                Require(BuildPipeline.IsBuildTargetSupported(BuildTargetGroup.Standalone, target), "Required desktop build module is missing");
                string outputRoot = Path.GetDirectoryName(projectRoot);
                string expectedBuildPath = Path.Combine(outputRoot, "player", windows ? "ByteFablesPlayer.exe" : "ByteFablesPlayer.x86_64");
                Require(SamePath(request.buildPath, expectedBuildPath) &&
                    SamePath(request.buildReportPath, Path.Combine(outputRoot, "build-result.json")) &&
                    !Directory.Exists(Path.GetDirectoryName(expectedBuildPath)) && !File.Exists(request.buildReportPath), "Fresh isolated build outputs required");
                safeReportPath = Path.Combine(outputRoot, "build-result.json");
                var backend = il2cppLinear ? ScriptingImplementation.IL2CPP : ScriptingImplementation.Mono2x;
                PlayerSettings.SetScriptingBackend(NamedBuildTarget.Standalone, backend);
                Require(PlayerSettings.GetScriptingBackend(NamedBuildTarget.Standalone) == backend,
                    "Requested scripting backend did not persist");
                PlayerSettings.SetUseDefaultGraphicsAPIs(target, false);
                PlayerSettings.SetGraphicsAPIs(target, new[] { graphics });
                var colourSpace = il2cppLinear ? ColorSpace.Linear : ColorSpace.Gamma;
                PlayerSettings.colorSpace = colourSpace;
                Require(PlayerSettings.colorSpace == colourSpace, "Requested colour space did not persist");
                PlayerSettings.runInBackground = true;
                GraphicsSettings.defaultRenderPipeline = null; QualitySettings.renderPipeline = null;
                AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
                const string actualPath = "Assets/ByteFablesFixture/artwork.bftextures";
                const string sentinelPath = "Assets/ByteFablesSentinel/artwork.bftextures";
                AssetDatabase.ImportAsset(actualPath, ImportAssetOptions.ForceSynchronousImport | ImportAssetOptions.ForceUpdate);
                AssetDatabase.ImportAsset(sentinelPath, ImportAssetOptions.ForceSynchronousImport | ImportAssetOptions.ForceUpdate);
                var actual = AssetDatabase.LoadAssetAtPath<TextureBundleAsset>(actualPath);
                var sentinel = AssetDatabase.LoadAssetAtPath<TextureBundleAsset>(sentinelPath);
                Require(actual != null && actual.ManifestSha256 == request.manifestSha256 &&
                    sentinel != null && sentinel.ManifestSha256 == request.sentinelManifestSha256, "Import did not match requested source");
                var shader = AssetDatabase.LoadAssetAtPath<Shader>("Packages/com.bytefables.textures/Shaders/PremultipliedArray.shader");
                Require(shader != null, "Package shader missing");
                var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
                var probe = new GameObject("ByteFables standalone acceptance").AddComponent<TexturePlayerQualification>();
                probe.Configure(actual, sentinel, shader, request.runId, request.editorVersion, request.manifestSha256,
                    request.sentinelManifestSha256, request.runtimePlatform, request.graphicsApi,
                    request.scriptingBackend, request.colourSpace, request.renderPipeline);
                const string scenePath = "Assets/ByteFablesPlayer.unity";
                Require(EditorSceneManager.SaveScene(scene, scenePath), "Could not save qualification scene");
                AssetDatabase.SaveAssets();
                Directory.CreateDirectory(Path.GetDirectoryName(expectedBuildPath));
                var build = BuildPipeline.BuildPlayer(new BuildPlayerOptions {
                    scenes = new[] { scenePath }, locationPathName = expectedBuildPath, target = target,
                    subtarget = (int)StandaloneBuildSubtarget.Player, options = BuildOptions.None });
                result.runId = request.runId; result.editorVersion = Application.unityVersion; result.target = request.target;
                result.manifestSha256 = request.manifestSha256; result.sentinelManifestSha256 = request.sentinelManifestSha256;
                result.graphicsApi = request.graphicsApi; result.scriptingBackend = request.scriptingBackend;
                result.colourSpace = request.colourSpace; result.renderPipeline = request.renderPipeline;
                result.errors = checked((int)build.summary.totalErrors); result.totalSize = build.summary.totalSize;
                result.developmentBuild = (build.summary.options & BuildOptions.Development) != 0;
                result.buildSucceeded = build.summary.result == BuildResult.Succeeded;
                Require(result.buildSucceeded && result.errors == 0 && File.Exists(expectedBuildPath), "Player build failed");
                result.status = "passed";
            }
            catch (Exception error)
            {
                result.status = "failed"; result.error = error.ToString();
                UnityEngine.Debug.LogException(error);
            }
            result.elapsedMilliseconds = watch.ElapsedMilliseconds;
            try
            {
                if (safeReportPath != null)
                    using (var stream = new FileStream(safeReportPath, FileMode.CreateNew, FileAccess.Write, FileShare.None))
                    {
                        byte[] bytes = new UTF8Encoding(false).GetBytes(JsonUtility.ToJson(result, true));
                        stream.Write(bytes, 0, bytes.Length); stream.Flush(true);
                    }
            }
            catch (Exception error) { result.status = "failed"; UnityEngine.Debug.LogException(error); }
            if (result.status != "passed") EditorApplication.Exit(1);
        }
    }
}
