using System;
using System.Collections.Generic;
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
    /// <summary>Builds the isolated Android compressed-texture qualification APK.</summary>
    public static class CompressedTextureAndroidBuild
    {
        public const string PackageId = "com.bytefables.compressedqualification";
        [Serializable] private sealed class Request
        {
            public string schema,runId,editorVersion,profile,target,runtimePlatform,graphicsApi,formatId;
            public string scriptingBackend,colourSpace,renderPipeline,gpuManifestSha256,referenceManifestSha256,sourceManifestSha256;
            public string buildPath,launchPath,buildReportPath; public int nativeSize,spriteCount,levelCount; public bool automatedDesktop;
        }
        [Serializable] private sealed class Result
        {
            public string schema="bytefables.unity-compressed-android-build.v1";
            public string status,runId,editorVersion,profile,target,graphicsApi,formatId,scriptingBackend,colourSpace,renderPipeline;
            public string gpuManifestSha256,referenceManifestSha256,packageId,architecture,error;
            public bool buildSucceeded,developmentBuild; public int errors; public ulong totalSize; public long elapsedMilliseconds;
        }
        private static void Require(bool yes,string message){if(!yes)throw new TextureContractException(message);}
        private static bool SamePath(string a,string b){var c=Environment.OSVersion.Platform==PlatformID.Win32NT?StringComparison.OrdinalIgnoreCase:StringComparison.Ordinal;return string.Equals(Path.GetFullPath(a),Path.GetFullPath(b),c);}

        private static TextAsset ImportBytes(string source,string assetPath)
        {
            string full=Path.GetFullPath(assetPath);Directory.CreateDirectory(Path.GetDirectoryName(full));File.Copy(source,full,false);
            AssetDatabase.ImportAsset(assetPath,ImportAssetOptions.ForceSynchronousImport|ImportAssetOptions.ForceUpdate);
            var asset=AssetDatabase.LoadAssetAtPath<TextAsset>(assetPath);Require(asset!=null,"Could not import Android qualification bytes: "+assetPath);return asset;
        }
        private static string SafeName(string name){return name.Replace('/','_').Replace('.','_')+".bytes";}

        public static void RunFromCommandLine()
        {
            var result=new Result();var watch=Stopwatch.StartNew();Request request=null;string safeReport=null;
            try
            {
                string requestPath=Environment.GetEnvironmentVariable("BYTEFABLES_COMPRESSED_REQUEST");string projectRoot=Path.GetFullPath(Path.Combine(Application.dataPath,".."));
                Require(SamePath(requestPath,Path.Combine(projectRoot,"compressed-device-request.json")),"Runner-owned Android compressed request required");
                Require(new FileInfo(requestPath).Length<=16384,"Android compressed request too large");Directory.SetCurrentDirectory(projectRoot);
                request=JsonUtility.FromJson<Request>(File.ReadAllText(requestPath));
                Require(request.schema=="bytefables.unity-compressed-device-request.v1"&&System.Text.RegularExpressions.Regex.IsMatch(request.runId??"","^[a-f0-9]{32}$"),"Invalid Android compressed request");
                Require(!request.automatedDesktop&&request.target=="Android"&&request.runtimePlatform=="Android"&&request.editorVersion==Application.unityVersion,
                    "Android compressed request/profile mismatch");
                bool vulkan=request.profile=="android-vulkan-astc4x4"&&request.graphicsApi=="Vulkan"&&request.formatId=="astc4x4";
                bool gles=request.profile=="android-gles3-etc2rgba8"&&request.graphicsApi=="OpenGLES3"&&request.formatId=="etc2rgba8";
                Require(vulkan||gles,"Unsupported Android compressed profile");
                Require(request.scriptingBackend=="IL2CPP"&&request.colourSpace=="Linear"&&request.renderPipeline=="BuiltIn","Android qualification requires IL2CPP/Linear/Built-in");
                Require(EditorUserBuildSettings.activeBuildTarget==BuildTarget.Android,"Start Unity with -buildTarget Android");
                Require(BuildPipeline.IsBuildTargetSupported(BuildTargetGroup.Android,BuildTarget.Android),"Unity Android Build Support module is missing");
                string outputRoot=Path.GetDirectoryName(projectRoot),expectedBuild=Path.Combine(outputRoot,"player","ByteFablesCompressed.apk");
                Require(SamePath(request.buildPath,expectedBuild)&&SamePath(request.launchPath,expectedBuild)&&SamePath(request.buildReportPath,Path.Combine(outputRoot,"build-result.json")),"Android output paths differ from isolated plan");
                Require(!File.Exists(expectedBuild)&&!File.Exists(request.buildReportPath),"Fresh Android qualification outputs required");safeReport=Path.Combine(outputRoot,"build-result.json");

                PlayerSettings.productName="ByteFablesCompressedQualification";
                PlayerSettings.SetApplicationIdentifier(NamedBuildTarget.Android,PackageId);
                PlayerSettings.SetScriptingBackend(NamedBuildTarget.Android,ScriptingImplementation.IL2CPP);
                PlayerSettings.Android.targetArchitectures=AndroidArchitecture.ARM64;
                EditorUserBuildSettings.buildAppBundle=false;
                PlayerSettings.SetUseDefaultGraphicsAPIs(BuildTarget.Android,false);
                PlayerSettings.SetGraphicsAPIs(BuildTarget.Android,new[]{vulkan?GraphicsDeviceType.Vulkan:GraphicsDeviceType.OpenGLES3});
                PlayerSettings.colorSpace=ColorSpace.Linear;PlayerSettings.runInBackground=true;GraphicsSettings.defaultRenderPipeline=null;QualitySettings.renderPipeline=null;
                Require(PlayerSettings.GetApplicationIdentifier(NamedBuildTarget.Android)==PackageId&&PlayerSettings.GetScriptingBackend(NamedBuildTarget.Android)==ScriptingImplementation.IL2CPP&&
                    PlayerSettings.Android.targetArchitectures==AndroidArchitecture.ARM64&&PlayerSettings.colorSpace==ColorSpace.Linear,"Unity did not accept Android build settings");

                AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
                string gpuRoot=Path.Combine(projectRoot,"Assets","StreamingAssets","ByteFablesGpuBlocks");
                string refRoot=Path.Combine(projectRoot,"Assets","StreamingAssets","ByteFablesReference");
                var blocks=GpuBlockTextureBundleDirectory.LoadDescriptor(Path.Combine(gpuRoot,"gpu.bfgpu"));var format=blocks.FindFormat(request.formatId);
                var reference=TextureBundleDirectory.LoadDescriptor(Path.Combine(refRoot,"artwork.bftextures"));
                Require(blocks.ManifestSha256==request.gpuManifestSha256&&reference.ManifestSha256==request.referenceManifestSha256,"Android staged source pins changed");

                const string assetRoot="Assets/ByteFablesAndroidData";
                var gpuManifest=ImportBytes(Path.Combine(gpuRoot,"manifest.json"),assetRoot+"/gpu-manifest.bytes");
                var gpuAssets=new List<TextAsset>();var gpuNames=new List<string>();
                foreach(var bank in format.Banks)foreach(var level in bank.Levels)
                { gpuNames.Add(level.File);gpuAssets.Add(ImportBytes(Path.Combine(gpuRoot,level.File.Replace('/',Path.DirectorySeparatorChar)),assetRoot+"/gpu-"+SafeName(level.File))); }
                var refTransport=ImportBytes(Path.Combine(refRoot,"transport.json"),assetRoot+"/reference-transport.bytes");
                var refSource=ImportBytes(Path.Combine(refRoot,"source-manifest.json"),assetRoot+"/reference-source.bytes");
                var refBanks=new List<TextAsset>();var refNames=new List<string>();
                for(int i=0;i<reference.Banks.Count;i++)
                { string name="banks/bank-"+i.ToString("D3")+".ktx2";refNames.Add(name);refBanks.Add(ImportBytes(Path.Combine(refRoot,name.Replace('/',Path.DirectorySeparatorChar)),assetRoot+"/ref-"+SafeName(name))); }
                var shader=AssetDatabase.LoadAssetAtPath<Shader>("Packages/com.bytefables.textures/Shaders/PremultipliedArray.shader");Require(shader!=null,"Android qualification shader missing");
                var scene=EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);
                var probe=new GameObject("ByteFables Android compressed qualification").AddComponent<CompressedTextureAndroidQualification>();
                probe.Configure(shader,gpuManifest,gpuNames.ToArray(),gpuAssets.ToArray(),refTransport,refSource,refNames.ToArray(),refBanks.ToArray(),
                    request.runId,request.editorVersion,request.profile,request.graphicsApi,request.formatId,request.gpuManifestSha256,request.referenceManifestSha256,request.sourceManifestSha256);
                const string scenePath="Assets/ByteFablesCompressedAndroid.unity";Require(EditorSceneManager.SaveScene(scene,scenePath),"Could not save Android qualification scene");AssetDatabase.SaveAssets();
                Directory.CreateDirectory(Path.GetDirectoryName(expectedBuild));
                var build=BuildPipeline.BuildPlayer(new BuildPlayerOptions{scenes=new[]{scenePath},locationPathName=expectedBuild,target=BuildTarget.Android,targetGroup=BuildTargetGroup.Android,options=BuildOptions.None});
                result.runId=request.runId;result.editorVersion=Application.unityVersion;result.profile=request.profile;result.target=request.target;result.graphicsApi=request.graphicsApi;result.formatId=request.formatId;
                result.scriptingBackend=PlayerSettings.GetScriptingBackend(NamedBuildTarget.Android)==ScriptingImplementation.IL2CPP?"IL2CPP":"Other";result.colourSpace=PlayerSettings.colorSpace.ToString();result.renderPipeline=GraphicsSettings.defaultRenderPipeline==null&&QualitySettings.renderPipeline==null?"BuiltIn":"SRP";
                result.gpuManifestSha256=request.gpuManifestSha256;result.referenceManifestSha256=request.referenceManifestSha256;result.packageId=PlayerSettings.GetApplicationIdentifier(NamedBuildTarget.Android);result.architecture=PlayerSettings.Android.targetArchitectures.ToString();
                result.errors=checked((int)build.summary.totalErrors);result.totalSize=build.summary.totalSize;result.developmentBuild=(build.summary.options&BuildOptions.Development)!=0;result.buildSucceeded=build.summary.result==BuildResult.Succeeded;
                Require(result.buildSucceeded&&result.errors==0&&!result.developmentBuild&&result.scriptingBackend=="IL2CPP"&&result.colourSpace=="Linear"&&result.renderPipeline=="BuiltIn"&&result.packageId==PackageId&&result.architecture.Contains("ARM64")&&File.Exists(expectedBuild),"Android compressed APK build failed");
                result.status="passed";
            }
            catch(Exception error){result.status="failed";result.error=error.ToString();UnityEngine.Debug.LogException(error);}
            result.elapsedMilliseconds=watch.ElapsedMilliseconds;
            try{if(safeReport!=null)using(var stream=new FileStream(safeReport,FileMode.CreateNew,FileAccess.Write,FileShare.None)){byte[] bytes=new UTF8Encoding(false).GetBytes(JsonUtility.ToJson(result,true));stream.Write(bytes,0,bytes.Length);stream.Flush(true);}}
            catch(Exception error){result.status="failed";UnityEngine.Debug.LogException(error);}if(result.status!="passed")EditorApplication.Exit(1);
        }
    }
}
