using System;
using System.Collections.Generic;
using System.Globalization;
using System.Text;

namespace ByteFables.Textures.Core
{
    public sealed class GpuBlockLevelRecord
    {
        public int Level { get; private set; }
        public int Size { get; private set; }
        public string File { get; private set; }
        public int ByteLength { get; private set; }
        public string Sha256 { get; private set; }
        internal GpuBlockLevelRecord(int level,int size,string file,int bytes,string sha)
        { Level=level;Size=size;File=file;ByteLength=bytes;Sha256=sha; }
    }
    public sealed class GpuBlockBankRecord
    {
        public int Index { get; private set; }
        public int Layers { get; private set; }
        public IReadOnlyList<GpuBlockLevelRecord> Levels { get; private set; }
        internal GpuBlockBankRecord(int index,int layers,List<GpuBlockLevelRecord> levels)
        { Index=index;Layers=layers;Levels=levels.AsReadOnly(); }
    }
    public sealed class GpuBlockFormatRecord
    {
        public string Id { get; private set; }
        public string UnityTextureFormat { get; private set; }
        public int BlockWidth { get; private set; }
        public int BlockHeight { get; private set; }
        public int BlockBytes { get; private set; }
        public int PayloadBytes { get; private set; }
        public IReadOnlyList<GpuBlockBankRecord> Banks { get; private set; }
        internal GpuBlockFormatRecord(string id,string unity,int bw,int bh,int bb,int payload,List<GpuBlockBankRecord> banks)
        { Id=id;UnityTextureFormat=unity;BlockWidth=bw;BlockHeight=bh;BlockBytes=bb;PayloadBytes=payload;Banks=banks.AsReadOnly(); }
    }

    /// <summary>Metadata-first raw GPU block bundle. Raw level files are opened only on LoadLevel.</summary>
    public sealed class GpuBlockTextureBundleData
    {
        public const string Schema="bytefables.gpu-block-texture-bundle.v1";
        public const string Profile="bytefables.gpu-blocks-4x4.v1";
        public const int MaximumPayloadBudget=128*1024*1024;
        private readonly Func<string,int,byte[]> reader;
        private readonly Dictionary<string,GpuBlockFormatRecord> byFormat;
        private readonly Dictionary<string,int> byKey;
        public string ManifestSha256 { get; private set; }
        public string SourceUastcSha256 { get; private set; }
        public int NativeSize { get; private set; }
        public int LayersPerBank { get; private set; }
        public IReadOnlyList<GpuBlockFormatRecord> Formats { get; private set; }
        public IReadOnlyList<TextureSprite> Sprites { get; private set; }

