using System;
using System.IO;

namespace ByteFables.Textures.Core
{
    public static class GpuBlockTextureBundleDirectory
    {
        public static GpuBlockTextureBundleData LoadDescriptor(string descriptorPath,Action<string> beforeBlockRead=null)
        {
            Checks.Require(Path.GetExtension(descriptorPath)==".bfgpu","Expected .bfgpu descriptor");
            string full=Path.GetFullPath(descriptorPath),root=Path.GetDirectoryName(full);
            Checks.Require(!File.Exists(Path.Combine(root,"failure.json")),"GPU block directory carries a failure marker");
            var descriptor=J.Obj(StrictJson.Parse(TextureBundleDirectory.ReadBounded(full,4096)));
            J.Keys(descriptor,"schema","publicOnly","manifestFile","manifestSha256");J.Eq(J.Get(descriptor,"schema"),"bytefables.unity-gpu-blocks.v1");
            J.Bool(J.Get(descriptor,"publicOnly"),true);J.Eq(J.Get(descriptor,"manifestFile"),"manifest.json");string manifestSha=J.Hash(J.Get(descriptor,"manifestSha256"));
            var manifest=TextureBundleDirectory.ReadBounded(Path.Combine(root,"manifest.json"),StrictJson.MaxBytes);
            return GpuBlockTextureBundleData.Load(manifest,(name,limit)=>{
                Checks.Require(name.StartsWith("formats/",StringComparison.Ordinal)&&name.EndsWith(".bin",StringComparison.Ordinal)&&!name.Contains(".."),"Invalid GPU block path");
                if(beforeBlockRead!=null)beforeBlockRead(name);return TextureBundleDirectory.ReadBounded(Path.Combine(root,name.Replace('/',Path.DirectorySeparatorChar)),limit);
            },manifestSha);
        }
    }
}
