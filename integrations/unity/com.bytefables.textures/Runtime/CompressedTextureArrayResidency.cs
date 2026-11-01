using System;
using System.Collections.Generic;
using System.Threading;
using ByteFables.Textures.Core;
using UnityEngine;

namespace ByteFables.Textures
{
    /// <summary>Lease-pinned GPU LRU for one explicitly selected block-compressed format.</summary>
    public sealed class CompressedTextureArrayResidency : IDisposable
    {
        private sealed class Entry { public Texture2DArray Texture; public int Bytes,Refs; public long Tick; }
        private readonly GpuBlockTextureBundleData source;private readonly string formatId;private readonly GpuBlockFormatRecord format;private readonly int mainThread;
        private readonly Dictionary<int,Entry> resident=new Dictionary<int,Entry>();private int budget,residentBytes,peakBytes,evictions;private long clock;private bool disposed;
        public string FormatId { get { return formatId; } } public int ResidentBytes { get { return residentBytes; } } public int PeakResidentBytes { get { return peakBytes; } }
        public int ResidentBanks { get { return resident.Count; } } public int Evictions { get { return evictions; } }
        public CompressedTextureArrayResidency(GpuBlockTextureBundleData source,string formatId,int budgetBytes)
        {
            this.source=source??throw new ArgumentNullException(nameof(source));this.formatId=formatId??throw new ArgumentNullException(nameof(formatId));format=source.FindFormat(formatId);mainThread=Thread.CurrentThread.ManagedThreadId;
            if(!CompressedTextureFormatSelector.IsSupported(formatId))throw new NotSupportedException("Selected compressed format is not supported by this device");SetBudgetInitial(budgetBytes);
        }
        public static CompressedTextureArrayResidency CreateForCurrentDevice(GpuBlockTextureBundleData source,int budgetBytes)
        { var selected=CompressedTextureFormatSelector.Select(source);return new CompressedTextureArrayResidency(source,selected,budgetBytes); }
        private void SetBudgetInitial(int value){if(value<1||value>GpuBlockTextureBundleData.MaximumPayloadBudget)throw new ArgumentOutOfRangeException(nameof(value));budget=value;}
        private void RequireOpen(){if(Thread.CurrentThread.ManagedThreadId!=mainThread)throw new InvalidOperationException("Compressed GPU residency must be used on its creating Unity thread");if(disposed)throw new ObjectDisposedException(nameof(CompressedTextureArrayResidency));}
        private void Touch(Entry e){e.Tick=++clock;}
        private int BankBytes(int bank){int n=0;foreach(var level in format.Banks[bank].Levels)n=checked(n+level.ByteLength);return n;}
        private int Pinned(){int n=0;foreach(var e in resident.Values)if(e.Refs>0)n=checked(n+e.Bytes);return n;}
        private bool EvictOne(){int victim=-1;long tick=long.MaxValue;foreach(var p in resident)if(p.Value.Refs==0&&p.Value.Tick<tick){victim=p.Key;tick=p.Value.Tick;}if(victim<0)return false;var e=resident[victim];resident.Remove(victim);residentBytes-=e.Bytes;evictions++;TextureArrayUpload.Destroy(e.Texture);return true;}
        private void MakeRoom(int bytes){if(bytes>budget)throw new TextureContractException("Compressed bank exceeds GPU budget");while(residentBytes+bytes>budget)if(!EvictOne())throw new TextureContractException("Compressed GPU budget is pinned by active leases");}
        public Lease AcquireBank(int bankIndex)
        {
            RequireOpen();if(bankIndex<0||bankIndex>=format.Banks.Count)throw new ArgumentOutOfRangeException(nameof(bankIndex));Entry entry;if(resident.TryGetValue(bankIndex,out entry)){entry.Refs++;Touch(entry);return new Lease(this,bankIndex,entry.Texture);}
            int bytes=BankBytes(bankIndex);MakeRoom(bytes);var texture=CompressedTextureArrayUpload.Create(source,formatId,bankIndex);entry=new Entry{Texture=texture,Bytes=bytes,Refs=1};Touch(entry);resident.Add(bankIndex,entry);residentBytes+=bytes;if(residentBytes>peakBytes)peakBytes=residentBytes;return new Lease(this,bankIndex,texture);
        }
        public SpriteLease AcquireSprite(string fullSpriteKey){var sprite=source.Find(fullSpriteKey);return new SpriteLease(AcquireBank(sprite.BankIndex),sprite);}
        public void SetBudget(int value){RequireOpen();if(value<1||value>GpuBlockTextureBundleData.MaximumPayloadBudget)throw new ArgumentOutOfRangeException(nameof(value));if(Pinned()>value)throw new TextureContractException("Compressed GPU budget is pinned by active leases");while(residentBytes>value)if(!EvictOne())throw new TextureContractException("Compressed GPU budget cannot be satisfied");budget=value;}
        private void Release(int bank){if(Thread.CurrentThread.ManagedThreadId!=mainThread)throw new InvalidOperationException("Compressed GPU lease must be released on its creating Unity thread");Entry e;if(!resident.TryGetValue(bank,out e))return;if(e.Refs<=0)throw new TextureContractException("Compressed GPU lease underflow");e.Refs--;Touch(e);if(disposed&&e.Refs==0){resident.Remove(bank);residentBytes-=e.Bytes;TextureArrayUpload.Destroy(e.Texture);}}
        public void Dispose(){if(disposed)return;RequireOpen();disposed=true;var remove=new List<int>();foreach(var p in resident)if(p.Value.Refs==0)remove.Add(p.Key);foreach(var bank in remove){var e=resident[bank];resident.Remove(bank);residentBytes-=e.Bytes;TextureArrayUpload.Destroy(e.Texture);}}
        public sealed class Lease:IDisposable{private CompressedTextureArrayResidency owner;private readonly int bank;public Texture2DArray Texture{get;private set;}internal Lease(CompressedTextureArrayResidency owner,int bank,Texture2DArray texture){this.owner=owner;this.bank=bank;Texture=texture;}public void Dispose(){var o=owner;if(o==null)return;owner=null;Texture=null;o.Release(bank);}}
        public sealed class SpriteLease:IDisposable{private Lease lease;public TextureSprite Sprite{get;private set;}public Texture2DArray Texture{get{if(lease==null)throw new ObjectDisposedException(nameof(SpriteLease));return lease.Texture;}}internal SpriteLease(Lease lease,TextureSprite sprite){this.lease=lease;Sprite=sprite;}public void Dispose(){var l=lease;if(l==null)return;lease=null;l.Dispose();}}
    }
}
