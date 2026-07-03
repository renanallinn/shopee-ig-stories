import { createCipheriv, createDecipheriv, randomBytes } from "crypto";

// AES-256-GCM, format: base64(iv[12] || ciphertext || authTag[16]).
// This layout is intentionally compatible with Python's
// cryptography.hazmat.primitives.ciphers.aead.AESGCM (which appends the tag
// to the ciphertext), so the worker can decrypt what this app encrypts.
function getKey(): Buffer {
  const b64 = process.env.CREDENTIALS_ENCRYPTION_KEY;
  if (!b64) {
    throw new Error("CREDENTIALS_ENCRYPTION_KEY is not set");
  }
  const key = Buffer.from(b64, "base64");
  if (key.length !== 32) {
    throw new Error("CREDENTIALS_ENCRYPTION_KEY must decode to 32 bytes");
  }
  return key;
}

export function encryptSecret(plaintext: string): string {
  const key = getKey();
  const iv = randomBytes(12);
  const cipher = createCipheriv("aes-256-gcm", key, iv);
  const ciphertext = Buffer.concat([
    cipher.update(plaintext, "utf8"),
    cipher.final(),
  ]);
  const tag = cipher.getAuthTag();
  return Buffer.concat([iv, ciphertext, tag]).toString("base64");
}

export function decryptSecret(encoded: string): string {
  const key = getKey();
  const raw = Buffer.from(encoded, "base64");
  const iv = raw.subarray(0, 12);
  const tag = raw.subarray(raw.length - 16);
  const ciphertext = raw.subarray(12, raw.length - 16);
  const decipher = createDecipheriv("aes-256-gcm", key, iv);
  decipher.setAuthTag(tag);
  return Buffer.concat([
    decipher.update(ciphertext),
    decipher.final(),
  ]).toString("utf8");
}
