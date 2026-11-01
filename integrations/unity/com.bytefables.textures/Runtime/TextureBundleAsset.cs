using System;
using ByteFables.Textures.Core;
using UnityEngine;

namespace ByteFables.Textures
{
    [Serializable]
    public struct SpriteBinding
    {
        [SerializeField] private string spriteKey, digestHex, family, palette;
        [SerializeField] private int complexity, bankIndex, layerIndex;
        public string SpriteKey { get { return spriteKey; } }
        public string DigestHex { get { return digestHex; } }
        public string Family { get { return family; } }
        public string Palette { get { return palette; } }
        public int Complexity { get { return complexity; } }
        public int BankIndex { get { return bankIndex; } }
        public int LayerIndex { get { return layerIndex; } }
        public SpriteBinding(TextureSprite source)
        {
            spriteKey = source.SpriteKey; digestHex = source.DigestHex; family = source.Family; palette = source.Palette;
            complexity = source.Complexity; bankIndex = source.BankIndex; layerIndex = source.LayerIndex;
        }
    }
    public sealed class TextureBundleAsset : ScriptableObject
    {
        [SerializeField] private string manifestSha256;
        [SerializeField] private int nativeSize;
        [SerializeField] private Texture2DArray[] banks;
        [SerializeField] private SpriteBinding[] sprites;
        public string ManifestSha256 { get { return manifestSha256; } }
        public int NativeSize { get { return nativeSize; } }
        public int SpriteCount { get { return sprites == null ? 0 : sprites.Length; } }
        public int BankCount { get { return banks == null ? 0 : banks.Length; } }
        public Texture2DArray GetBank(int index) { return banks[index]; }
        public SpriteBinding GetSprite(int index) { return sprites[index]; }
        public SpriteBinding Find(string fullSpriteKey)
        {
            foreach (var sprite in sprites) if (sprite.SpriteKey == fullSpriteKey) return sprite;
            throw new ArgumentException("Full sprite key is not present", nameof(fullSpriteKey));
        }
        public void Initialize(TextureBundleData data, Texture2DArray[] ownedSubAssets)
        {
            if (data == null || ownedSubAssets == null || ownedSubAssets.Length != data.Banks.Count)
                throw new ArgumentException("Texture-bank inventory mismatch");
            manifestSha256 = data.ManifestSha256; nativeSize = data.NativeSize;
            banks = (Texture2DArray[])ownedSubAssets.Clone(); sprites = new SpriteBinding[data.Sprites.Count];
            for (int i = 0; i < sprites.Length; i++) sprites[i] = new SpriteBinding(data.Sprites[i]);
        }
    }
}
