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
    /// <summary>Builds an isolated IL2CPP/Linear compressed-texture measurement player.</summary>
    public static class CompressedTextureDeviceBuild
    {
        [Serializable]
        private sealed class Request
        {
            public string schema, runId, editorVersion, profile, target, runtimePlatform, graphicsApi, formatId;
            public string scriptingBackend, colourSpace, renderPipeline, gpuManifestSha256, referenceManifestSha256, sourceManifestSha256;
            public string buildPath, launchPath, buildReportPath; public int nativeSize, spriteCount, levelCount; public bool automatedDesktop;
        }
        [Serializable]
        private sealed class Result
        {
            public string schema="bytefables.unity-compressed-device-build.v1";
            public string status, runId, editorVersion, profile, target, graphicsApi, formatId, scriptingBackend, colourSpace, renderPipeline;
            public string gpuManifestSha256, referenceManifestSha256, error; public bool buildSucceeded, developmentBuild; public int errors; public ulong totalSize; public long elapsedMilliseconds;
        }
        private static void Require(bool yes,string message){if(!yes)throw new TextureContractException(message);}
        private static bool SamePath(string a,string b){var c=Environment.OSVersion.Platform==PlatformID.Win32NT?StringComparison.OrdinalIgnoreCase:StringComparison.Ordinal;return string.Equals(Path.GetFullPath(a),Path.GetFullPath(b),c);}

        public static void RunFromCommandLine()
        {
            var result=new Result();var watch=Stopwatch.StartNew();Request request=null;string safeReport=null;
            try
            {
                string requestPath=Environment.GetEnvironmentVariable("BYTEFABLES_COMPRESSED_REQUEST");string projectRoot=Path.GetFullPath(Path.Combine(Application.dataPath,".."));
                Require(SamePath(requestPath,Path.Combine(projectRoot,"compressed-device-request.json")),"Runner-owned compressed request required");Require(new FileInfo(requestPath).Length<=16384,"Compressed request too large");
                Directory.SetCurrentDirectory(projectRoot);request=JsonUtility.FromJson<Request>(File.ReadAllText(requestPath));
                Require(request.schema=="bytefables.unity-compressed-device-request.v1"&&System.Text.RegularExpressions.Regex.IsMatch(request.runId??"","^[a-f0-9]{32}$"),"Invalid compressed request");
                Require(request.automatedDesktop&&request.editorVersion==Application.unityVersion&&request.scriptingBackend=="IL2CPP"&&request.colourSpace=="Linear"&&request.renderPipeline=="BuiltIn","Compressed desktop build contract mismatch");
                BuildTarget target;RuntimePlatform editorPlatform;GraphicsDeviceType graphics;string expectedBuild,expectedLaunch;
                string outputRoot=Path.GetDirectoryName(projectRoot),playerRoot=Path.Combine(outputRoot,"player");
                if(request.profile=="windows-d3d11-bc7"||request.profile=="windows-d3d12-bc7")
                {
                    Require(request.target=="StandaloneWindows64"&&request.runtimePlatform=="WindowsPlayer"&&request.formatId=="bc7","Windows compressed profile mismatch");
                    target=BuildTarget.StandaloneWindows64;editorPlatform=RuntimePlatform.WindowsEditor;graphics=request.graphicsApi=="Direct3D11"?GraphicsDeviceType.Direct3D11:request.graphicsApi=="Direct3D12"?GraphicsDeviceType.Direct3D12:throw new TextureContractException("Windows graphics API mismatch");
                    expectedBuild=Path.Combine(playerRoot,"ByteFablesCompressed.exe");expectedLaunch=expectedBuild;
                }
                else if(request.profile=="linux-vulkan-bc7")
                {
                    Require(request.target=="StandaloneLinux64"&&request.runtimePlatform=="LinuxPlayer"&&request.graphicsApi=="Vulkan"&&request.formatId=="bc7","Linux compressed profile mismatch");
                    target=BuildTarget.StandaloneLinux64;editorPlatform=RuntimePlatform.LinuxEditor;graphics=GraphicsDeviceType.Vulkan;expectedBuild=Path.Combine(playerRoot,"ByteFablesCompressed.x86_64");expectedLaunch=expectedBuild;
                }
                else if(request.profile=="macos-metal-astc4x4")
                {
                    Require(request.target=="StandaloneOSX"&&request.runtimePlatform=="OSXPlayer"&&request.graphicsApi=="Metal"&&request.formatId=="astc4x4","macOS compressed profile mismatch");
                    target=BuildTarget.StandaloneOSX;editorPlatform=RuntimePlatform.OSXEditor;graphics=GraphicsDeviceType.Metal;expectedBuild=Path.Combine(playerRoot,"ByteFablesCompressed.app");expectedLaunch=Path.Combine(expectedBuild,"Contents","MacOS","ByteFablesCompressed");
                }
                else throw new TextureContractException("Only native desktop compressed profiles can build in v1");
                Require(Application.platform==editorPlatform,"Native compressed build host required");Require(EditorUserBuildSettings.activeBuildTarget==target,"Start Unity with requested compressed -buildTarget");
                Require(BuildPipeline.IsBuildTargetSupported(BuildTargetGroup.Standalone,target),"Required compressed desktop build module missing");
                Require(SamePath(request.buildPath,expectedBuild)&&SamePath(request.launchPath,expectedLaunch)&&SamePath(request.buildReportPath,Path.Combine(outputRoot,"build-result.json")),"Compressed output paths differ from isolated plan");
                Require(!File.Exists(expectedBuild)&&!Directory.Exists(expectedBuild)&&!File.Exists(request.buildReportPath),"Fresh compressed build outputs required");safeReport=Path.Combine(outputRoot,"build-result.json");

                PlayerSettings.productName="ByteFablesCompressed";PlayerSettings.SetScriptingBackend(NamedBuildTarget.Standalone,ScriptingImplementation.IL2CPP);
                Require(PlayerSettings.GetScriptingBackend(NamedBuildTarget.Standalone)==ScriptingImplementation.IL2CPP,"Unity did not accept IL2CPP backend");
                PlayerSettings.SetUseDefaultGraphicsAPIs(target,false);PlayerSettings.SetGraphicsAPIs(target,new[]{graphics});PlayerSettings.colorSpace=ColorSpace.Linear;PlayerSettings.runInBackground=true;
                GraphicsSettings.defaultRenderPipeline=null;QualitySettings.renderPipeline=null;Require(PlayerSettings.colorSpace==ColorSpace.Linear&&GraphicsSettings.defaultRenderPipeline==null&&QualitySettings.renderPipeline==null,"Compressed build settings changed");
                AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
                var shader=AssetDatabase.LoadAssetAtPath<Shader>("Packages/com.bytefables.textures/Shaders/PremultipliedArray.shader");Require(shader!=null,"Compressed qualification shader missing");
                var scene=EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);var probe=new GameObject("ByteFables compressed device measurement").AddComponent<CompressedTextureDeviceQualification>();
                probe.Configure(shader,request.runId,request.editorVersion,request.profile,request.runtimePlatform,request.graphicsApi,request.formatId,request.gpuManifestSha256,request.referenceManifestSha256,request.sourceManifestSha256);
                const string scenePath="Assets/ByteFablesCompressedDevice.unity";Require(EditorSceneManager.SaveScene(scene,scenePath),"Could not save compressed qualification scene");AssetDatabase.SaveAssets();Directory.CreateDirectory(playerRoot);
                var build=BuildPipeline.BuildPlayer(new BuildPlayerOptions{scenes=new[]{scenePath},locationPathName=expectedBuild,target=target,subtarget=(int)StandaloneBuildSubtarget.Player,options=BuildOptions.None});
                result.runId=request.runId;result.editorVersion=Application.unityVersion;result.profile=request.profile;result.target=request.target;result.graphicsApi=request.graphicsApi;result.formatId=request.formatId;
                result.scriptingBackend=PlayerSettings.GetScriptingBackend(NamedBuildTarget.Standalone)==ScriptingImplementation.IL2CPP?"IL2CPP":"Other";result.colourSpace=PlayerSettings.colorSpace.ToString();result.renderPipeline=GraphicsSettings.defaultRenderPipeline==null&&QualitySettings.renderPipeline==null?"BuiltIn":"SRP";
                result.gpuManifestSha256=request.gpuManifestSha256;result.referenceManifestSha256=request.referenceManifestSha256;result.errors=checked((int)build.summary.totalErrors);result.totalSize=build.summary.totalSize;result.developmentBuild=(build.summary.options&BuildOptions.Development)!=0;result.buildSucceeded=build.summary.result==BuildResult.Succeeded;
                Require(result.scriptingBackend==request.scriptingBackend&&result.colourSpace==request.colourSpace&&result.renderPipeline==request.renderPipeline,"Compressed build settings changed before completion");
                Require(result.buildSucceeded&&result.errors==0&&(File.Exists(expectedLaunch)||Directory.Exists(expectedBuild)),"Compressed player build failed");result.status="passed";
            }
            catch(Exception error){result.status="failed";result.error=error.ToString();UnityEngine.Debug.LogException(error);}
            result.elapsedMilliseconds=watch.ElapsedMilliseconds;
            try{if(safeReport!=null)using(var stream=new FileStream(safeReport,FileMode.CreateNew,FileAccess.Write,FileShare.None)){byte[] bytes=new UTF8Encoding(false).GetBytes(JsonUtility.ToJson(result,true));stream.Write(bytes,0,bytes.Length);stream.Flush(true);}}
            catch(Exception error){result.status="failed";UnityEngine.Debug.LogException(error);}if(result.status!="passed")EditorApplication.Exit(1);
        }
    }
}
