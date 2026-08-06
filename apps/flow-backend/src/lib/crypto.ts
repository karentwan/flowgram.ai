/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

/**
 * AES-256-GCM encryption helpers for secrets at rest.
 *
 * The master key is `FLOWGRAM_ENCRYPTION_KEY` (base64, 32 bytes). Ciphertext is
 * returned as a base64 string of `iv(12) || tag(16) || data`, self-describing
 * so callers just store/restore opaque strings.
 */
import { randomBytes, createCipheriv, createDecipheriv } from 'node:crypto';
import { config } from '../config.js';

const KEY_BUFFER = (() => {
  const raw = Buffer.from(config.encryptionKey, 'base64');
  if (raw.length !== 32) {
    throw new Error(
      'FLOWGRAM_ENCRYPTION_KEY must be a base64-encoded 32-byte value. Generate one with:\n' +
        '  node -e "console.log(require(\'crypto\').randomBytes(32).toString(\'base64\'))"'
    );
  }
  return raw;
})();

const ALGO = 'aes-256-gcm';
const IV_LEN = 12;
const TAG_LEN = 16;

/** Marker prefix so we can detect already-encrypted values (idempotent encrypt). */
const PREFIX = 'enc::';

/** Encrypt a UTF-8 string into an opaque base64 payload (with prefix). */
export function encrypt(plaintext: string): string {
  if (!plaintext) return plaintext;
  const iv = randomBytes(IV_LEN);
  const cipher = createCipheriv(ALGO, KEY_BUFFER, iv);
  const data = Buffer.concat([cipher.update(plaintext, 'utf8'), cipher.final()]);
  const tag = cipher.getAuthTag();
  return PREFIX + Buffer.concat([iv, tag, data]).toString('base64');
}

/** Decrypt a payload produced by `encrypt()`. Returns the original UTF-8 string. */
export function decrypt(payload: string): string {
  if (!payload || !payload.startsWith(PREFIX)) return payload;
  const buf = Buffer.from(payload.slice(PREFIX.length), 'base64');
  const iv = buf.subarray(0, IV_LEN);
  const tag = buf.subarray(IV_LEN, IV_LEN + TAG_LEN);
  const data = buf.subarray(IV_LEN + TAG_LEN);
  const decipher = createDecipheriv(ALGO, KEY_BUFFER, iv);
  decipher.setAuthTag(tag);
  return Buffer.concat([decipher.update(data), decipher.final()]).toString('utf8');
}

/** True if the value looks like an encrypted payload. */
export function isEncrypted(value: string): boolean {
  return typeof value === 'string' && value.startsWith(PREFIX);
}
