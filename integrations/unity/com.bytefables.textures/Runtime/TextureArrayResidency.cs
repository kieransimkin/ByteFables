using System;
using System.Collections;
using System.Collections.Generic;
using ByteFables.Textures.Core;
using UnityEngine;

namespace ByteFables.Textures
{
    [Serializable]
    public struct TextureResidencyStats
    {
        public long budgetBytes, residentBytes, peakResidentBytes;
        public int residentBanks, pinnedBanks, loads, hits, evictions;
    }

    /// <summary>
    /// Bounded GPU residency over an already verified TextureBundleData snapshot.
    /// Call on Unity's main thread. This class does not perform network I/O or decode Basis.
    /// </summary>
    public sealed class TextureArrayResidency : IDisposable
    {
        private sealed class Entry
        {
            public Texture2DArray Texture;
            public long Bytes, Last;
            public int References;
        }
        private readonly TextureBundleData source;
        private readonly FilterMode filter;
        private readonly Dictionary<int, Entry> entries = new Dictionary<int, Entry>();
        private long budget, resident, peak, clock;
        private int loads, hits, evictions;
        private bool disposed;

        public TextureArrayResidency(TextureBundleData source, long budgetBytes, FilterMode filter = FilterMode.Trilinear)
        {
            this.source = source ?? throw new ArgumentNullException(nameof(source));
            if (filter != FilterMode.Point && filter != FilterMode.Trilinear)
                throw new ArgumentException("Use Point or Trilinear filtering", nameof(filter));
            this.filter = filter;
            if (budgetBytes < 1 || budgetBytes > TextureBundleData.MaximumPayloadBudget)
                throw new ArgumentOutOfRangeException(nameof(budgetBytes));
            budget = budgetBytes;
        }

        private void RequireOpen()
        { if (disposed) throw new ObjectDisposedException(nameof(TextureArrayResidency)); }

        private long BankBytes(int bankIndex)
        {
            if (bankIndex < 0 || bankIndex >= source.Banks.Count) throw new ArgumentOutOfRangeException(nameof(bankIndex));
            var bank = source.Banks[bankIndex]; long total = 0;
            for (int mip = 0; mip < bank.LevelCount; mip++)
            { long side = bank.LevelSize(mip); total = checked(total + side * side * bank.Layers * 4L); }
            return total;
        }

        private void Touch(Entry entry) { entry.Last = ++clock; }

        private void EvictFor(long required, int exclude = -1)
        {
            if (required < 0 || required > budget) throw new InvalidOperationException("A single texture bank exceeds the residency budget");
            while (resident + required > budget)
            {
                int victimIndex = -1; Entry victim = null;
                foreach (var pair in entries)
                {
                    if (pair.Key == exclude || pair.Value.References != 0) continue;
                    if (victim == null || pair.Value.Last < victim.Last) { victimIndex = pair.Key; victim = pair.Value; }
                }
                if (victim == null) throw new InvalidOperationException("Texture residency budget is pinned by active leases");
                entries.Remove(victimIndex); resident -= victim.Bytes; evictions++;
                TextureArrayUpload.Destroy(victim.Texture); victim.Texture = null;
            }
        }

        public TextureBankLease AcquireBank(int bankIndex)
        {
            RequireOpen(); Entry entry;
            if (entries.TryGetValue(bankIndex, out entry)) hits++;
            else
            {
                long bytes = BankBytes(bankIndex); EvictFor(bytes, bankIndex);
                var texture = TextureArrayUpload.Create(source.Banks[bankIndex], filter, keepReadable: false, requireGpu: true);
                entry = new Entry { Texture = texture, Bytes = bytes, References = 0 };
                entries.Add(bankIndex, entry); resident += bytes; peak = Math.Max(peak, resident); loads++;
            }
            entry.References++; Touch(entry); return new TextureBankLease(this, bankIndex, entry.Texture);
        }

        public TextureSpriteLease AcquireSprite(string fullSpriteKey)
        {
            RequireOpen(); var sprite = source.Find(fullSpriteKey); var bank = AcquireBank(sprite.BankIndex);
            return new TextureSpriteLease(bank, sprite);
        }

        /// <summary>Cooperatively prefetch one bank per frame. Banks remain unpinned and may be evicted later.</summary>
        public IEnumerator Prefetch(IEnumerable<int> bankIndices)
        {
            RequireOpen(); if (bankIndices == null) throw new ArgumentNullException(nameof(bankIndices));
            foreach (int bankIndex in bankIndices)
            {
                using (var lease = AcquireBank(bankIndex)) { }
                yield return null;
            }
        }

        public void SetBudget(long budgetBytes)
        {
            RequireOpen(); if (budgetBytes < 1 || budgetBytes > TextureBundleData.MaximumPayloadBudget)
                throw new ArgumentOutOfRangeException(nameof(budgetBytes));
            long pinned = 0;
            foreach (var entry in entries.Values) if (entry.References > 0) pinned = checked(pinned + entry.Bytes);
            if (pinned > budgetBytes) throw new InvalidOperationException("Texture residency budget is pinned by active leases");
            budget = budgetBytes; EvictFor(0);
        }

        internal void Release(int bankIndex)
        {
            Entry entry; if (!entries.TryGetValue(bankIndex, out entry)) return;
            if (entry.References <= 0) throw new TextureContractException("Texture residency lease underflow");
            entry.References--; Touch(entry);
            if (disposed && entry.References == 0)
            {
                entries.Remove(bankIndex); resident -= entry.Bytes; TextureArrayUpload.Destroy(entry.Texture); entry.Texture = null;
            }
        }

        public TextureResidencyStats Stats
        {
            get
            {
                int pinned = 0; foreach (var entry in entries.Values) if (entry.References > 0) pinned++;
                return new TextureResidencyStats { budgetBytes = budget, residentBytes = resident, peakResidentBytes = peak,
                    residentBanks = entries.Count, pinnedBanks = pinned, loads = loads, hits = hits, evictions = evictions };
            }
        }

        public void Dispose()
        {
            if (disposed) return; disposed = true;
            foreach (var pair in new List<KeyValuePair<int,Entry>>(entries))
                if (pair.Value.References == 0)
                { entries.Remove(pair.Key); resident -= pair.Value.Bytes; TextureArrayUpload.Destroy(pair.Value.Texture); pair.Value.Texture = null; }
        }

        public sealed class TextureBankLease : IDisposable
        {
            private TextureArrayResidency owner; private readonly int bankIndex;
            public Texture2DArray Texture { get; private set; }
            internal TextureBankLease(TextureArrayResidency owner, int index, Texture2DArray texture)
            { this.owner = owner; bankIndex = index; Texture = texture; }
            public void Dispose()
            { var current = owner; if (current == null) return; owner = null; Texture = null; current.Release(bankIndex); }
        }

        public sealed class TextureSpriteLease : IDisposable
        {
            private TextureBankLease bank;
            public TextureSprite Sprite { get; private set; }
            public Texture2DArray Texture { get { if (bank == null) throw new ObjectDisposedException(nameof(TextureSpriteLease)); return bank.Texture; } }
            internal TextureSpriteLease(TextureBankLease bank, TextureSprite sprite) { this.bank = bank; Sprite = sprite; }
            public void Dispose() { var current = bank; if (current == null) return; bank = null; current.Dispose(); }
        }
    }
}
