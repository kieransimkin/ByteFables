using System;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text;
using ByteFables.Textures.Core;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEditor.PackageManager;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;

namespace ByteFables.Textures.Editor
{
    /// <summary>Builds an isolated URP/HDRP qualification player. Ordinary projects are untouched.</summary>
    public static class TextureSrpBuild
    {
        [Serializable] private sealed class Request
        {
            public string schema, runId, editorVersion, profile, target, runtimePlatform, graphicsApi;
            public string scriptingBackend, colourSpace, renderPipeline, srpPackageName, srpPackageVersion;
            public string pipelineAssetType, pipelineRuntimeType, manifestSha256, sentinelManifestSha256;
            public int[] graphCounts; public int pipelineComparisons; public string buildPath, buildReportPath;
        }
        [Serializable] private sealed class Result
        {
            public string schema="bytefables.unity-srp-player-build.v1";
            public string status, runId, editorVersion, profile, target, graphicsApi, scriptingBackend, colourSpace, renderPipeline;
            public string srpPackageName, srpPackageVersion, pipelineAssetType, manifestSha256, sentinelManifestSha256, error;
            public bool buildSucceeded, developmentBuild; public int errors; public long elapsedMilliseconds; public ulong totalSize;
        }
        static void Require(bool ok,string message){if(!ok)throw new TextureContractException(message);}
        static bool SamePath(string a,string b){var c=Environment.OSVersion.Platform==PlatformID.Win32NT?StringComparison.OrdinalIgnoreCase:StringComparison.Ordinal;return string.Equals(Path.GetFullPath(a),Path.GetFullPath(b),c);}
        static Type TypeByName(string fullName)
        {
            var type=AppDomain.CurrentDomain.GetAssemblies().Select(a=>a.GetType(fullName,false)).FirstOrDefault(t=>t!=null);
            Require(type!=null,"Required SRP type is unavailable: "+fullName); return type;
        }
        static RenderPipelineAsset CreateUrp()
        {
            var rendererType=TypeByName("UnityEngine.Rendering.Universal.UniversalRendererData");
            var assetType=TypeByName("UnityEngine.Rendering.Universal.UniversalRenderPipelineAsset");
            var renderer=(ScriptableObject)ScriptableObject.CreateInstance(rendererType);
            Directory.CreateDirectory("Assets/ByteFablesPipeline");
            AssetDatabase.CreateAsset(renderer,"Assets/ByteFablesPipeline/UniversalRenderer.asset");
            var create=assetType.GetMethods(BindingFlags.Public|BindingFlags.Static).FirstOrDefault(m=>
            {
                var q=m.GetParameters();return m.Name=="Create"&&q.Length==1&&q[0].ParameterType.IsAssignableFrom(rendererType);
            });
            Require(create!=null,"UniversalRenderPipelineAsset.Create(rendererData) is unavailable");
            var asset=create.Invoke(null,new object[]{renderer}) as RenderPipelineAsset;
            Require(asset!=null,"URP asset creation failed"); AssetDatabase.CreateAsset(asset,"Assets/ByteFablesPipeline/UniversalPipeline.asset"); return asset;
        }
        static RenderPipelineAsset CreateHdrp()
        {
            var assetType=TypeByName("UnityEngine.Rendering.HighDefinition.HDRenderPipelineAsset");
            var asset=ScriptableObject.CreateInstance(assetType) as RenderPipelineAsset;
            Require(asset!=null,"HDRP asset creation failed"); Directory.CreateDirectory("Assets/ByteFablesPipeline");
            AssetDatabase.CreateAsset(asset,"Assets/ByteFablesPipeline/HighDefinitionPipeline.asset");
            var globalType=AppDomain.CurrentDomain.GetAssemblies().Select(a=>a.GetType("UnityEngine.Rendering.HighDefinition.HDRenderPipelineGlobalSettings",false)).FirstOrDefault(t=>t!=null);
            var ensure=globalType?.GetMethod("Ensure",BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.Static);
            if(ensure!=null)ensure.Invoke(null,null);
            return asset;
        }
        static Shader PipelineShader(string pipeline)
        {
            var path=pipeline=="URP"?"Packages/com.bytefables.textures/Shaders/PremultipliedArrayURP.shader":"Packages/com.bytefables.textures/Shaders/PremultipliedArrayHDRP.shader";
            var shader=AssetDatabase.LoadAssetAtPath<Shader>(path); Require(shader!=null,"SRP shader asset missing: "+path); return shader;
        }
        public static void RunFromCommandLine()
        {
            var result=new Result();var watch=Stopwatch.StartNew();Request request=null;string safe=null;
            try
            {
                string requestPath=Environment.GetEnvironmentVariable("BYTEFABLES_SRP_REQUEST");
                string projectRoot=Path.GetFullPath(Path.Combine(Application.dataPath,".."));
                Require(SamePath(requestPath,Path.Combine(projectRoot,"srp-player-request.json")),"Runner-owned SRP request required");
                Require(new FileInfo(requestPath).Length<=32768,"SRP build request too large");Directory.SetCurrentDirectory(projectRoot);
                request=JsonUtility.FromJson<Request>(File.ReadAllText(requestPath));
                Require(request.schema=="bytefables.unity-srp-player-request.v1"&&System.Text.RegularExpressions.Regex.IsMatch(request.runId??"","^[a-f0-9]{32}$"),"Invalid SRP request");
                Require(request.editorVersion==Application.unityVersion,"Unity version differs from pinned SRP request");
                Require(request.scriptingBackend=="IL2CPP"&&request.colourSpace=="Linear"&&(request.renderPipeline=="URP"||request.renderPipeline=="HDRP"),"Only IL2CPP/Linear URP/HDRP profiles are defined");
                bool windows=request.target=="StandaloneWindows64";Require(windows||request.target=="StandaloneLinux64","Unsupported SRP target");
                Require(Application.platform==(windows?RuntimePlatform.WindowsEditor:RuntimePlatform.LinuxEditor),"Native SRP build/run host required");
                Require(request.runtimePlatform==(windows?"WindowsPlayer":"LinuxPlayer"),"SRP runtime platform mismatch");
                var target=windows?BuildTarget.StandaloneWindows64:BuildTarget.StandaloneLinux64;
                GraphicsDeviceType graphics=request.graphicsApi=="Direct3D11"?GraphicsDeviceType.Direct3D11:request.graphicsApi=="Direct3D12"?GraphicsDeviceType.Direct3D12:GraphicsDeviceType.Vulkan;
                Require((windows&&(graphics==GraphicsDeviceType.Direct3D11||graphics==GraphicsDeviceType.Direct3D12))||(!windows&&graphics==GraphicsDeviceType.Vulkan),"Target/API mismatch");
                Require(EditorUserBuildSettings.activeBuildTarget==target,"Start Unity with requested SRP -buildTarget");
                Require(BuildPipeline.IsBuildTargetSupported(BuildTargetGroup.Standalone,target),"Required desktop build module is missing");
                var package=PackageInfo.FindForAssetPath("Packages/"+request.srpPackageName);
                Require(package!=null&&package.name==request.srpPackageName&&package.version==request.srpPackageVersion,"Resolved SRP package does not match pinned version");
                string outputRoot=Path.GetDirectoryName(projectRoot);string expected=Path.Combine(outputRoot,"player",windows?"ByteFablesSrp.exe":"ByteFablesSrp.x86_64");
                Require(SamePath(request.buildPath,expected)&&SamePath(request.buildReportPath,Path.Combine(outputRoot,"build-result.json"))&&!Directory.Exists(Path.GetDirectoryName(expected))&&!File.Exists(request.buildReportPath),"Fresh SRP build outputs required");safe=Path.Combine(outputRoot,"build-result.json");
                PlayerSettings.SetScriptingBackend(NamedBuildTarget.Standalone,ScriptingImplementation.IL2CPP);
                PlayerSettings.SetUseDefaultGraphicsAPIs(target,false);PlayerSettings.SetGraphicsAPIs(target,new[]{graphics});PlayerSettings.colorSpace=ColorSpace.Linear;PlayerSettings.runInBackground=true;
                Require(PlayerSettings.GetScriptingBackend(NamedBuildTarget.Standalone)==ScriptingImplementation.IL2CPP&&PlayerSettings.colorSpace==ColorSpace.Linear,"Requested IL2CPP/Linear settings did not stick");
                var pipeline=request.renderPipeline=="URP"?CreateUrp():CreateHdrp();
                Require(pipeline.GetType().FullName==request.pipelineAssetType,"Created wrong render pipeline asset type");
                GraphicsSettings.defaultRenderPipeline=pipeline;QualitySettings.renderPipeline=pipeline;AssetDatabase.SaveAssets();
                AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
                const string actualPath="Assets/ByteFablesFixture/artwork.bftextures",sentinelPath="Assets/ByteFablesSentinel/artwork.bftextures";
                AssetDatabase.ImportAsset(actualPath,ImportAssetOptions.ForceSynchronousImport|ImportAssetOptions.ForceUpdate);AssetDatabase.ImportAsset(sentinelPath,ImportAssetOptions.ForceSynchronousImport|ImportAssetOptions.ForceUpdate);
                var actual=AssetDatabase.LoadAssetAtPath<TextureBundleAsset>(actualPath);var sentinel=AssetDatabase.LoadAssetAtPath<TextureBundleAsset>(sentinelPath);
                Require(actual!=null&&actual.ManifestSha256==request.manifestSha256&&sentinel!=null&&sentinel.ManifestSha256==request.sentinelManifestSha256,"SRP import did not match requested source");
                var shader=PipelineShader(request.renderPipeline);var graphShader=AssetDatabase.LoadAssetAtPath<Shader>("Packages/com.bytefables.textures/Shaders/PremultipliedArrayInstanced.shader");
                Require(graphShader!=null,"Instanced qualification shader missing");
                var scene=EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);var probe=new GameObject("ByteFables SRP acceptance").AddComponent<TextureSrpQualification>();
                probe.Configure(actual,sentinel,shader,graphShader,request.runId,request.editorVersion,request.profile,request.manifestSha256,request.sentinelManifestSha256,request.runtimePlatform,request.graphicsApi,request.renderPipeline,request.srpPackageName,request.srpPackageVersion,request.pipelineAssetType,request.pipelineRuntimeType,request.graphCounts,request.pipelineComparisons);
                const string scenePath="Assets/ByteFablesSrpPlayer.unity";Require(EditorSceneManager.SaveScene(scene,scenePath),"Could not save SRP qualification scene");AssetDatabase.SaveAssets();Directory.CreateDirectory(Path.GetDirectoryName(expected));
                var build=BuildPipeline.BuildPlayer(new BuildPlayerOptions{scenes=new[]{scenePath},locationPathName=expected,target=target,subtarget=(int)StandaloneBuildSubtarget.Player,options=BuildOptions.None});
                result.runId=request.runId;result.editorVersion=Application.unityVersion;result.profile=request.profile;result.target=request.target;result.graphicsApi=request.graphicsApi;result.scriptingBackend="IL2CPP";result.colourSpace="Linear";result.renderPipeline=request.renderPipeline;result.srpPackageName=package.name;result.srpPackageVersion=package.version;result.pipelineAssetType=pipeline.GetType().FullName;result.manifestSha256=request.manifestSha256;result.sentinelManifestSha256=request.sentinelManifestSha256;
                result.errors=checked((int)build.summary.totalErrors);result.totalSize=build.summary.totalSize;result.developmentBuild=(build.summary.options&BuildOptions.Development)!=0;result.buildSucceeded=build.summary.result==BuildResult.Succeeded;
                Require(result.buildSucceeded&&result.errors==0&&File.Exists(expected),"SRP player build failed");result.status="passed";
            }
            catch(Exception e){result.status="failed";result.error=e.ToString();UnityEngine.Debug.LogException(e);}
            result.elapsedMilliseconds=watch.ElapsedMilliseconds;
            try{if(safe!=null)using(var stream=new FileStream(safe,FileMode.CreateNew,FileAccess.Write,FileShare.None)){var b=new UTF8Encoding(false).GetBytes(JsonUtility.ToJson(result,true));stream.Write(b,0,b.Length);stream.Flush(true);}}catch(Exception e){result.status="failed";UnityEngine.Debug.LogException(e);}
            if(result.status!="passed")EditorApplication.Exit(1);
        }
    }
}
