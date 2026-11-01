using System;
using System.Collections.Generic;
using System.Globalization;
using System.Text;

namespace ByteFables.Textures.Core
{
    // Deliberately scoped JSON: the texture contracts use integers, not floats.
    // Duplicate keys, invalid UTF-8, nonfinite numbers and unpaired surrogates fail.
    public static class StrictJson
    {
        public const int MaxBytes = 8 * 1024 * 1024;
        public static object Parse(byte[] bytes)
        {
            Checks.Require(bytes != null && bytes.Length > 0 && bytes.Length <= MaxBytes, "JSON byte budget exceeded");
            string text;
            try { text = new UTF8Encoding(false, true).GetString(bytes); }
            catch (DecoderFallbackException) { throw new TextureContractException("Invalid UTF-8 JSON"); }
            return new Parser(text).Read();
        }
        private sealed class Parser
        {
            private readonly string text;
            private int at, nodes;
            internal Parser(string text) { this.text = text; }
            internal object Read()
            {
                var result = Value(0); Space();
                Checks.Require(at == text.Length, "Trailing JSON data");
                return result;
            }
            private void Space() { while (at < text.Length && (text[at] == ' ' || text[at] == '\n' || text[at] == '\r' || text[at] == '\t')) at++; }
            private bool Take(char c) { Space(); if (at < text.Length && text[at] == c) { at++; return true; } return false; }
            private void Need(char c) { Checks.Require(Take(c), "Expected JSON delimiter " + c); }
            private object Value(int depth)
            {
                Checks.Require(depth <= 24 && ++nodes <= 300000, "JSON nesting/node budget exceeded");
                Space(); Checks.Require(at < text.Length, "Truncated JSON");
                char c = text[at];
                if (c == '{')
                {
                    at++; var map = new Dictionary<string, object>(StringComparer.Ordinal);
                    if (Take('}')) return map;
                    do
                    {
                        Space(); var key = String(); Need(':');
                        Checks.Require(!map.ContainsKey(key), "Duplicate JSON member: " + key);
                        map.Add(key, Value(depth + 1));
                        if (Take('}')) return map;
                        Need(',');
                    } while (true);
                }
                if (c == '[')
                {
                    at++; var list = new List<object>();
                    if (Take(']')) return list;
                    do { list.Add(Value(depth + 1)); if (Take(']')) return list; Need(','); } while (true);
                }
                if (c == '"') return String();
                if (c == 't') { Literal("true"); return true; }
                if (c == 'f') { Literal("false"); return false; }
                if (c == 'n') { Literal("null"); return null; }
                int start = at;
                if (c == '-') at++;
                Checks.Require(at < text.Length && text[at] >= '0' && text[at] <= '9', "Invalid JSON value");
                if (text[at] == '0') at++;
                else while (at < text.Length && text[at] >= '0' && text[at] <= '9') at++;
                Checks.Require(at - start <= 20, "JSON integer too large");
                long number;
                Checks.Require(long.TryParse(text.Substring(start, at - start), NumberStyles.AllowLeadingSign,
                    CultureInfo.InvariantCulture, out number), "Invalid JSON integer");
                return number;
            }
            private void Literal(string word)
            {
                Checks.Require(at + word.Length <= text.Length && string.CompareOrdinal(text, at, word, 0, word.Length) == 0,
                    "Invalid JSON literal"); at += word.Length;
            }
            private char HexChar()
            {
                Checks.Require(at + 4 <= text.Length, "Truncated Unicode escape");
                int n = 0;
                for (int i = 0; i < 4; i++)
                {
                    char c = text[at++]; int v = c >= '0' && c <= '9' ? c - '0' : c >= 'a' && c <= 'f' ? c - 'a' + 10 : c >= 'A' && c <= 'F' ? c - 'A' + 10 : -1;
                    Checks.Require(v >= 0, "Invalid Unicode escape"); n = n * 16 + v;
                }
                return (char)n;
            }
            private string String()
            {
                Checks.Require(at < text.Length && text[at++] == '"', "Expected JSON string");
                var output = new StringBuilder(); bool done = false;
                while (at < text.Length)
                {
                    char c = text[at++]; if (c == '"') { done = true; break; }
                    Checks.Require(c >= 32, "Control character in JSON string");
                    if (c == '\\')
                    {
                        Checks.Require(at < text.Length, "Truncated JSON escape");
                        c = text[at++];
                        switch (c)
                        {
                            case '"': case '\\': case '/': break;
                            case 'b': c = '\b'; break; case 'f': c = '\f'; break;
                            case 'n': c = '\n'; break; case 'r': c = '\r'; break; case 't': c = '\t'; break;
                            case 'u': c = HexChar(); break;
                            default: throw new TextureContractException("Invalid JSON escape");
                        }
                    }
                    output.Append(c); Checks.Require(output.Length <= 65536, "JSON string budget exceeded");
                }
                Checks.Require(done, "Unterminated JSON string");
                string result = output.ToString();
                for (int i = 0; i < result.Length; i++)
                {
                    if (char.IsHighSurrogate(result[i]))
                    { Checks.Require(i + 1 < result.Length && char.IsLowSurrogate(result[++i]), "Unpaired surrogate"); }
                    else Checks.Require(!char.IsLowSurrogate(result[i]), "Unpaired surrogate");
                }
                return result;
            }
        }
    }

    internal static class J
    {
        internal static Dictionary<string, object> Obj(object value)
        {
            var result = value as Dictionary<string, object>;
            Checks.Require(result != null, "Expected JSON object"); return result;
        }
        internal static List<object> Arr(object value)
        {
            var result = value as List<object>;
            Checks.Require(result != null, "Expected JSON array"); return result;
        }
        internal static object Get(Dictionary<string, object> map, string key)
        {
            object value; Checks.Require(map.TryGetValue(key, out value), "Missing member: " + key); return value;
        }
        internal static string Str(object value) { Checks.Require(value is string, "Expected string"); return (string)value; }
        internal static int Int(object value, int low, int high)
        {
            Checks.Require(value is long && (long)value >= low && (long)value <= high, "Integer outside contract bounds"); return (int)(long)value;
        }
        internal static void Eq(object value, string expected) { Checks.Require(Str(value) == expected, "Unexpected contract value: " + expected); }
        internal static void Bool(object value, bool expected) { Checks.Require(value is bool && (bool)value == expected, "Unexpected boolean"); }
        internal static string Hash(object value) { string s = Str(value); Checks.Require(Checks.IsHash(s), "Invalid SHA-256"); return s; }
        internal static void Keys(Dictionary<string, object> map, params string[] keys)
        { Checks.Require(map.Count == keys.Length, "Unexpected JSON members"); foreach (var k in keys) Checks.Require(map.ContainsKey(k), "Missing member: " + k); }
    }
}
