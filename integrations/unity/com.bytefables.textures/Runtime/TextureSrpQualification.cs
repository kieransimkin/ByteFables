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
    [Serializable] public sealed class TextureSrpResult
    {
        public string schema="bytefables.unity-srp-player-qualification.v1";
        public string status,runId,editorVersion,profile,manifestSha256,sentinelManifestSha256,error;
        public string runtimePlatform,graphicsApi,graphicsDevice,graphicsDeviceVersion,operatingSystem,scriptingBackend,colourSpace,renderPipeline;
        public string srpPackageName,srpPackageVersion,pipelineAssetType,pipelineRuntimeType;
        public bool playerExecuted,gpuExecuted,serializedAssetsExecuted,syntheticSentinelsExecuted,disposalExecuted,pipelineExecuted,graphExecuted,isEditor;
        public int banks,sprites,cpuComparisons,gpuComparisons,shaderComparisons,bindingComparisons,overlapComparisons,skipped;
        public int overlapByteTolerance=1,pipelineComparisons,pipelineByteTolerance=1;
        public long elapsedMilliseconds; public TextureGraphProbeResult[] graphResults;
    }
    public sealed class TextureSrpQualification:MonoBehaviour
    {
        [SerializeField] TextureBundleAsset actual,sentinel;[SerializeField] Shader pipelineShader,graphShader;
        [SerializeField] string expectedRunId,expectedVersion,expectedProfile,expectedManifest,expectedSentinelManifest,expectedPlatform,expectedGraphicsApi,expectedPipeline,expectedPackageName,expectedPackageVersion,expectedAssetType,expectedRuntimeType;
        [SerializeField] int[] graphCounts;[SerializeField] int expectedPipelineComparisons;
        public void Configure(TextureBundleAsset a,TextureBundleAsset s,Shader ps,Shader gs,string runId,string version,string profile,string manifest,string sentinelManifest,string platform,string api,string pipeline,string packageName,string packageVersion,string assetType,string runtimeType,int[] counts,int pipelineComparisons)
        {actual=a;sentinel=s;pipelineShader=ps;graphShader=gs;expectedRunId=runId;expectedVersion=version;expectedProfile=profile;expectedManifest=manifest;expectedSentinelManifest=sentinelManifest;expectedPlatform=platform;expectedGraphicsApi=api;expectedPipeline=pipeline;expectedPackageName=packageName;expectedPackageVersion=packageVersion;expectedAssetType=assetType;expectedRuntimeType=runtimeType;graphCounts=(int[])counts.Clone();expectedPipelineComparisons=pipelineComparisons;}
        static void Require(bool ok,string message){if(!ok)throw new TextureContractException(message);}
        IEnumerator Start()
        {
            Application.runInBackground=true;var watch=Stopwatch.StartNew();var report=new TextureSrpResult{runId=expectedRunId,isEditor=Application.isEditor};yield return null;
            var work=RunChecks(report);Exception failure=null;while(true){bool more=false;try{more=work.MoveNext();}catch(Exception e){failure=e;}if(failure!=null||!more)break;yield return work.Current;}try{(work as IDisposable)?.Dispose();}catch(Exception e){if(failure==null)failure=e;}
            report.elapsedMilliseconds=watch.ElapsedMilliseconds;report.status=failure==null?"passed":"failed";report.error=failure==null?null:failure.ToString();
            try{string path=Environment.GetEnvironmentVariable("BYTEFABLES_SRP_REPORT");Require(!string.IsNullOrEmpty(path)&&Path.IsPathRooted(path),"Absolute fresh SRP report path required");using(var stream=new FileStream(path,FileMode.CreateNew,FileAccess.Write,FileShare.None)){var b=new UTF8Encoding(false).GetBytes(JsonUtility.ToJson(report,true));stream.Write(b,0,b.Length);stream.Flush(true);}}catch(Exception e){failure=e;}
            if(failure!=null)Debug.LogException(failure);Application.Quit(failure==null?0:1);
        }
        IEnumerator RunChecks(TextureSrpResult report)
        {
            Require(!Application.isEditor,"Editor execution is not SRP player qualification");Require(expectedRunId==Environment.GetEnvironmentVariable("BYTEFABLES_SRP_RUN_ID"),"Stale/substituted SRP player");
            report.editorVersion=Application.unityVersion;report.profile=expectedProfile;report.runtimePlatform=Application.platform.ToString();report.graphicsApi=SystemInfo.graphicsDeviceType.ToString();report.graphicsDevice=SystemInfo.graphicsDeviceName;report.graphicsDeviceVersion=SystemInfo.graphicsDeviceVersion;report.operatingSystem=SystemInfo.operatingSystem;report.colourSpace=QualitySettings.activeColorSpace.ToString();report.renderPipeline=expectedPipeline;report.srpPackageName=expectedPackageName;report.srpPackageVersion=expectedPackageVersion;
#if ENABLE_IL2CPP
            report.scriptingBackend="IL2CPP";
#else
            report.scriptingBackend="Other";
#endif
            var asset=GraphicsSettings.currentRenderPipeline;Require(asset!=null&&GraphicsSettings.isScriptableRenderPipelineEnabled,"Requested SRP is not active");report.pipelineAssetType=asset.GetType().FullName;
            Require(report.editorVersion==expectedVersion&&report.runtimePlatform==expectedPlatform&&report.graphicsApi==expectedGraphicsApi&&report.scriptingBackend=="IL2CPP"&&report.colourSpace=="Linear"&&report.pipelineAssetType==expectedAssetType,"SRP runtime profile changed or fell back");
            Require(SystemInfo.graphicsDeviceType!=GraphicsDeviceType.Null&&SystemInfo.supports2DArrayTextures&&SystemInfo.supportsAsyncGPUReadback&&SystemInfo.supportsInstancing,"Required SRP GPU capabilities are unavailable");
            Require(pipelineShader!=null&&pipelineShader.isSupported&&graphShader!=null&&graphShader.isSupported,"Required SRP shaders are unavailable");report.playerExecuted=true;
            var data=TextureBundleDirectory.LoadDescriptor(Path.Combine(Application.streamingAssetsPath,"ByteFablesFixture/artwork.bftextures"));var probes=TextureBundleDirectory.LoadDescriptor(Path.Combine(Application.streamingAssetsPath,"ByteFablesSentinel/artwork.bftextures"));
            Require(data.ManifestSha256==expectedManifest&&probes.ManifestSha256==expectedSentinelManifest,"SRP StreamingAssets source differs from build pins");report.manifestSha256=data.ManifestSha256;report.sentinelManifestSha256=probes.ManifestSha256;report.banks=data.Banks.Count;report.sprites=data.Sprites.Count;
            var baseReport=new TexturePlayerResult();var q=TexturePlayerReadback.Qualify(actual,data,pipelineShader,baseReport);try{while(q.MoveNext())yield return q.Current;}finally{(q as IDisposable)?.Dispose();}q=TexturePlayerReadback.Qualify(sentinel,probes,pipelineShader,baseReport);try{while(q.MoveNext())yield return q.Current;}finally{(q as IDisposable)?.Dispose();}
            TexturePlayerReadback.Overlap(probes,pipelineShader,baseReport);report.cpuComparisons=baseReport.cpuComparisons;report.gpuComparisons=baseReport.gpuComparisons;report.shaderComparisons=baseReport.shaderComparisons;report.bindingComparisons=baseReport.bindingComparisons;report.overlapComparisons=baseReport.overlapComparisons;report.serializedAssetsExecuted=true;report.syntheticSentinelsExecuted=true;
            var pipelineProbe=TextureSrpCameraProbe.Qualify(actual,data,sentinel,probes,pipelineShader,Math.Min(16,data.Sprites.Count),report);try{while(pipelineProbe.MoveNext())yield return pipelineProbe.Current;}finally{(pipelineProbe as IDisposable)?.Dispose();}
            Require(report.pipelineComparisons==expectedPipelineComparisons,"SRP pipeline comparison count changed");report.pipelineExecuted=true;
            var runtime=RenderPipelineManager.currentPipeline;Require(runtime!=null,"SRP runtime pipeline never instantiated");report.pipelineRuntimeType=runtime.GetType().FullName;Require(report.pipelineRuntimeType==expectedRuntimeType,"Wrong SRP runtime implementation active");
            var graphs=new TextureGraphProbeResult[graphCounts.Length];for(int i=0;i<graphCounts.Length;i++){graphs[i]=TextureGraphBenchmark.Run(actual,data,graphShader,graphCounts[i]);yield return null;}report.graphResults=graphs;report.graphExecuted=true;
            var owner=new UploadedTextureBundle(probes);owner.Dispose();owner.Dispose();bool disposed=false;try{owner.GetBank(0);}catch(ObjectDisposedException){disposed=true;}Require(disposed,"Disposed SRP runtime bundle remained usable");report.disposalExecuted=true;report.gpuExecuted=true;yield return null;
        }
    }
}
