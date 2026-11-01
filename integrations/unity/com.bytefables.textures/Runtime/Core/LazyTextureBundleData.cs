using System;
using System.Collections.Generic;
using System.Globalization;
using System.Text;

namespace ByteFables.Textures.Core
{
    public sealed class LazyTextureBankRecord
    {
        public int Index { get; private set; }
        public int Layers { get; private set; }
        public string File { get; private set; }
        public int ByteLength { get; private set; }
        public string Sha256 { get; private set; }
        internal string[] LevelHashes { get; private set; }
        internal LazyTextureBankRecord(int index, int layers, string file, int length, string sha, string[] levelHashes)
        { Index=index; Layers=layers; File=file; ByteLength=length; Sha256=sha; LevelHashes=levelHashes; }
    }

    /// <summary>
    /// Metadata-first runtime bundle. Opening it validates only manifest/identity metadata;
    /// KTX2 bank bytes are not read until LoadBank is called.
    /// </summary>
    public sealed class LazyTextureBundleData
    {
        public const string Schema = "bytefables.runtime-resolved-bundle.v1";
        public const string Profile = "bytefables.runtime-rgba8-resolved.v1";
        public const int MaximumPayloadBudget = 128 * 1024 * 1024;
        public string ManifestSha256 { get; private set; }
        public string SourceKind { get; private set; }
        public string SourceArtifactSha256 { get; private set; }
        public string SourceTransportSha256 { get; private set; }
        public string SourceManifestSha256 { get; private set; }
        public int NativeSize { get; private set; }
        public int PayloadBytes { get; private set; }
        public int LayersPerBank { get; private set; }
        public IReadOnlyList<LazyTextureBankRecord> Banks { get; private set; }
        public IReadOnlyList<TextureSprite> Sprites { get; private set; }
        private readonly Dictionary<string,int> byKey;
        private readonly Func<string,int,byte[]> reader;

        private LazyTextureBundleData(string manifestSha, string sourceKind, string artifactSha,
            string transportSha, string sourceSha, int size, int payload, int layersPerBank,
            List<LazyTextureBankRecord> banks, List<TextureSprite> sprites, Func<string,int,byte[]> reader)
        {
            ManifestSha256=manifestSha; SourceKind=sourceKind; SourceArtifactSha256=artifactSha;
            SourceTransportSha256=transportSha; SourceManifestSha256=sourceSha; NativeSize=size;
            PayloadBytes=payload; LayersPerBank=layersPerBank; Banks=banks.AsReadOnly(); Sprites=sprites.AsReadOnly();
            this.reader=reader; byKey=new Dictionary<string,int>(StringComparer.Ordinal);
            for(int i=0;i<sprites.Count;i++) byKey.Add(sprites[i].SpriteKey,i);
        }

        public TextureSprite Find(string fullSpriteKey)
        {
            int index; Checks.Require(fullSpriteKey!=null && byKey.TryGetValue(fullSpriteKey,out index),"Unknown full sprite key");
            return Sprites[index];
        }

        public int BankPayloadBytes(int bankIndex)
        {
            Checks.Require(bankIndex>=0 && bankIndex<Banks.Count,"Invalid bank index");
            int total=0, layers=Banks[bankIndex].Layers;
            for(int level=0;level<Ktx2ArrayData.LevelsFor(NativeSize);level++)
            { int side=NativeSize>>level; total=checked(total+side*side*layers*4); }
            return total;
        }

        public Ktx2ArrayData LoadBank(int bankIndex)
        {
            Checks.Require(bankIndex>=0 && bankIndex<Banks.Count,"Invalid bank index");
            var record=Banks[bankIndex];
            var bytes=reader(record.File,record.ByteLength);
            Checks.Require(bytes!=null && bytes.Length==record.ByteLength,"Runtime bank byte count mismatch");
            var parsed=Ktx2ArrayData.Parse(bytes,record.Sha256);
            Checks.Require(parsed.Size==NativeSize && parsed.Layers==record.Layers,"Runtime bank geometry mismatch");
            for(int level=0;level<parsed.LevelCount;level++)
            {
                Checks.Require(parsed.LevelSha256(level)==record.LevelHashes[level],"Runtime bank mip checksum mismatch");
                for(int layer=0;layer<record.Layers;layer++)
                {
                    int spriteIndex=bankIndex*LayersPerBank+layer;
                    Checks.Require(spriteIndex<Sprites.Count && parsed.LayerSha256(level,layer)==Sprites[spriteIndex].LevelHashes[level],
                        "Runtime sprite mip checksum mismatch");
                }
            }
            return parsed;
        }

