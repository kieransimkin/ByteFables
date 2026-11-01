using System;
using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;

namespace ByteFables.Textures.Core
{
    public sealed class TextureCpuResidency : IDisposable
    {
        private sealed class Entry { public Ktx2ArrayData Data; public int Bytes, References; public long Tick; }
        private readonly object gate=new object();
        private readonly LazyTextureBundleData source;
        private readonly Dictionary<int,Entry> resident=new Dictionary<int,Entry>();
        private readonly Dictionary<int,Task<Ktx2ArrayData>> loading=new Dictionary<int,Task<Ktx2ArrayData>>();
        private long clock; private int budgetBytes,residentBytes,peakResidentBytes,loads,hits,evictions; private bool disposed;
        public LazyTextureBundleData Source { get { return source; } }
        public int BudgetBytes { get { lock(gate)return budgetBytes; } }
        public int ResidentBytes { get { lock(gate)return residentBytes; } }
        public int PeakResidentBytes { get { lock(gate)return peakResidentBytes; } }
        public int ResidentBanks { get { lock(gate)return resident.Count; } }
        public int InFlight { get { lock(gate)return loading.Count; } }
        public int Loads { get { lock(gate)return loads; } }
        public int Hits { get { lock(gate)return hits; } }
        public int Evictions { get { lock(gate)return evictions; } }

        public TextureCpuResidency(LazyTextureBundleData source,int budgetBytes)
        { this.source=source??throw new ArgumentNullException(nameof(source));SetBudgetInitial(budgetBytes); }
        private void SetBudgetInitial(int value){if(value<1||value>LazyTextureBundleData.MaximumPayloadBudget)throw new ArgumentOutOfRangeException(nameof(value));budgetBytes=value;}
        private void RequireOpen(){if(disposed)throw new ObjectDisposedException(nameof(TextureCpuResidency));}
        private void Touch(Entry entry){entry.Tick=++clock;}
        private int PinnedBytes(){int total=0;foreach(var e in resident.Values)if(e.References>0)total=checked(total+e.Bytes);return total;}
        private bool EvictOne()
        {
            int victim=-1;long tick=long.MaxValue;
            foreach(var pair in resident)if(pair.Value.References==0&&pair.Value.Tick<tick){victim=pair.Key;tick=pair.Value.Tick;}
            if(victim<0)return false;var entry=resident[victim];resident.Remove(victim);residentBytes-=entry.Bytes;evictions++;return true;
        }
        private void MakeRoom(int bytes)
        {
            if(bytes>budgetBytes)throw new TextureContractException("CPU bank exceeds residency budget");
            while(residentBytes+bytes>budgetBytes)if(!EvictOne())throw new TextureContractException("CPU residency budget is pinned by active leases");
        }
        private TextureCpuBankLease PinExisting(int bank)
        {
            Entry entry;if(!resident.TryGetValue(bank,out entry))return null;entry.References++;Touch(entry);hits++;return new TextureCpuBankLease(this,bank,entry.Data);
        }
        public TextureCpuBankLease AcquireBank(int bankIndex)
        { return AcquireBankAsync(bankIndex,CancellationToken.None).GetAwaiter().GetResult(); }

        public async Task<TextureCpuBankLease> AcquireBankAsync(int bankIndex,CancellationToken cancellationToken)
        {
            cancellationToken.ThrowIfCancellationRequested();
            if(bankIndex<0||bankIndex>=source.Banks.Count)throw new ArgumentOutOfRangeException(nameof(bankIndex));
            Task<Ktx2ArrayData> task;
            lock(gate)
            {
                RequireOpen();var existing=PinExisting(bankIndex);if(existing!=null)return existing;
                if(!loading.TryGetValue(bankIndex,out task))
                { task=Task.Run(()=>source.LoadBank(bankIndex));loading.Add(bankIndex,task); }
            }
            Ktx2ArrayData parsed;
            try{parsed=await WaitWithCancellation(task,cancellationToken).ConfigureAwait(false);}
            catch
            {
                lock(gate){Task<Ktx2ArrayData> current;if(loading.TryGetValue(bankIndex,out current)&&object.ReferenceEquals(current,task)&&task.IsCompleted)loading.Remove(bankIndex);}
                throw;
            }
            lock(gate)
            {
                RequireOpen();Task<Ktx2ArrayData> current;if(loading.TryGetValue(bankIndex,out current)&&object.ReferenceEquals(current,task))loading.Remove(bankIndex);
                var existing=PinExisting(bankIndex);if(existing!=null)return existing;
                int bytes=source.Banks[bankIndex].ByteLength;MakeRoom(bytes);
                var entry=new Entry{Data=parsed,Bytes=bytes,References=1};Touch(entry);resident.Add(bankIndex,entry);residentBytes+=bytes;loads++;if(residentBytes>peakResidentBytes)peakResidentBytes=residentBytes;
                return new TextureCpuBankLease(this,bankIndex,parsed);
            }
        }
        private static async Task<T> WaitWithCancellation<T>(Task<T> task,CancellationToken token)
        {
            if(!token.CanBeCanceled)return await task.ConfigureAwait(false);
            var signal=new TaskCompletionSource<bool>();using(token.Register(()=>signal.TrySetResult(true)))
            { if(task!=await Task.WhenAny(task,signal.Task).ConfigureAwait(false))throw new OperationCanceledException(token); }
            return await task.ConfigureAwait(false);
        }
        internal void Release(int bankIndex)
        {
            lock(gate)
            {
                Entry entry;if(!resident.TryGetValue(bankIndex,out entry))return;
                if(entry.References<=0)throw new TextureContractException("CPU residency lease underflow");entry.References--;Touch(entry);
                if(disposed&&entry.References==0){resident.Remove(bankIndex);residentBytes-=entry.Bytes;}
            }
        }
        public async Task PrefetchAsync(IEnumerable<int> bankIndices,CancellationToken cancellationToken)
        {
            if(bankIndices==null)throw new ArgumentNullException(nameof(bankIndices));
            foreach(var bank in bankIndices){cancellationToken.ThrowIfCancellationRequested();using(var lease=await AcquireBankAsync(bank,cancellationToken).ConfigureAwait(false)){} }
        }
        public void SetBudget(int value)
        {
            if(value<1||value>LazyTextureBundleData.MaximumPayloadBudget)throw new ArgumentOutOfRangeException(nameof(value));
            lock(gate)
            {
                RequireOpen();if(PinnedBytes()>value)throw new TextureContractException("CPU residency budget is pinned by active leases");
                while(residentBytes>value)if(!EvictOne())throw new TextureContractException("CPU residency cannot satisfy requested budget");
                budgetBytes=value;
            }
        }
        public void Dispose()
        {
            lock(gate)
            {
                if(disposed)return;disposed=true;var remove=new List<int>();foreach(var pair in resident)if(pair.Value.References==0)remove.Add(pair.Key);
                foreach(var bank in remove){residentBytes-=resident[bank].Bytes;resident.Remove(bank);}loading.Clear();
            }
        }
        public sealed class TextureCpuBankLease:IDisposable
        {
            private TextureCpuResidency owner;private readonly int bankIndex;public Ktx2ArrayData Data{get;private set;}
            internal TextureCpuBankLease(TextureCpuResidency owner,int bank,Ktx2ArrayData data){this.owner=owner;bankIndex=bank;Data=data;}
            public void Dispose(){var current=owner;if(current==null)return;owner=null;Data=null;current.Release(bankIndex);}
        }
    }
}
