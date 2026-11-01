using System;
using System.Collections.Generic;
using System.IO;
using ByteFables.Textures.Core;
using UnityEditor.AssetImporters;
using UnityEngine;

namespace ByteFables.Textures.Editor
{
    // Only our descriptor extension is registered. Other KTX2 importers are not intercepted.
    [ScriptedImporter(1, "bftextures")]
    public sealed class TextureBundleImporter : ScriptedImporter
    {
        [SerializeField] private bool keepReadable = false;
        [SerializeField, Range(1, 128)] private int payloadBudgetMiB = 64;
        public override void OnImportAsset(AssetImportContext ctx)
        {
            string root = Path.GetDirectoryName(ctx.assetPath).Replace('\\', '/');
            ctx.DependsOnSourceAsset(root + "/transport.json");
            ctx.DependsOnSourceAsset(root + "/source-manifest.json");
            var created = new List<UnityEngine.Object>();
            try
            {
                var data = TextureBundleDirectory.LoadDescriptor(ctx.assetPath, payloadBudgetMiB * 1024 * 1024,
                    name => ctx.DependsOnSourceAsset(root + "/" + name));
                var banks = new Texture2DArray[data.Banks.Count];
                for (int i = 0; i < banks.Length; i++)
                {
                    ctx.DependsOnSourceAsset(root + "/banks/bank-" + i.ToString("D3") + ".ktx2");
                    // Asset import workers may have no graphics device. GPU qualification is
                    // a separate, mandatory test; a successful import alone is not a GPU pass.
                    banks[i] = TextureArrayUpload.Create(data.Banks[i], keepReadable: keepReadable, requireGpu: false);
                    banks[i].name = "bank-" + i.ToString("D3"); created.Add(banks[i]);
                }
                var asset = ScriptableObject.CreateInstance<TextureBundleAsset>(); created.Add(asset);
                asset.name = Path.GetFileNameWithoutExtension(ctx.assetPath); asset.Initialize(data, banks);
                ctx.AddObjectToAsset("bundle", asset);
                for (int i = 0; i < banks.Length; i++) ctx.AddObjectToAsset("bank-" + i.ToString("D3"), banks[i]);
                ctx.SetMainObject(asset);
            }
            catch (Exception e)
            {
                foreach (var item in created) TextureArrayUpload.Destroy(item);
                ctx.LogImportError("ByteFables texture import rejected: " + e.Message);
                throw;
            }
        }
    }
}