        private GpuBlockTextureBundleData(string manifestSha,string uastcSha,int size,int capacity,
            List<GpuBlockFormatRecord> formats,List<TextureSprite> sprites,Func<string,int,byte[]> reader)
        {
            ManifestSha256=manifestSha;SourceUastcSha256=uastcSha;NativeSize=size;LayersPerBank=capacity;
            Formats=formats.AsReadOnly();Sprites=sprites.AsReadOnly();this.reader=reader;
            byFormat=new Dictionary<string,GpuBlockFormatRecord>(StringComparer.Ordinal);
            foreach(var format in formats)byFormat.Add(format.Id,format);
            byKey=new Dictionary<string,int>(StringComparer.Ordinal);for(int i=0;i<sprites.Count;i++)byKey.Add(sprites[i].SpriteKey,i);
        }
        public GpuBlockFormatRecord FindFormat(string id)
        { GpuBlockFormatRecord result=null;Checks.Require(id!=null&&byFormat.TryGetValue(id,out result),"Unknown GPU block format");return result; }
        public TextureSprite Find(string fullSpriteKey)
        { int i=-1;Checks.Require(fullSpriteKey!=null&&byKey.TryGetValue(fullSpriteKey,out i),"Unknown full sprite key");return Sprites[i]; }
        public byte[] LoadLevel(string formatId,int bankIndex,int level)
        {
            var format=FindFormat(formatId);Checks.Require(bankIndex>=0&&bankIndex<format.Banks.Count,"Invalid GPU bank index");
            var bank=format.Banks[bankIndex];Checks.Require(level>=0&&level<bank.Levels.Count,"Invalid GPU mip index");var record=bank.Levels[level];
            var data=reader(record.File,record.ByteLength);Checks.Require(data!=null&&data.Length==record.ByteLength,"GPU block byte count mismatch");
            var snapshot=(byte[])data.Clone();Checks.Require(TextureHashes.Sha256(snapshot)==record.Sha256,"GPU block checksum mismatch");return snapshot;
        }
        public int PerLayerBytes(string formatId,int level)
        {
            var format=FindFormat(formatId);Checks.Require(level>=0&&level<Ktx2ArrayData.LevelsFor(NativeSize),"Invalid GPU mip index");
            int side=NativeSize>>level,bx=Math.Max(1,(side+format.BlockWidth-1)/format.BlockWidth),by=Math.Max(1,(side+format.BlockHeight-1)/format.BlockHeight);
            return checked(bx*by*format.BlockBytes);
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
        public static GpuBlockTextureBundleData Load(byte[] manifestBytes,Func<string,int,byte[]> blockReader,string expectedManifestSha256=null)
        {
            if(blockReader==null)throw new ArgumentNullException(nameof(blockReader));Checks.Require(manifestBytes!=null&&manifestBytes.Length<=StrictJson.MaxBytes,"Invalid GPU block manifest size");
            var snapshot=(byte[])manifestBytes.Clone();string manifestSha=TextureHashes.Sha256(snapshot);if(expectedManifestSha256!=null)Checks.Require(expectedManifestSha256==manifestSha,"GPU block manifest pin mismatch");
            var doc=J.Obj(StrictJson.Parse(snapshot));J.Keys(doc,"schema","profile","status","publicOnly","guarantee","tool","sourceUastc","sourceManifest","nativeSize","layersPerBank","spriteCount","levelCount","formats","sprites");
            J.Eq(J.Get(doc,"schema"),Schema);J.Eq(J.Get(doc,"profile"),Profile);J.Eq(J.Get(doc,"status"),"passed");J.Bool(J.Get(doc,"publicOnly"),true);J.Eq(J.Get(doc,"guarantee"),"presentation-only");
            var tool=J.Obj(J.Get(doc,"tool"));J.Keys(tool,"name","version");J.Eq(J.Get(tool,"name"),"Khronos KTX-Software");J.Eq(J.Get(tool,"version"),"4.4.2");
            var sourceUastc=J.Obj(J.Get(doc,"sourceUastc"));J.Keys(sourceUastc,"file","byteLength","sha256");J.Eq(J.Get(sourceUastc,"file"),"source-uastc.json");Number(sourceUastc,"byteLength",1,StrictJson.MaxBytes);string uastcSha=Hash(sourceUastc,"sha256");
            var sourceManifest=J.Obj(J.Get(doc,"sourceManifest"));J.Keys(sourceManifest,"file","byteLength","sha256");J.Eq(J.Get(sourceManifest,"file"),"source-manifest.json");Number(sourceManifest,"byteLength",1,StrictJson.MaxBytes);Hash(sourceManifest,"sha256");
            int size=Number(doc,"nativeSize",16,128);Checks.Require(size==16||size==32||size==64||size==128,"Invalid GPU block native size");int capacity=Number(doc,"layersPerBank",1,256),count=Number(doc,"spriteCount",1,1024),levels=Ktx2ArrayData.LevelsFor(size);Checks.Require(Number(doc,"levelCount",1,8)==levels,"GPU block mip count mismatch");
            var formatsDoc=J.Arr(J.Get(doc,"formats"));Checks.Require(formatsDoc.Count==3,"GPU block format count mismatch");var formats=new List<GpuBlockFormatRecord>();var formatIds=new HashSet<string>();
            foreach(var item in formatsDoc)
            {
                var fmt=J.Obj(item);J.Keys(fmt,"id","ktxTarget","unityTextureFormat","blockWidth","blockHeight","blockBytes","payloadBytes","banks");string id=Text(fmt,"id"),unity=Text(fmt,"unityTextureFormat"),ktxTarget=Text(fmt,"ktxTarget");
                Checks.Require((id=="bc7"&&unity=="BC7"&&ktxTarget=="bc7")||
                    (id=="astc4x4"&&unity=="ASTC_4x4"&&ktxTarget=="astc")||
                    (id=="etc2rgba8"&&unity=="ETC2_RGBA8"&&ktxTarget=="etc-rgba"),"Unsupported GPU block format");Checks.Require(formatIds.Add(id),"Duplicate GPU block format");
                int bw=Number(fmt,"blockWidth",4,4),bh=Number(fmt,"blockHeight",4,4),bb=Number(fmt,"blockBytes",16,16),payload=Number(fmt,"payloadBytes",1,MaximumPayloadBudget);
                var banksDoc=J.Arr(J.Get(fmt,"banks"));int expectedBanks=(count+capacity-1)/capacity;Checks.Require(banksDoc.Count==expectedBanks,"GPU block bank count mismatch");var banks=new List<GpuBlockBankRecord>();int sum=0;
                for(int b=0;b<banksDoc.Count;b++)
                {
                    var bank=J.Obj(banksDoc[b]);J.Keys(bank,"index","layerCount","levels");int layers=Math.Min(capacity,count-b*capacity);Checks.Require(Number(bank,"index",0,15)==b&&Number(bank,"layerCount",1,256)==layers,"GPU block bank mismatch");
                    var levelsDoc=J.Arr(J.Get(bank,"levels"));Checks.Require(levelsDoc.Count==levels,"GPU block level count mismatch");var records=new List<GpuBlockLevelRecord>();
                    for(int l=0;l<levels;l++)
                    {
                        var rec=J.Obj(levelsDoc[l]);J.Keys(rec,"level","size","file","byteLength","sha256");int side=size>>l,bx=Math.Max(1,(side+bw-1)/bw),by=Math.Max(1,(side+bh-1)/bh),bytes=checked(bx*by*bb*layers);
                        Checks.Require(Number(rec,"level",0,7)==l&&Number(rec,"size",1,128)==side&&Number(rec,"byteLength",1,MaximumPayloadBudget)==bytes,"GPU block level geometry mismatch");string file=Text(rec,"file");Checks.Require(file=="formats/"+id+"/bank-"+b.ToString("D3",CultureInfo.InvariantCulture)+"-mip-"+l.ToString("D2",CultureInfo.InvariantCulture)+".bin","GPU block level path mismatch");records.Add(new GpuBlockLevelRecord(l,side,file,bytes,Hash(rec,"sha256")));sum=checked(sum+bytes);
                    }
                    banks.Add(new GpuBlockBankRecord(b,layers,records));
                }
                Checks.Require(sum==payload,"GPU block payload size mismatch");formats.Add(new GpuBlockFormatRecord(id,unity,bw,bh,bb,payload,banks));
            }
            var spritesDoc=J.Arr(J.Get(doc,"sprites"));Checks.Require(spritesDoc.Count==count,"GPU sprite count mismatch");var sprites=new List<TextureSprite>();string previous=null;
            for(int i=0;i<count;i++)
            {
                var s=J.Obj(spritesDoc[i]);J.Keys(s,"spriteKey","digestHex","family","palette","complexity","nativeSize","bankIndex","layerIndex","sourceRGBAsha256");string digest=Hash(s,"digestHex"),family=Text(s,"family"),palette=Text(s,"palette"),sourceHash=Hash(s,"sourceRGBAsha256");int complexity=Number(s,"complexity",1,8);Checks.Require(Number(s,"nativeSize",16,128)==size&&Number(s,"bankIndex",0,15)==i/capacity&&Number(s,"layerIndex",0,255)==i%capacity,"GPU sprite placement mismatch");string order=family+"/"+palette+"/"+complexity.ToString(CultureInfo.InvariantCulture)+"/"+digest;Checks.Require(previous==null||string.CompareOrdinal(previous,order)<0,"GPU sprites duplicate/unsorted");previous=order;string key=CanonicalKey(digest,family,palette,complexity,size,sourceHash);Checks.Require(Text(s,"spriteKey")==key,"GPU sprite key changed");sprites.Add(new TextureSprite(key,digest,family,palette,complexity,i/capacity,i%capacity,new string[levels]));
            }
            return new GpuBlockTextureBundleData(manifestSha,uastcSha,size,capacity,formats,sprites,blockReader);
        }
    }
}