        private static string Text(Dictionary<string,object> map,string key){return J.Str(J.Get(map,key));}
        private static int Number(Dictionary<string,object> map,string key,int lo,int hi){return J.Int(J.Get(map,key),lo,hi);}
        private static string Hash(Dictionary<string,object> map,string key){return J.Hash(J.Get(map,key));}
        private static string CanonicalKey(string digest,string family,string palette,int complexity,int size,string sourceHash)
        {
            string json="{\n  \"profile\": \"bytefables.premultiplied-area-mips.v1\",\n  \"digestHex\": \""+digest+
                "\",\n  \"family\": \""+family+"\",\n  \"palette\": \""+palette+"\",\n  \"complexity\": "+complexity.ToString(CultureInfo.InvariantCulture)+
                ",\n  \"nativeSize\": "+size.ToString(CultureInfo.InvariantCulture)+",\n  \"sourceRGBAsha256\": \""+sourceHash+"\"\n}\n";
            return "bfalpha1-"+TextureHashes.Sha256(Encoding.UTF8.GetBytes(json));
        }

        public static LazyTextureBundleData Load(byte[] manifestBytes, Func<string,int,byte[]> bankReader,
            string expectedManifestSha256=null, int maxPayloadBytes=MaximumPayloadBudget)
        {
            if(bankReader==null)throw new ArgumentNullException(nameof(bankReader));
            Checks.Require(manifestBytes!=null && manifestBytes.Length<=StrictJson.MaxBytes,"Invalid runtime manifest size");
            Checks.Require(maxPayloadBytes>=1 && maxPayloadBytes<=MaximumPayloadBudget,"Invalid runtime payload budget");
            var snapshot=(byte[])manifestBytes.Clone();string manifestSha=TextureHashes.Sha256(snapshot);
            if(expectedManifestSha256!=null)Checks.Require(Checks.IsHash(expectedManifestSha256)&&expectedManifestSha256==manifestSha,"Runtime manifest pin mismatch");
            var doc=J.Obj(StrictJson.Parse(snapshot));
            J.Keys(doc,"schema","profile","status","publicOnly","guarantee","sourceArtifact","sourceTransportSha256","sourceManifestSha256",
                "nativeSize","layersPerBank","spriteCount","levelCount","payloadBytes","banks","sprites");
            J.Eq(J.Get(doc,"schema"),Schema);J.Eq(J.Get(doc,"profile"),Profile);J.Eq(J.Get(doc,"status"),"passed");
            J.Bool(J.Get(doc,"publicOnly"),true);J.Eq(J.Get(doc,"guarantee"),"presentation-only");
            var artifact=J.Obj(J.Get(doc,"sourceArtifact"));J.Keys(artifact,"kind","manifestSha256");
            string kind=Text(artifact,"kind");Checks.Require(kind=="lossless-ktx2"||kind=="uastc-zstd","Unsupported runtime source kind");
            string artifactSha=Hash(artifact,"manifestSha256"),transportSha=Hash(doc,"sourceTransportSha256"),sourceSha=Hash(doc,"sourceManifestSha256");
            int size=Number(doc,"nativeSize",16,128);Checks.Require(size==16||size==32||size==64||size==128,"Invalid runtime native size");
            int capacity=Number(doc,"layersPerBank",1,256),count=Number(doc,"spriteCount",1,1024),levels=Ktx2ArrayData.LevelsFor(size);
            Checks.Require(Number(doc,"levelCount",1,8)==levels,"Runtime mip count mismatch");
            int expectedPayload=0;for(int level=0;level<levels;level++)expectedPayload=checked(expectedPayload+(size>>level)*(size>>level)*4*count);
            Checks.Require(Number(doc,"payloadBytes",1,maxPayloadBytes)==expectedPayload,"Runtime payload size mismatch");
            var bankDocs=J.Arr(J.Get(doc,"banks"));int expectedBanks=(count+capacity-1)/capacity;
            Checks.Require(bankDocs.Count==expectedBanks && expectedBanks<=16,"Runtime bank count mismatch");
            var banks=new List<LazyTextureBankRecord>();
            for(int b=0;b<bankDocs.Count;b++)
            {
                var bank=J.Obj(bankDocs[b]);J.Keys(bank,"index","layerCount","file","byteLength","sha256","levels");
                int layers=Math.Min(capacity,count-b*capacity);
                Checks.Require(Number(bank,"index",0,15)==b && Number(bank,"layerCount",1,256)==layers,"Runtime bank index/layer mismatch");
                string file=Text(bank,"file");Checks.Require(file=="banks/bank-"+b.ToString("D3",CultureInfo.InvariantCulture)+".ktx2","Runtime bank path mismatch");
                int length=Number(bank,"byteLength",80,Ktx2ArrayData.MaxContainerBytes);
                Checks.Require(length==Ktx2ArrayData.EncodedLength(size,layers),"Runtime bank byte length mismatch");
                string sha=Hash(bank,"sha256");var levelDocs=J.Arr(J.Get(bank,"levels"));Checks.Require(levelDocs.Count==levels,"Runtime bank level count mismatch");
                var levelHashes=new string[levels];
                for(int l=0;l<levels;l++)
                {
                    var rec=J.Obj(levelDocs[l]);J.Keys(rec,"level","size","byteLength","sha256");int side=size>>l;
                    Checks.Require(Number(rec,"level",0,7)==l&&Number(rec,"size",1,128)==side&&
                        Number(rec,"byteLength",4,MaximumPayloadBudget)==side*side*layers*4,"Runtime level geometry mismatch");
                    levelHashes[l]=Hash(rec,"sha256");
                }
                banks.Add(new LazyTextureBankRecord(b,layers,file,length,sha,levelHashes));
            }
            var spriteDocs=J.Arr(J.Get(doc,"sprites"));Checks.Require(spriteDocs.Count==count,"Runtime sprite count mismatch");
            var sprites=new List<TextureSprite>();string previous=null;
            for(int i=0;i<count;i++)
            {
                var s=J.Obj(spriteDocs[i]);J.Keys(s,"spriteKey","digestHex","family","palette","complexity","nativeSize","bankIndex","layerIndex","sourceRGBAsha256","resolvedLevelSha256");
                string digest=Hash(s,"digestHex"),family=Text(s,"family"),palette=Text(s,"palette"),sourceHash=Hash(s,"sourceRGBAsha256");
                int complexity=Number(s,"complexity",1,8);Checks.Require(Number(s,"nativeSize",16,128)==size&&
                    Number(s,"bankIndex",0,banks.Count-1)==i/capacity&&Number(s,"layerIndex",0,255)==i%capacity,"Runtime sprite placement mismatch");
                string order=family+"/"+palette+"/"+complexity.ToString(CultureInfo.InvariantCulture)+"/"+digest;
                Checks.Require(previous==null||string.CompareOrdinal(previous,order)<0,"Runtime sprites duplicate/unsorted");previous=order;
                string key=CanonicalKey(digest,family,palette,complexity,size,sourceHash);Checks.Require(Text(s,"spriteKey")==key,"Runtime sprite key changed");
                var hashes=J.Arr(J.Get(s,"resolvedLevelSha256"));Checks.Require(hashes.Count==levels,"Runtime sprite level count mismatch");
                var values=new string[levels];for(int l=0;l<levels;l++)values[l]=J.Hash(hashes[l]);
                sprites.Add(new TextureSprite(key,digest,family,palette,complexity,i/capacity,i%capacity,values));
            }
            return new LazyTextureBundleData(manifestSha,kind,artifactSha,transportSha,sourceSha,size,expectedPayload,capacity,banks,sprites,bankReader);
        }
    }

