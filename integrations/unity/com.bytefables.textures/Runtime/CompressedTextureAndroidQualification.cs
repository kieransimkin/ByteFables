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
    public sealed class CompressedTextureAndroidResult
    {
        public string schema="bytefables.unity-compressed-android-qualification.v1";
        public string status,runId,editorVersion,profile,gpuManifestSha256,referenceManifestSha256,sourceManifestSha256,error;
        public string runtimePlatform,graphicsApi,graphicsDevice,graphicsDeviceVersion,operatingSystem,scriptingBackend,colourSpace,renderPipeline,formatId,orientation,packageId,deviceModel;
        public bool playerExecuted,gpuExecuted,formatSupported,arraySupported,readbackExecuted,shaderExecuted,productionQualified,isEditor;
        public int sprites,banks,levels,readbackComparisons,shaderComparisons,orientationComparisons,skipped;
        public double readbackMeanAbsoluteError,readbackPsnrDb,shaderMeanAbsoluteError,shaderPsnrDb,topLeftMeanAbsoluteError,bottomUpMeanAbsoluteError;
        public int readbackMaxAbsoluteError,shaderMaxAbsoluteError; public long elapsedMilliseconds;
    }

    /// <summary>Physical Android device qualification; writes evidence to persistent external app storage for ADB retrieval.</summary>
    public sealed class CompressedTextureAndroidQualification : MonoBehaviour
    {
        public const string PackageId="com.bytefables.compressedqualification";
        public const string ResultFile="bytefables-compressed-android-result.json";
        [SerializeField] private Shader arrayShader; [SerializeField] private TextAsset gpuManifest,referenceTransport,referenceSource;
        [SerializeField] private string[] gpuNames,referenceBankNames; [SerializeField] private TextAsset[] gpuFiles,referenceBanks;
        [SerializeField] private string expectedRunId,expectedVersion,expectedProfile,expectedGraphicsApi,expectedFormatId,expectedGpuManifest,expectedReferenceManifest,expectedSourceManifest;

        public void Configure(Shader shader,TextAsset gpuManifest,string[] gpuNames,TextAsset[] gpuFiles,TextAsset referenceTransport,TextAsset referenceSource,
            string[] referenceBankNames,TextAsset[] referenceBanks,string runId,string version,string profile,string graphicsApi,string formatId,
            string gpuManifestSha,string referenceManifestSha,string sourceManifestSha)
        {
            arrayShader=shader;this.gpuManifest=gpuManifest;this.gpuNames=gpuNames;this.gpuFiles=gpuFiles;this.referenceTransport=referenceTransport;this.referenceSource=referenceSource;
            this.referenceBankNames=referenceBankNames;this.referenceBanks=referenceBanks;expectedRunId=runId;expectedVersion=version;expectedProfile=profile;expectedGraphicsApi=graphicsApi;expectedFormatId=formatId;
            expectedGpuManifest=gpuManifestSha;expectedReferenceManifest=referenceManifestSha;expectedSourceManifest=sourceManifestSha;
        }
        private static void Require(bool yes,string message){if(!yes)throw new TextureContractException(message);}
        private static byte[] Find(string name,string[] names,TextAsset[] files,int limit)
        {
            Require(names!=null&&files!=null&&names.Length==files.Length,"Android embedded file inventory mismatch");
            for(int i=0;i<names.Length;i++)if(names[i]==name){var b=files[i].bytes;Require(b!=null&&b.Length>0&&b.Length<=limit,"Android embedded file byte budget mismatch");return (byte[])b.Clone();}
            throw new TextureContractException("Android embedded file missing: "+name);
        }
        private sealed class ErrorAccumulator
        {
            public long Samples;public double Absolute,Square;public int Maximum;
            public void Add(byte[] expected,byte[] actual){Require(expected!=null&&actual!=null&&expected.Length==actual.Length,"Android compressed comparison length mismatch");for(int i=0;i<expected.Length;i++){int d=Math.Abs(expected[i]-actual[i]);Samples++;Absolute+=d;Square+=d*d;if(d>Maximum)Maximum=d;}}
            public double Mean{get{return Samples==0?0.0:Absolute/Samples;}}public double Psnr{get{if(Samples==0||Square==0)return 999.0;double mse=Square/Samples;return 20.0*Math.Log10(255.0/Math.Sqrt(mse));}}
        }
        private IEnumerator Start()
        {
            Application.runInBackground=true;var watch=Stopwatch.StartNew();var report=new CompressedTextureAndroidResult{runId=expectedRunId,profile=expectedProfile,formatId=expectedFormatId,isEditor=Application.isEditor};
            yield return null;Exception failure=null;var work=RunChecks(report);while(true){bool more=false;try{more=work.MoveNext();}catch(Exception error){failure=error;}if(failure!=null||!more)break;yield return work.Current;}
            try{(work as IDisposable)?.Dispose();}catch(Exception error){if(failure==null)failure=error;}report.elapsedMilliseconds=watch.ElapsedMilliseconds;report.status=failure==null?"passed":"failed";report.error=failure==null?null:failure.ToString();
            try{string path=Path.Combine(Application.persistentDataPath,ResultFile);using(var stream=new FileStream(path,FileMode.CreateNew,FileAccess.Write,FileShare.Read)){byte[] bytes=new UTF8Encoding(false).GetBytes(JsonUtility.ToJson(report,true));stream.Write(bytes,0,bytes.Length);stream.Flush(true);}}
            catch(Exception error){failure=error;}if(failure!=null)UnityEngine.Debug.LogException(failure);Application.Quit(failure==null?0:1);
        }
        private IEnumerator RunChecks(CompressedTextureAndroidResult report)
        {
            Require(!Application.isEditor&&Application.platform==RuntimePlatform.Android,"Android player execution is required");
            bool vulkan=expectedProfile=="android-vulkan-astc4x4"&&expectedGraphicsApi=="Vulkan"&&expectedFormatId=="astc4x4";
            bool gles=expectedProfile=="android-gles3-etc2rgba8"&&expectedGraphicsApi=="OpenGLES3"&&expectedFormatId=="etc2rgba8";Require(vulkan||gles,"Unknown Android compressed profile");
            report.editorVersion=Application.unityVersion;report.runtimePlatform=Application.platform.ToString();report.graphicsApi=SystemInfo.graphicsDeviceType.ToString();report.graphicsDevice=SystemInfo.graphicsDeviceName;report.graphicsDeviceVersion=SystemInfo.graphicsDeviceVersion;report.operatingSystem=SystemInfo.operatingSystem;report.deviceModel=SystemInfo.deviceModel;report.packageId=Application.identifier;
            report.colourSpace=QualitySettings.activeColorSpace.ToString();report.renderPipeline=GraphicsSettings.currentRenderPipeline==null?"BuiltIn":"SRP";
#if ENABLE_IL2CPP
            report.scriptingBackend="IL2CPP";
#else
            report.scriptingBackend="Other";
#endif
            Require(report.editorVersion==expectedVersion&&report.graphicsApi==expectedGraphicsApi&&report.packageId==PackageId,"Android Unity/API/package mismatch");
            Require(report.scriptingBackend=="IL2CPP"&&report.colourSpace=="Linear"&&report.renderPipeline=="BuiltIn","Android qualification requires IL2CPP/Linear/Built-in");
            report.arraySupported=SystemInfo.supports2DArrayTextures;report.formatSupported=CompressedTextureFormatSelector.IsSupported(expectedFormatId);
            Require(report.arraySupported&&report.formatSupported&&SystemInfo.supportsAsyncGPUReadback&&SystemInfo.graphicsDeviceType!=GraphicsDeviceType.Null,"Requested Android compressed/readback capability unavailable; no fallback/skip");
            Require(arrayShader!=null&&arrayShader.isSupported&&gpuManifest!=null&&referenceTransport!=null&&referenceSource!=null,"Android serialized qualification data missing");report.playerExecuted=true;

            var blocks=GpuBlockTextureBundleData.Load(gpuManifest.bytes,(name,limit)=>Find(name,gpuNames,gpuFiles,limit),expectedGpuManifest);
            var reference=TextureBundleData.Load(referenceTransport.bytes,(name,limit)=>name=="source-manifest.json"?(byte[])referenceSource.bytes.Clone():Find(name,referenceBankNames,referenceBanks,limit),expectedReferenceManifest);
            Require(blocks.Sprites.Count==reference.Sprites.Count&&blocks.NativeSize==reference.NativeSize,"Android compressed/reference geometry mismatch");
            report.gpuManifestSha256=blocks.ManifestSha256;report.referenceManifestSha256=reference.ManifestSha256;report.sourceManifestSha256=expectedSourceManifest;report.sprites=blocks.Sprites.Count;report.banks=blocks.FindFormat(expectedFormatId).Banks.Count;report.levels=reference.Banks[0].LevelCount;
            for(int i=0;i<blocks.Sprites.Count;i++){var a=blocks.Sprites[i];var b=reference.Sprites[i];Require(a.SpriteKey==b.SpriteKey&&a.DigestHex==b.DigestHex&&a.BankIndex==b.BankIndex&&a.LayerIndex==b.LayerIndex,"Android identity mapping changed");}

            var readback=new ErrorAccumulator();var top=new ErrorAccumulator();var bottom=new ErrorAccumulator();int topVotes=0,bottomVotes=0;
            for(int bankIndex=0;bankIndex<report.banks;bankIndex++)
            {
                var texture=CompressedTextureArrayUpload.Create(blocks,expectedFormatId,bankIndex,FilterMode.Point,false);
                try{var original=reference.Banks[bankIndex];for(int layer=0;layer<original.Layers;layer++){for(int mip=0;mip<original.LevelCount;mip++){
                    int side=original.LevelSize(mip);var req=AsyncGPUReadback.Request(texture,mip,0,side,0,side,layer,1,TextureFormat.RGBA32);req.WaitForCompletion();Require(!req.hasError,"Android compressed GPU readback failed");var actual=req.GetData<byte>().ToArray();
                    var te=original.CopyLayer(mip,layer,false);var be=original.CopyLayer(mip,layer,true);top.Add(te,actual);bottom.Add(be,actual);readback.Add(be,actual);report.readbackComparisons++;
                    if(mip==0&&MeanAbsolute(te,be)>1.0){double tm=MeanAbsolute(te,actual),bm=MeanAbsolute(be,actual);report.orientationComparisons++;if(bm<tm)bottomVotes++;else if(tm<bm)topVotes++;}
                }yield return null;}}
                finally{TextureArrayUpload.Destroy(texture);}
            }
            report.readbackExecuted=true;report.readbackMeanAbsoluteError=readback.Mean;report.readbackPsnrDb=readback.Psnr;report.readbackMaxAbsoluteError=readback.Maximum;report.topLeftMeanAbsoluteError=top.Mean;report.bottomUpMeanAbsoluteError=bottom.Mean;
            Require(report.orientationComparisons>0,"Android corpus has no asymmetric orientation evidence");report.orientation=bottomVotes==report.orientationComparisons?"bottom-up":topVotes==report.orientationComparisons?"top-left":(topVotes==0&&bottomVotes==0?"ambiguous":"mixed");

            var shaderMetrics=new ErrorAccumulator();var material=new Material(arrayShader);int samples=Math.Min(16,blocks.Sprites.Count);
            try{using(var residency=new CompressedTextureArrayResidency(blocks,expectedFormatId,blocks.FindFormat(expectedFormatId).PayloadBytes)){
                for(int sample=0;sample<samples;sample++){int spriteIndex=samples==1?0:(int)Math.Round(sample*(blocks.Sprites.Count-1.0)/(samples-1.0));var sprite=blocks.Sprites[spriteIndex];using(var lease=residency.AcquireBank(sprite.BankIndex)){
                    material.SetTexture("_Array",lease.Texture);material.SetFloat("_Layer",sprite.LayerIndex);for(int mip=0;mip<report.levels;mip++){material.SetFloat("_Mip",mip);int side=reference.Banks[sprite.BankIndex].LevelSize(mip);var expected=reference.Banks[sprite.BankIndex].CopyLayer(mip,sprite.LayerIndex,true);foreach(var matte in new[]{new Color32(0,0,0,0),new Color32(0,0,0,255),new Color32(255,255,255,255)}){shaderMetrics.Add(Composite(expected,matte),Draw(material,side,matte));report.shaderComparisons++;}}}yield return null;}
            }}finally{TextureArrayUpload.Destroy(material);}
            report.shaderExecuted=true;report.shaderMeanAbsoluteError=shaderMetrics.Mean;report.shaderPsnrDb=shaderMetrics.Psnr;report.shaderMaxAbsoluteError=shaderMetrics.Maximum;report.productionQualified=report.orientation=="bottom-up";report.gpuExecuted=true;yield return null;
        }
        private static double MeanAbsolute(byte[] a,byte[] b){Require(a.Length==b.Length,"Android orientation byte count mismatch");double t=0;for(int i=0;i<a.Length;i++)t+=Math.Abs(a[i]-b[i]);return t/a.Length;}
        private static byte[] Composite(byte[] source,Color32 matte){var result=new byte[source.Length];byte[] bg={matte.r,matte.g,matte.b,matte.a};for(int p=0;p<source.Length;p+=4)for(int c=0;c<4;c++)result[p+c]=(byte)(source[p+c]+(bg[c]*(255-source[p+3])+127)/255);return result;}
        private static byte[] Draw(Material material,int side,Color32 clear)
        {
            var target=new RenderTexture(side,side,0,RenderTextureFormat.ARGB32,RenderTextureReadWrite.Linear){antiAliasing=1,useMipMap=false,autoGenerateMips=false};var read=new Texture2D(side,side,TextureFormat.RGBA32,false,true);var previous=RenderTexture.active;bool srgb=GL.sRGBWrite;
            try{Require(target.Create(),"Android render target allocation failed");RenderTexture.active=target;GL.sRGBWrite=false;GL.Clear(false,true,clear);Graphics.Blit(null,target,material,0);RenderTexture.active=target;read.ReadPixels(new Rect(0,0,side,side),0,0,false);return read.GetPixelData<byte>(0).ToArray();}
            finally{RenderTexture.active=previous;GL.sRGBWrite=srgb;target.Release();TextureArrayUpload.Destroy(target);TextureArrayUpload.Destroy(read);}
        }
    }
}
