/** SHA-256 through Web Crypto: supported in modern browsers and Node >=20. */
export async function sha256(data: Uint8Array): Promise<Uint8Array> {
  if (!globalThis.crypto?.subtle) {
    throw new Error('Secure Web Crypto SHA-256 implementation unavailable');
  }
  // new ArrayBuffer guarantees a non-shared buffer accepted by WebCrypto.
  const copy = Uint8Array.from(data);
  const digest = await globalThis.crypto.subtle.digest('SHA-256', copy);
  return new Uint8Array(digest);
}