    public static class LazyTextureBundleDirectory
    {
        public static LazyTextureBundleData LoadDescriptor(string descriptorPath, int maxPayloadBytes=LazyTextureBundleData.MaximumPayloadBudget,
            Action<string> beforeBankRead=null)
        {
            Checks.Require(PathExtension(descriptorPath)==".bfresolved","Expected .bfresolved descriptor");
            string full=System.IO.Path.GetFullPath(descriptorPath),root=System.IO.Path.GetDirectoryName(full);
            Checks.Require(!System.IO.File.Exists(System.IO.Path.Combine(root,"failure.json")),"Runtime staging directory carries a failure marker");
            var descriptor=J.Obj(StrictJson.Parse(TextureBundleDirectory.ReadBounded(full,4096)));
            J.Keys(descriptor,"schema","publicOnly","manifestFile","manifestSha256");
            J.Eq(J.Get(descriptor,"schema"),"bytefables.unity-lazy-runtime.v1");J.Bool(J.Get(descriptor,"publicOnly"),true);J.Eq(J.Get(descriptor,"manifestFile"),"manifest.json");
            string manifestSha=J.Hash(J.Get(descriptor,"manifestSha256"));
            var manifest=TextureBundleDirectory.ReadBounded(System.IO.Path.Combine(root,"manifest.json"),StrictJson.MaxBytes);
            return LazyTextureBundleData.Load(manifest,(name,limit)=>{
                Checks.Require(name.Length==19&&name.StartsWith("banks/bank-",StringComparison.Ordinal)&&name.EndsWith(".ktx2",StringComparison.Ordinal),"Invalid lazy runtime bank path");
                if(beforeBankRead!=null)beforeBankRead(name);
                return TextureBundleDirectory.ReadBounded(System.IO.Path.Combine(root,name.Replace('/',System.IO.Path.DirectorySeparatorChar)),limit);
            },manifestSha,maxPayloadBytes);
        }
        private static string PathExtension(string path){return System.IO.Path.GetExtension(path);}
    }
}
