using System;
using ByteFables.Textures.Core;
using UnityEngine;
using UnityEngine.Rendering;

namespace ByteFables.Textures
{
    public static class CompressedTextureFormatSelector
    {
        public static string[] PreferredForCurrentPlatform()
        {
            switch(Application.platform)
            {
                case RuntimePlatform.Android:
                case RuntimePlatform.IPhonePlayer:
                    return new[]{"astc4x4","etc2rgba8","bc7"};
                default:
                    return new[]{"bc7","astc4x4","etc2rgba8"};
            }
        }
        public static TextureFormat UnityFormat(string id)
        {
            if(id=="bc7")return TextureFormat.BC7;
            if(id=="astc4x4")return TextureFormat.ASTC_4x4;
            if(id=="etc2rgba8")return TextureFormat.ETC2_RGBA8;
            throw new ArgumentException("Unknown compressed format",nameof(id));
        }
        public static bool IsSupported(string id)
        {
            var format=UnityFormat(id);
            return SystemInfo.graphicsDeviceType!=GraphicsDeviceType.Null && SystemInfo.supports2DArrayTextures &&
                SystemInfo.SupportsTextureFormat(format);
        }
        public static string Select(GpuBlockTextureBundleData data,bool allowNoCompressedFormat=false)
        {
            if(data==null)throw new ArgumentNullException(nameof(data));
            foreach(var id in PreferredForCurrentPlatform())
            {
                try{data.FindFormat(id);}catch(TextureContractException){continue;}
                if(IsSupported(id))return id;
            }
            if(allowNoCompressedFormat)return null;
            throw new NotSupportedException("No ByteFables GPU block format is supported; use the explicit RGBA8 resolved fallback instead");
        }
    }

    public static class CompressedTextureArrayUpload
    {
        /// <summary>
        /// Upload raw 4x4 GPU blocks exactly as produced by Khronos. No block flipping is attempted.
        /// Real-device qualification must prove orientation for the target graphics API before production use.
        /// </summary>
        public static Texture2DArray Create(GpuBlockTextureBundleData data,string formatId,int bankIndex,
            FilterMode filter=FilterMode.Trilinear,bool keepReadable=false)
        {
            if(data==null)throw new ArgumentNullException(nameof(data));
            if(filter!=FilterMode.Point&&filter!=FilterMode.Trilinear)throw new ArgumentException("Use Point or Trilinear filtering",nameof(filter));
            var format=data.FindFormat(formatId);if(bankIndex<0||bankIndex>=format.Banks.Count)throw new ArgumentOutOfRangeException(nameof(bankIndex));
            if(!CompressedTextureFormatSelector.IsSupported(formatId))throw new NotSupportedException("Requested GPU block format is not supported on this device");
            var bank=format.Banks[bankIndex];Texture2DArray texture=null;
            try
            {
                texture=new Texture2DArray(data.NativeSize,data.NativeSize,bank.Layers,CompressedTextureFormatSelector.UnityFormat(formatId),
                    bank.Levels.Count,true,true);
                texture.name="ByteFables "+formatId+" bank "+bankIndex;texture.wrapMode=TextureWrapMode.Clamp;texture.filterMode=filter;texture.anisoLevel=0;
                if(texture.mipmapCount!=bank.Levels.Count)throw new TextureContractException("Compressed Unity mip allocation differs from source");
                for(int mip=0;mip<bank.Levels.Count;mip++)
                {
                    var level=data.LoadLevel(formatId,bankIndex,mip);int per=data.PerLayerBytes(formatId,mip);
                    if(level.Length!=per*bank.Layers)throw new TextureContractException("Compressed level byte count changed");
                    for(int layer=0;layer<bank.Layers;layer++)texture.SetPixelData<byte>(level,mip,layer,layer*per);
                }
                texture.Apply(updateMipmaps:false,makeNoLongerReadable:!keepReadable);return texture;
            }
            catch{TextureArrayUpload.Destroy(texture);throw;}
        }
    }
}
