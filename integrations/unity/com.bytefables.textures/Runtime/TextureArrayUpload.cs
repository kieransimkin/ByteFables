using System;
using ByteFables.Textures.Core;
using UnityEngine;
using UnityEngine.Rendering;

namespace ByteFables.Textures
{
    public static class TextureArrayUpload
    {
        /// <summary>Call on Unity's main thread. The returned Texture2DArray belongs to the caller.</summary>
        public static Texture2DArray Create(Ktx2ArrayData data, FilterMode filter = FilterMode.Trilinear,
            bool keepReadable = false, bool requireGpu = true)
        {
            if (data == null) throw new ArgumentNullException(nameof(data));
            if (filter != FilterMode.Point && filter != FilterMode.Trilinear)
                throw new ArgumentException("Use Point or Trilinear filtering", nameof(filter));
            if (requireGpu && (SystemInfo.graphicsDeviceType == GraphicsDeviceType.Null || !SystemInfo.supports2DArrayTextures ||
                !SystemInfo.SupportsTextureFormat(TextureFormat.RGBA32) || SystemInfo.maxTextureSize < data.Size ||
                SystemInfo.maxTextureArraySlices < data.Layers))
                throw new NotSupportedException("This graphics device cannot hold the required RGBA8 texture array");
            Texture2DArray texture = null;
            try
            {
                // linear:true means NO implicit sRGB decode. These are stored sample values,
                // not a claim that the artwork was filtered in physically linear light.
                texture = new Texture2DArray(data.Size, data.Size, data.Layers, TextureFormat.RGBA32, true, true);
                texture.name = "ByteFables " + data.FileSha256;
                texture.wrapMode = TextureWrapMode.Clamp; texture.filterMode = filter; texture.anisoLevel = 0;
                if (texture.mipmapCount != data.LevelCount) throw new TextureContractException("Unity mip allocation differs from source");
                for (int layer = 0; layer < data.Layers; layer++)
                    for (int mip = 0; mip < data.LevelCount; mip++)
                        texture.SetPixelData<byte>(data.CopyLayer(mip, layer, bottomUp: true), mip, layer);
                // Never call Apply() with its default updateMipmaps:true: it would discard the verified chain.
                texture.Apply(updateMipmaps: false, makeNoLongerReadable: !keepReadable);
                return texture;
            }
            catch { Destroy(texture); throw; }
        }
        public static void Destroy(UnityEngine.Object value)
        {
            if (value == null) return;
            if (Application.isPlaying) UnityEngine.Object.Destroy(value);
            else UnityEngine.Object.DestroyImmediate(value);
        }
    }

    /// <summary>Owns runtime-created arrays. Dispose when their UI/scene is removed, on the main thread.</summary>
    public sealed class UploadedTextureBundle : IDisposable
    {
        private Texture2DArray[] arrays;
        public TextureBundleData Source { get; private set; }
        public UploadedTextureBundle(TextureBundleData data, bool keepReadable = false)
        {
            Source = data ?? throw new ArgumentNullException(nameof(data));
            arrays = new Texture2DArray[data.Banks.Count];
            try { for (int i = 0; i < arrays.Length; i++) arrays[i] = TextureArrayUpload.Create(data.Banks[i], keepReadable: keepReadable); }
            catch { Dispose(); throw; }
        }
        public Texture2DArray GetBank(int index)
        {
            if (arrays == null) throw new ObjectDisposedException(nameof(UploadedTextureBundle));
            if (index < 0 || index >= arrays.Length) throw new ArgumentOutOfRangeException(nameof(index));
            return arrays[index];
        }
        public void Dispose()
        {
            if (arrays == null) return;
            foreach (var texture in arrays) TextureArrayUpload.Destroy(texture);
            arrays = null;
        }
    }
}
