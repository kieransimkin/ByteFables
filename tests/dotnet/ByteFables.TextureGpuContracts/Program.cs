using System;
using System.Collections.Generic;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using ByteFables.Textures.Core;

internal static class Program
{
    private static int tests;
    private static void Need(bool yes,string message){if(!yes)throw new Exception(message);}
    private static void Test(string name,Action action){action();tests++;Console.WriteLine("PASS "+name);}
    private static void Reject(Action action){try{action();}catch(TextureContractException){return;}throw new Exception("Invalid input was accepted");}
    private static byte[] Json(JsonNode node){return Encoding.UTF8.GetBytes(node.ToJsonString(new JsonSerializerOptions{WriteIndented=true})+"\n");}
    private static int LevelBytes(int side){int blocks=Math.Max(1,(side+3)/4);return blocks*blocks*16*2;}
    private static string Key(string digest,string sourceHash)
    {
        string json="{\n  \"profile\": \"bytefables.premultiplied-area-mips.v1\",\n  \"digestHex\": \""+digest+
            "\",\n  \"family\": \"sigil\",\n  \"palette\": \"neon\",\n  \"complexity\": 4,\n  \"nativeSize\": 16,\n  \"sourceRGBAsha256\": \""+sourceHash+"\"\n}\n";
        return "bfalpha1-"+TextureHashes.Sha256(Encoding.UTF8.GetBytes(json));
    }
    public static int Main()
    {
        try
        {
            var files=new Dictionary<string,byte[]>(StringComparer.Ordinal);
            var formats=new JsonArray();
            var defs=new[]{new[]{"bc7","bc7","BC7"},new[]{"astc4x4","astc","ASTC_4x4"},new[]{"etc2rgba8","etc-rgba","ETC2_RGBA8"}};
            foreach(var def in defs)
            {
                var levels=new JsonArray();int total=0;
                for(int mip=0;mip<5;mip++)
                {
                    int side=16>>mip,length=LevelBytes(side);var raw=new byte[length];
                    for(int i=0;i<raw.Length;i++)raw[i]=(byte)((i+mip*17+def[0].Length*13)&255);
                    string path="formats/"+def[0]+"/bank-000-mip-"+mip.ToString("D2")+".bin";files.Add(path,raw);total+=length;
                    levels.Add(new JsonObject{{"level",mip},{"size",side},{"file",path},{"byteLength",length},{"sha256",TextureHashes.Sha256(raw)}});
                }
                formats.Add(new JsonObject{{"id",def[0]},{"ktxTarget",def[1]},{"unityTextureFormat",def[2]},
                    {"blockWidth",4},{"blockHeight",4},{"blockBytes",16},{"payloadBytes",total},
                    {"banks",new JsonArray(new JsonObject{{"index",0},{"layerCount",2},{"levels",levels}})}});
            }
            string d0=new string('0',64),d1=new string('1',64),s0=new string('2',64),s1=new string('3',64);
            var sprites=new JsonArray(
                new JsonObject{{"spriteKey",Key(d0,s0)},{"digestHex",d0},{"family","sigil"},{"palette","neon"},{"complexity",4},{"nativeSize",16},{"bankIndex",0},{"layerIndex",0},{"sourceRGBAsha256",s0}},
                new JsonObject{{"spriteKey",Key(d1,s1)},{"digestHex",d1},{"family","sigil"},{"palette","neon"},{"complexity",4},{"nativeSize",16},{"bankIndex",0},{"layerIndex",1},{"sourceRGBAsha256",s1}});
            var manifest=new JsonObject{{"schema",GpuBlockTextureBundleData.Schema},{"profile",GpuBlockTextureBundleData.Profile},{"status","passed"},{"publicOnly",true},{"guarantee","presentation-only"},
                {"tool",new JsonObject{{"name","Khronos KTX-Software"},{"version","4.4.2"}}},
                {"sourceUastc",new JsonObject{{"file","source-uastc.json"},{"byteLength",123},{"sha256",new string('a',64)}}},
                {"sourceManifest",new JsonObject{{"file","source-manifest.json"},{"byteLength",456},{"sha256",new string('b',64)}}},
                {"nativeSize",16},{"layersPerBank",2},{"spriteCount",2},{"levelCount",5},{"formats",formats},{"sprites",sprites}};
            var bytes=Json(manifest);int reads=0;
            Func<string,int,byte[]> reader=(path,limit)=>{reads++;var source=files[path];Need(source.Length==limit,"Reader limit changed");return (byte[])source.Clone();};
            var data=GpuBlockTextureBundleData.Load(bytes,reader);
            Test("metadata-only open reads no block files",()=>Need(reads==0,"Opening metadata read block bytes"));
            Test("stable full-key lookup reads no blocks",()=>{Need(data.Find(Key(d0,s0)).DigestHex==d0,"Identity lookup failed");Need(reads==0,"Identity lookup read block bytes");});
            Test("all three canonical format mappings",()=>{Need(data.FindFormat("bc7").UnityTextureFormat=="BC7","BC7 mapping");Need(data.FindFormat("astc4x4").UnityTextureFormat=="ASTC_4x4","ASTC mapping");Need(data.FindFormat("etc2rgba8").UnityTextureFormat=="ETC2_RGBA8","ETC2 mapping");});
            Test("one requested mip performs one bounded read",()=>{var raw=data.LoadLevel("bc7",0,0);Need(reads==1&&raw.Length==LevelBytes(16),"Lazy block read mismatch");raw[0]^=255;Need(data.LoadLevel("bc7",0,0)[0]!=raw[0]&&reads==2,"Returned block buffer was not isolated");});
            Test("per-layer block geometry",()=>Need(data.PerLayerBytes("bc7",0)*2==LevelBytes(16)&&data.PerLayerBytes("bc7",4)==16,"Block geometry mismatch"));
            Test("wrong block checksum rejected",()=>{var bad=(JsonObject)manifest.DeepClone();var level0=bad["formats"].AsArray()[0].AsObject()["banks"].AsArray()[0].AsObject()["levels"].AsArray()[0].AsObject();level0["sha256"]=new string('f',64);var d=GpuBlockTextureBundleData.Load(Json(bad),reader);Reject(()=>d.LoadLevel("bc7",0,0));});
            Test("noncanonical Khronos target mapping rejected",()=>{var bad=(JsonObject)manifest.DeepClone();bad["formats"].AsArray()[0].AsObject()["ktxTarget"]="astc";Reject(()=>GpuBlockTextureBundleData.Load(Json(bad),reader));});
            Console.WriteLine(JsonSerializer.Serialize(new{status="passed",tests,unityExecuted=false,gpuExecuted=false}));return 0;
        }
        catch(Exception error){Console.Error.WriteLine(error);return 1;}
    }
}
