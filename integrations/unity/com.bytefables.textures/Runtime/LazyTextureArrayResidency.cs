using System;
using System.Collections;
using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;
using ByteFables.Textures.Core;
using UnityEngine;

namespace ByteFables.Textures
{
    /// <summary>Independent CPU/disk and GPU residency over a LazyTextureBundleData source.</summary>
    public sealed class LazyTextureArrayResidency : IDisposable
    {
        private sealed class Entry { public Texture2DArray Texture; public int Bytes,References; public long Tick; }
        private readonly int mainThread; private readonly LazyTextureBundleData source; private readonly TextureCpuResidency cpu;
        private readonly Dictionary<int,Entry> gpu=new Dictionary<int,Entry>();private readonly FilterMode filter;
        private int gpuBudget,gpuBytes,peakGpuBytes;private long clock;private bool disposed;private int evictions;
        public TextureCpuResidency Cpu { get { return cpu; } }
        public int GpuResidentBytes { get { return gpuBytes; } } public int PeakGpuResidentBytes { get { return peakGpuBytes; } }
        public int GpuResidentBanks { get { return gpu.Count; } } public int GpuEvictions { get { return evictions; } }
        public LazyTextureArrayResidency(LazyTextureBundleData source,int cpuBudgetBytes,int gpuBudgetBytes,FilterMode filter=FilterMode.Trilinear)
        {
            this.source=source??throw new ArgumentNullException(nameof(source));if(filter!=FilterMode.Point&&filter!=FilterMode.Trilinear)throw new ArgumentException("Use Point or Trilinear",nameof(filter));
            if(gpuBudgetBytes<1||gpuBudgetBytes>LazyTextureBundleData.MaximumPayloadBudget)throw new ArgumentOutOfRangeException(nameof(gpuBudgetBytes));
            this.filter=filter;gpuBudget=gpuBudgetBytes;cpu=new TextureCpuResidency(source,cpuBudgetBytes);mainThread=Thread.CurrentThread.ManagedThreadId;
        }
        private void MainThread(){if(Thread.CurrentThread.ManagedThreadId!=mainThread)throw new InvalidOperationException("GPU residency must be used on its creating Unity thread");if(disposed)throw new ObjectDisposedException(nameof(LazyTextureArrayResidency));}
        private void Touch(Entry e){e.Tick=++clock;}
        private int PinnedGpuBytes(){int n=0;foreach(var e in gpu.Values)if(e.References>0)n=checked(n+e.Bytes);return n;}
        private bool EvictOne()
        {
            int victim=-1;long tick=long.MaxValue;foreach(var p in gpu)if(p.Value.References==0&&p.Value.Tick<tick){victim=p.Key;tick=p.Value.Tick;}
            if(victim<0)return false;var e=gpu[victim];gpu.Remove(victim);gpuBytes-=e.Bytes;evictions++;TextureArrayUpload.Destroy(e.Texture);return true;
        }
        private void MakeRoom(int bytes){if(bytes>gpuBudget)throw new TextureContractException("GPU bank exceeds residency budget");while(gpuBytes+bytes>gpuBudget)if(!EvictOne())throw new TextureContractException("GPU residency budget is pinned by active leases");}
        public TextureBankLease AcquireBank(int bankIndex)
        {
            MainThread();if(bankIndex<0||bankIndex>=source.Banks.Count)throw new ArgumentOutOfRangeException(nameof(bankIndex));
            Entry entry;if(gpu.TryGetValue(bankIndex,out entry)){entry.References++;Touch(entry);return new TextureBankLease(this,bankIndex,entry.Texture);}
            using(var bank=cpu.AcquireBank(bankIndex))
            {
                int bytes=source.BankPayloadBytes(bankIndex);MakeRoom(bytes);var texture=TextureArrayUpload.Create(bank.Data,filter,keepReadable:false);
                entry=new Entry{Texture=texture,Bytes=bytes,References=1};Touch(entry);gpu.Add(bankIndex,entry);gpuBytes+=bytes;if(gpuBytes>peakGpuBytes)peakGpuBytes=gpuBytes;
                return new TextureBankLease(this,bankIndex,texture);
            }
        }
        public TextureSpriteLease AcquireSprite(string fullSpriteKey)
        { var sprite=source.Find(fullSpriteKey);return new TextureSpriteLease(AcquireBank(sprite.BankIndex),sprite); }
        public Task PrefetchCpuAsync(IEnumerable<int> banks,CancellationToken cancellationToken)
        { if(disposed)throw new ObjectDisposedException(nameof(LazyTextureArrayResidency));return cpu.PrefetchAsync(banks,cancellationToken); }
        public IEnumerator PrefetchGpu(IList<int> banks)
        {
            if(banks==null)throw new ArgumentNullException(nameof(banks));
            for(int i=0;i<banks.Count;i++){using(var lease=AcquireBank(banks[i])){}yield return null;}
        }
        public void SetBudgets(int cpuBytes,int gpuBytes)
        {
            MainThread();if(gpuBytes<1||gpuBytes>LazyTextureBundleData.MaximumPayloadBudget)throw new ArgumentOutOfRangeException(nameof(gpuBytes));
            if(PinnedGpuBytes()>gpuBytes)throw new TextureContractException("GPU residency budget is pinned by active leases");
            cpu.SetBudget(cpuBytes);while(this.gpuBytes>gpuBytes)if(!EvictOne())throw new TextureContractException("GPU residency cannot satisfy requested budget");gpuBudget=gpuBytes;
        }
        internal void Release(int bankIndex)
        {
            if(Thread.CurrentThread.ManagedThreadId!=mainThread)throw new InvalidOperationException("GPU residency lease must be released on its creating Unity thread");
            Entry entry;if(!gpu.TryGetValue(bankIndex,out entry))return;if(entry.References<=0)throw new TextureContractException("GPU residency lease underflow");entry.References--;Touch(entry);
            if(disposed&&entry.References==0){gpu.Remove(bankIndex);gpuBytes-=entry.Bytes;TextureArrayUpload.Destroy(entry.Texture);}
        }
        public void Dispose()
        {
            if(disposed)return;MainThread();disposed=true;var remove=new List<int>();foreach(var p in gpu)if(p.Value.References==0)remove.Add(p.Key);
            foreach(var bank in remove){var e=gpu[bank];gpu.Remove(bank);gpuBytes-=e.Bytes;TextureArrayUpload.Destroy(e.Texture);}cpu.Dispose();
        }
        public sealed class TextureBankLease:IDisposable
        {
            private LazyTextureArrayResidency owner;private readonly int bankIndex;public Texture2DArray Texture{get;private set;}
            internal TextureBankLease(LazyTextureArrayResidency owner,int bank,Texture2DArray texture){this.owner=owner;bankIndex=bank;Texture=texture;}
            public void Dispose(){var current=owner;if(current==null)return;owner=null;Texture=null;current.Release(bankIndex);}
        }
        public sealed class TextureSpriteLease:IDisposable
        {
            private TextureBankLease bank;public TextureSprite Sprite{get;private set;}public Texture2DArray Texture{get{if(bank==null)throw new ObjectDisposedException(nameof(TextureSpriteLease));return bank.Texture;}}
            internal TextureSpriteLease(TextureBankLease bank,TextureSprite sprite){this.bank=bank;Sprite=sprite;}
            public void Dispose(){var current=bank;if(current==null)return;bank=null;current.Dispose();}
        }
    }
}
