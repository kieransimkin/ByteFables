using System;
using System.IO;

namespace ByteFables.Textures.Core
{
    /// <summary>Bounded local-file adapter. No network requests and no arbitrary manifest paths.</summary>
    public static class TextureBundleDirectory
    {
        public static byte[] ReadBounded(string path, int maxBytes)
        {
            Checks.Require(maxBytes > 0 && maxBytes <= Ktx2ArrayData.MaxContainerBytes, "Invalid file budget");
            string full = Path.GetFullPath(path);
            string cursor = full;
            while (!string.IsNullOrEmpty(cursor))
            {
                Checks.Require((File.GetAttributes(cursor) & FileAttributes.ReparsePoint) == 0, "Symlink/reparse paths are not accepted");
                cursor = Path.GetDirectoryName(cursor);
            }
            using (var stream = new FileStream(full, FileMode.Open, FileAccess.Read, FileShare.Read))
            {
                Checks.Require(stream.Length > 0 && stream.Length <= maxBytes, "File exceeds byte budget");
                var bytes = new byte[(int)stream.Length]; int done = 0;
                while (done < bytes.Length)
                { int n = stream.Read(bytes, done, bytes.Length - done); Checks.Require(n > 0, "File changed/truncated while reading"); done += n; }
                Checks.Require(stream.ReadByte() == -1, "File grew while reading"); return bytes;
            }
        }
        /// <summary>Open a staged .bftextures descriptor whose transport checksum is pinned.</summary>
        public static TextureBundleData LoadDescriptor(string descriptorPath, int maxPayloadBytes = TextureBundleData.DefaultPayloadBudget, Action<string> beforeRead = null)
        {
            Checks.Require(Path.GetExtension(descriptorPath) == ".bftextures", "Expected .bftextures descriptor");
            string full = Path.GetFullPath(descriptorPath), root = Path.GetDirectoryName(full);
            Checks.Require(!File.Exists(Path.Combine(root, "failure.json")), "Staging directory carries a failure marker");
            var descriptor = J.Obj(StrictJson.Parse(ReadBounded(full, 4096)));
            J.Keys(descriptor, "schema", "publicOnly", "manifestFile", "manifestSha256");
            J.Eq(J.Get(descriptor, "schema"), "bytefables.unity-texture-import.v1"); J.Bool(J.Get(descriptor, "publicOnly"), true);
            J.Eq(J.Get(descriptor, "manifestFile"), "transport.json");
            var bytes = ReadBounded(Path.Combine(root, "transport.json"), StrictJson.MaxBytes);
            return TextureBundleData.Load(bytes, (name, limit) =>
            {
                // The core reader supplies only source-manifest.json and canonical bank names.
                Checks.Require(name == "source-manifest.json" ||
                    (name.Length == 19 && name.StartsWith("banks/bank-", StringComparison.Ordinal) && name.EndsWith(".ktx2", StringComparison.Ordinal)), "Invalid local bundle path");
                if (beforeRead != null) beforeRead(name);
                return ReadBounded(Path.Combine(root, name.Replace('/', Path.DirectorySeparatorChar)), limit);
            }, J.Hash(J.Get(descriptor, "manifestSha256")), maxPayloadBytes);
        }
    }
}
