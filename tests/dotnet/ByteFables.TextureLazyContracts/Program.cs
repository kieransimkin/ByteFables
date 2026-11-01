using System;
using System.IO;
using System.Threading;
using System.Threading.Tasks;
using ByteFables.Textures.Core;

internal static class Program
{
    private static int tests;
    private static void Need(bool yes,string message){if(!yes)throw new Exception(message);}
    private static void Test(string name,Action action){action();tests++;Console.WriteLine("PASS "+name);}
    private static void Reject(Action action){try{action();}catch(TextureContractException){return;}throw new Exception("Invalid input accepted");}

    public static int Main(string[] args)
    {
        try
        {
            if(args.Length!=2||args[0]!="--descriptor")throw new Exception("Usage: --descriptor path/runtime.bfresolved");
            string descriptor=args[1];int reads=0;
            var lazy=LazyTextureBundleDirectory.LoadDescriptor(descriptor,beforeBankRead:name=>Interlocked.Increment(ref reads));
            Test("metadata open performs zero bank reads",()=>Need(reads==0,"Opening metadata read a KTX bank"));
            Test("identity lookup needs no bank bytes",()=>{var s=lazy.Find(lazy.Sprites[0].SpriteKey);Need(s.DigestHex==lazy.Sprites[0].DigestHex,"Identity lookup mismatch");Need(reads==0,"Lookup read a bank");});
            Test("explicit LoadBank reads exactly one bank and verifies it",()=>{var b=lazy.LoadBank(0);Need(b.Layers==lazy.Banks[0].Layers,"Bank geometry mismatch");Need(reads==1,"Unexpected bank read count");});
            Test("CPU residency caches and hits without another disk read",()=>{
                using(var cache=new TextureCpuResidency(lazy,lazy.Banks[0].ByteLength))
                {
                    using(var a=cache.AcquireBank(0))Need(a.Data.Layers>0,"Empty bank");int after=reads;
                    using(var b=cache.AcquireBank(0))Need(b.Data.Layers>0,"Empty cached bank");
                    Need(reads==after&&cache.Hits>=1,"CPU cache reread a resident bank");
                }
            });
            Test("concurrent acquire is coalesced",()=>{
                using(var cache=new TextureCpuResidency(lazy,lazy.Banks[0].ByteLength))
                {
                    int before=reads;var a=cache.AcquireBankAsync(0,CancellationToken.None);var b=cache.AcquireBankAsync(0,CancellationToken.None);
                    Task.WaitAll(a,b);using(a.Result){}using(b.Result){}Need(reads==before+1,"Concurrent load was not coalesced");Need(cache.Loads==1,"Load counter mismatch");
                }
            });
            if(lazy.Banks.Count>1)
            {
                Test("one-bank budget evicts unpinned LRU",()=>{
                    int budget=Math.Max(lazy.Banks[0].ByteLength,lazy.Banks[1].ByteLength);
                    using(var cache=new TextureCpuResidency(lazy,budget))
                    {
                        using(cache.AcquireBank(0)){}using(cache.AcquireBank(1)){}Need(cache.ResidentBanks==1&&cache.Evictions==1,"Expected one LRU eviction");
                    }
                });
                Test("pinned bank prevents unsafe replacement",()=>{
                    int budget=Math.Max(lazy.Banks[0].ByteLength,lazy.Banks[1].ByteLength);
                    using(var cache=new TextureCpuResidency(lazy,budget))using(var lease=cache.AcquireBank(0))
                        Reject(()=>{using(cache.AcquireBank(1)){};});
                });
            }
            Test("cancelled waiter is not a successful lease",()=>{
                using(var cache=new TextureCpuResidency(lazy,lazy.Banks[0].ByteLength))
                { var c=new CancellationTokenSource();c.Cancel();try{cache.AcquireBankAsync(0,c.Token).GetAwaiter().GetResult();throw new Exception("Cancelled acquire passed");}catch(OperationCanceledException){} }
            });
            Console.WriteLine("{\"status\":\"passed\",\"tests\":"+tests+",\"unityExecuted\":false,\"gpuExecuted\":false}");return 0;
        }
        catch(Exception error){Console.Error.WriteLine(error);return 1;}
    }
}
