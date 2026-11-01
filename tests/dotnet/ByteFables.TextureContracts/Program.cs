using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.Encodings.Web;
using System.Text.Json;
using System.Text.Json.Nodes;
using ByteFables.Textures.Core;

internal static class Program
{
    private static int tests;
    private static void Need(bool value, string message) { if (!value) throw new Exception(message); }
    private static void Test(string name, Action action) { action(); tests++; Console.WriteLine("PASS " + name); }
    private static void Reject(Action action)
    {
        try { action(); } catch (TextureContractException) { return; }
        throw new Exception("Invalid input was accepted");
    }
    private static byte[] Json(JsonNode node) { return Encoding.UTF8.GetBytes(node.ToJsonString(new JsonSerializerOptions { WriteIndented = true, Encoder = JavaScriptEncoder.UnsafeRelaxedJsonEscaping }) + "\n"); }
    public static int Main(string[] args)
    {
        try
        {
            string vector = "tests/vectors/artwork-ktx2-v1.json", descriptor = null;
            for (int i = 0; i < args.Length; i += 2)
            {
                if (i + 1 == args.Length) throw new Exception("Missing argument value");
                if (args[i] == "--vector") vector = args[i + 1];
                else if (args[i] == "--descriptor") descriptor = args[i + 1];
                else throw new Exception("Unknown argument " + args[i]);
            }
            var fixture = JsonNode.Parse(File.ReadAllText(vector));
            var manifest = Json(fixture["transport"]);
            var files = new Dictionary<string, byte[]>(StringComparer.Ordinal);
            foreach (var item in fixture["files"].AsObject()) files.Add(item.Key, Convert.FromBase64String(item.Value.GetValue<string>()));
            Func<string, int, byte[]> reader = (name, max) => (byte[])files[name].Clone();
            var data = TextureBundleData.Load(manifest, reader);
            Test("frozen Python/JavaScript vector imports into C#", () => { Need(data.Sprites.Count == 4 && data.Banks.Count == 2 && data.NativeSize == 16, "Geometry mismatch"); });
            Test("all individual layer hashes", () => {
                foreach (var sprite in data.Sprites)
                    for (int level = 0; level < data.Banks[sprite.BankIndex].LevelCount; level++)
                        Need(TextureHashes.Sha256(data.Banks[sprite.BankIndex].CopyLayer(level, sprite.LayerIndex)) == sprite.LevelHashes[level], "Layer hash changed");
            });
            Test("manifest trust pin checked before file access", () => {
                int calls = 0; Reject(() => TextureBundleData.Load(manifest, (n,m) => { calls++; return files[n]; }, new string('0',64))); Need(calls == 0, "Untrusted manifest read files");
            });
            Test("checksummed payload snapshot survives caller mutation", () => {
                var raw = (byte[])files["banks/bank-000.ktx2"].Clone(); var parsed = Ktx2ArrayData.Parse(raw); var expected = parsed.CopyLayer(0,0);
                Array.Clear(raw,0,raw.Length); Need(parsed.CopyLayer(0,0).SequenceEqual(expected), "Parser retained caller buffer");
                var copy = parsed.CopyLayer(0,0); copy[0] ^= 255; Need(parsed.CopyLayer(0,0).SequenceEqual(expected), "Parser exposed its private buffer");
            });
            Test("bad headers and descriptors rejected", () => {
                byte[] raw = files["banks/bank-000.ktx2"];
                foreach (int at in new[] {0,12,16,20,24,28,32,36,40,44,48,52,56,60,64,72,80,88,96,200,215,300}) {
                    byte[] changed=(byte[])raw.Clone();changed[at]^=0x80;Reject(()=>Ktx2ArrayData.Parse(changed));
                }
            });
            Test("truncation and trailing bytes rejected", () => {
                var raw=files["banks/bank-000.ktx2"]; Reject(()=>Ktx2ArrayData.Parse(raw.Take(raw.Length-1).ToArray()));
                Reject(()=>Ktx2ArrayData.Parse(raw.Concat(new byte[]{0}).ToArray()));
            });
            Test("duplicate keys, floats, bad UTF8 and nesting rejected", () => {
                foreach (string s in new[]{"{\"a\":1,\"a\":2}","[1.0]","[NaN]","[01]","[true,]","{\"a\":\"\\uD800\"}",new string('[',26)+"0"+new string(']',26)})
                    Reject(()=>StrictJson.Parse(Encoding.UTF8.GetBytes(s)));
                Reject(()=>StrictJson.Parse(new byte[]{0xff}));
            });
            Test("unknown JSON fields rejected", () => {
                var changed=fixture["transport"].DeepClone();changed["unexpected"]=true;Reject(()=>TextureBundleData.Load(Json(changed),reader));
            });
            Test("bank path traversal rejected without opening it", () => {
                var changed=fixture["transport"].DeepClone();changed["banks"][0]["file"]="../bank.ktx2";
                Reject(()=>TextureBundleData.Load(Json(changed),reader));
            });
            Test("bank checksums and payload budget rejected", () => {
                var changed=fixture["transport"].DeepClone();changed["banks"][0]["sha256"]=new string('0',64);
                Reject(()=>TextureBundleData.Load(Json(changed),reader));Reject(()=>TextureBundleData.Load(manifest,reader,maxPayloadBytes:1));
            });
            Test("changed identity key rejected even with updated manifest binding", () => {
                var source=JsonNode.Parse(files["source-manifest.json"]);source["sprites"][0]["spriteKey"]="bfalpha1-"+new string('0',64);var altered=Json(source);
                var changed=fixture["transport"].DeepClone();changed["sourceManifest"]["sha256"]=TextureHashes.Sha256(altered);changed["sourceManifest"]["byteLength"]=altered.Length;
                Reject(()=>TextureBundleData.Load(Json(changed),(n,m)=>n=="source-manifest.json"?altered:files[n]));
            });
            Test("indices and exact full-key lookup", () => {
                Need(data.Find(data.Sprites[0].SpriteKey).DigestHex==data.Sprites[0].DigestHex,"Lookup mismatch");
                Reject(()=>data.Find(data.Sprites[0].DigestHex));Reject(()=>data.Banks[0].CopyLayer(-1,0));Reject(()=>data.Banks[0].CopyLayer(0,2));
            });
            if (descriptor != null)
            {
                var staged=TextureBundleDirectory.LoadDescriptor(descriptor);
                Test("staged descriptor imports with all hashes and metadata",()=>Need(staged.Sprites.Count>0,"Empty staging"));
                Test("Unity row reversal on every staged mip/layer",()=>{
                    foreach(var sprite in staged.Sprites) {
                        var bank=staged.Banks[sprite.BankIndex];
                        for(int mip=0;mip<bank.LevelCount;mip++) {
                            var top=bank.CopyLayer(mip,sprite.LayerIndex);var bottom=bank.CopyLayer(mip,sprite.LayerIndex,true);int side=bank.LevelSize(mip),stride=side*4;
                            for(int y=0;y<side;y++) for(int x=0;x<stride;x++) Need(top[y*stride+x]==bottom[(side-1-y)*stride+x],"Row reversal failed");
                        }
                    }
                });
            }
            Console.WriteLine(JsonSerializer.Serialize(new { status="passed", tests, unityExecuted=false, gpuExecuted=false }));return 0;
        }
        catch(Exception error) { Console.Error.WriteLine(error);return 1; }
    }
}
