using System;
using System.IO;
using System.Security.Cryptography;
using System.Text;

namespace ByteFables.Textures.Core
{
    public sealed class TextureContractException : FormatException
    {
        public TextureContractException(string message) : base(message) { }
    }

    internal static class Checks
    {
        internal static void Require(bool value, string message)
        {
            if (!value) throw new TextureContractException(message);
        }
        internal static bool IsHash(string value)
        {
            if (value == null || value.Length != 64) return false;
            foreach (char c in value) if (!((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f'))) return false;
            return true;
        }
        internal static string Hash(byte[] bytes, int start, int length)
        {
            using (var sha = SHA256.Create())
            {
                var digest = sha.ComputeHash(bytes, start, length);
                var text = new StringBuilder(64);
                foreach (byte b in digest) text.Append(b.ToString("x2"));
                return text.ToString();
            }
        }
    }

    public static class TextureHashes
    {
        public static string Sha256(byte[] bytes)
        {
            if (bytes == null) throw new ArgumentNullException(nameof(bytes));
            return Checks.Hash(bytes, 0, bytes.Length);
        }
    }
}
