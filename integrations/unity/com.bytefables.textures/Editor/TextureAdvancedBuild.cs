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
    /// <summary>Builds the isolated IL2CPP/Linear advanced qualification player.</summary>
    public static class TextureAdvancedBuild
    {
        [Serializable]
        private sealed class Request
        {
            public string schema, runId, editorVersion, profile, target, runtimePlatform, graphicsApi;
            public string scriptingBackend, colourSpace, renderPipeline, manifestSha256, sentinelManifestSha256;
            public string buildPath, buildReportPath;
            public int[] graphCounts;
        }
        [Serializable]
        private sealed class Result
        {
            public string schema = "bytefables.unity-advanced-player-build.v1";
            public string status, runId, editorVersion, profile, target, graphicsApi, scriptingBackend, colourSpace, renderPipeline;
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
                string requestPath = Environment.GetEnvironmentVariable("BYTEFABLES_ADVANCED_REQUEST");
                string projectRoot = Path.GetFullPath(Path.Combine(Application.dataPath, ".."));
                Require(SamePath(requestPath, Path.Combine(projectRoot, "advanced-player-request.json")), "Runner-owned advanced request required");
                Require(new FileInfo(requestPath).Length <= 16384, "Advanced build request too large");
                Directory.SetCurrentDirectory(projectRoot);
                request = JsonUtility.FromJson<Request>(File.ReadAllText(requestPath));
                Require(request.schema == "bytefables.unity-advanced-player-request.v1" &&
                    System.Text.RegularExpressions.Regex.IsMatch(request.runId ?? "", "^[a-f0-9]{32}$"), "Invalid advanced request");
                Require(request.editorVersion == Application.unityVersion, "Unity version differs from pinned advanced request");
                Require(request.scriptingBackend == "IL2CPP" && request.colourSpace == "Linear" && request.renderPipeline == "BuiltIn",
                    "Advanced v1 is specifically Built-in/Linear/IL2CPP");
                Require(request.profile == "windows-d3d11-il2cpp-linear" || request.profile == "windows-d3d12-il2cpp-linear" ||
                    request.profile == "linux-vulkan-il2cpp-linear", "Unsupported advanced profile");
                Require(request.graphCounts != null && request.graphCounts.Length >= 1 && request.graphCounts.Length <= 3,
                    "Advanced graph workload count missing");
                for (int i = 0; i < request.graphCounts.Length; i++)
                    Require(request.graphCounts[i] >= 1 && request.graphCounts[i] <= 10000 &&
                        (i == 0 || request.graphCounts[i] > request.graphCounts[i-1]), "Invalid graph workload counts");

                bool windows = request.target == "StandaloneWindows64";
                Require(windows || request.target == "StandaloneLinux64", "Unsupported advanced target");
                Require(Application.platform == (windows ? RuntimePlatform.WindowsEditor : RuntimePlatform.LinuxEditor),
                    "Native advanced build-and-run host required");
                Require(request.runtimePlatform == (windows ? "WindowsPlayer" : "LinuxPlayer"), "Advanced runtime platform mismatch");
                var target = windows ? BuildTarget.StandaloneWindows64 : BuildTarget.StandaloneLinux64;
                GraphicsDeviceType graphics;
                if (!windows)
                {
                    Require(request.graphicsApi == "Vulkan" && request.profile == "linux-vulkan-il2cpp-linear", "Advanced Linux API mismatch");
                    graphics = GraphicsDeviceType.Vulkan;
                }
                else if (request.graphicsApi == "Direct3D11" && request.profile == "windows-d3d11-il2cpp-linear")
                    graphics = GraphicsDeviceType.Direct3D11;
                else if (request.graphicsApi == "Direct3D12" && request.profile == "windows-d3d12-il2cpp-linear")
                    graphics = GraphicsDeviceType.Direct3D12;
                else throw new TextureContractException("Advanced Windows API/profile mismatch");
                Require(EditorUserBuildSettings.activeBuildTarget == target, "Start Unity with the requested advanced -buildTarget");
                Require(BuildPipeline.IsBuildTargetSupported(BuildTargetGroup.Standalone, target), "Required desktop build module is missing");

                string outputRoot = Path.GetDirectoryName(projectRoot);
                string expectedBuildPath = Path.Combine(outputRoot, "player", windows ? "ByteFablesAdvanced.exe" : "ByteFablesAdvanced.x86_64");
                Require(SamePath(request.buildPath, expectedBuildPath) &&
                    SamePath(request.buildReportPath, Path.Combine(outputRoot, "build-result.json")) &&
                    !Directory.Exists(Path.GetDirectoryName(expectedBuildPath)) && !File.Exists(request.buildReportPath),
                    "Fresh isolated advanced build outputs required");
                safeReportPath = Path.Combine(outputRoot, "build-result.json");

                PlayerSettings.SetScriptingBackend(NamedBuildTarget.Standalone, ScriptingImplementation.IL2CPP);
                Require(PlayerSettings.GetScriptingBackend(NamedBuildTarget.Standalone) == ScriptingImplementation.IL2CPP,
                    "Unity did not accept IL2CPP backend");
                PlayerSettings.SetUseDefaultGraphicsAPIs(target, false);
                PlayerSettings.SetGraphicsAPIs(target, new[] { graphics });
                PlayerSettings.colorSpace = ColorSpace.Linear;
                Require(PlayerSettings.colorSpace == ColorSpace.Linear, "Unity did not accept Linear colour space");
                PlayerSettings.runInBackground = true;
                GraphicsSettings.defaultRenderPipeline = null; QualitySettings.renderPipeline = null;
                Require(GraphicsSettings.defaultRenderPipeline == null && QualitySettings.renderPipeline == null,
                    "Advanced v1 requires Built-in rendering");

                AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
                const string actualPath = "Assets/ByteFablesFixture/artwork.bftextures";
                const string sentinelPath = "Assets/ByteFablesSentinel/artwork.bftextures";
                AssetDatabase.ImportAsset(actualPath, ImportAssetOptions.ForceSynchronousImport | ImportAssetOptions.ForceUpdate);
                AssetDatabase.ImportAsset(sentinelPath, ImportAssetOptions.ForceSynchronousImport | ImportAssetOptions.ForceUpdate);
                var actual = AssetDatabase.LoadAssetAtPath<TextureBundleAsset>(actualPath);
                var sentinel = AssetDatabase.LoadAssetAtPath<TextureBundleAsset>(sentinelPath);
                Require(actual != null && actual.ManifestSha256 == request.manifestSha256 &&
                    sentinel != null && sentinel.ManifestSha256 == request.sentinelManifestSha256,
                    "Advanced import did not match requested source");
                var shader = AssetDatabase.LoadAssetAtPath<Shader>("Packages/com.bytefables.textures/Shaders/PremultipliedArray.shader");
                var graphShader = AssetDatabase.LoadAssetAtPath<Shader>("Packages/com.bytefables.textures/Shaders/PremultipliedArrayInstanced.shader");
                Require(shader != null && graphShader != null, "Advanced qualification shaders missing");

                var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
                var probe = new GameObject("ByteFables advanced standalone acceptance").AddComponent<TextureAdvancedQualification>();
                probe.Configure(actual, sentinel, shader, graphShader, request.runId, request.editorVersion, request.profile,
                    request.manifestSha256, request.sentinelManifestSha256, request.runtimePlatform, request.graphicsApi,
                    request.scriptingBackend, request.colourSpace, request.renderPipeline, request.graphCounts);
                const string scenePath = "Assets/ByteFablesAdvancedPlayer.unity";
                Require(EditorSceneManager.SaveScene(scene, scenePath), "Could not save advanced qualification scene");
                AssetDatabase.SaveAssets();
                Directory.CreateDirectory(Path.GetDirectoryName(expectedBuildPath));
                var build = BuildPipeline.BuildPlayer(new BuildPlayerOptions {
                    scenes = new[] { scenePath }, locationPathName = expectedBuildPath, target = target,
                    subtarget = (int)StandaloneBuildSubtarget.Player, options = BuildOptions.None });

                result.runId = request.runId; result.editorVersion = Application.unityVersion; result.profile = request.profile;
                result.target = request.target; result.manifestSha256 = request.manifestSha256;
                result.sentinelManifestSha256 = request.sentinelManifestSha256; result.graphicsApi = request.graphicsApi;
                result.scriptingBackend = PlayerSettings.GetScriptingBackend(NamedBuildTarget.Standalone) == ScriptingImplementation.IL2CPP ? "IL2CPP" : "Other";
                result.colourSpace = PlayerSettings.colorSpace.ToString();
                result.renderPipeline = GraphicsSettings.defaultRenderPipeline == null && QualitySettings.renderPipeline == null ? "BuiltIn" : "SRP";
                result.errors = checked((int)build.summary.totalErrors); result.totalSize = build.summary.totalSize;
                result.developmentBuild = (build.summary.options & BuildOptions.Development) != 0;
                result.buildSucceeded = build.summary.result == BuildResult.Succeeded;
                Require(result.scriptingBackend == request.scriptingBackend && result.colourSpace == request.colourSpace &&
                    result.renderPipeline == request.renderPipeline, "Advanced build settings changed before build completion");
                Require(result.buildSucceeded && result.errors == 0 && File.Exists(expectedBuildPath), "Advanced player build failed");
                result.status = "passed";
            }
            catch (Exception error)
            {
                result.status = "failed"; result.error = error.ToString(); UnityEngine.Debug.LogException(error);
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
