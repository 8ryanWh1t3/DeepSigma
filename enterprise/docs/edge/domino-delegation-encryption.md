# Domino Delegation Encryption — Runbook

## What It Is

A 4-of-7 Shamir threshold encryption ceremony using physical domino tiles as a co-presence proof. Seven participants each contribute a domino tile to form a chain, then receive a keyword (Shamir share). Any four keywords plus a passphrase can lock/unlock sensitive text via AES-256-GCM.

## Public vs Secret

| Category | Examples | Handling |
|---|---|---|
| **Public** | Ceremony JSON, chain fingerprint, domino name, session ID, keyword fingerprints, participant list | Safe to store, share, and archive. The ceremony JSON is the verifiable record. |
| **Secret** | Keywords (7 base64 strings), reconstructed secret, passphrase, plaintext | Never stored. Never transmitted electronically. Distribute keywords in person only. |

## Ceremony Steps

### 1. Run Self-Test
Open the EDGE module in a browser (offline). Click **Run Self-Test**. The tool verifies GF(256) arithmetic, Shamir roundtrip, and Base64 encoding. Must pass before proceeding.

### 2. Chain Ceremony
Seven participants each draw a physical domino tile from a double-six set. Enter tiles in order. The right side of each tile must match the left side of the next (standard domino chaining). The tool validates connectivity and computes a SHA-256 seal.

### 3. Generate Keywords
Click **Generate Keywords**. The tool creates a random 256-bit secret and splits it into 7 Shamir shares (threshold 4). Each keyword card appears with a fingerprint. A 1-hour TTL starts.

### 4. Distribute Keywords
Distribute keywords **one at a time, in person**:
- Press and hold the reveal button to show a keyword
- Hand the device to the participant (or read aloud)
- After copying, click the overwrite button to clear the clipboard
- Each participant records their keyword privately

### 5. Export Ceremony Record
Download or copy the ceremony JSON. This is the public record. It contains the chain, seal, fingerprints, and TTL window — never the keywords or secret.

### 6. Unlock (when needed)
Gather at least 4 of 7 keyword holders. Each pastes their keyword into an unlock slot. Optionally load the ceremony JSON for fingerprint verification. Once 4 valid keywords are entered (within TTL), the secret is reconstructed.

### 7. Encrypt / Decrypt
With the secret reconstructed:
- **Lock**: Enter a strong passphrase + plaintext. The tool derives an AES-256-GCM key via HKDF (secret + passphrase) and encrypts.
- **Unlock**: Enter the same passphrase + ciphertext to decrypt.

## Operational Security Rules

1. **Never export all 7 keywords** from a single device. Distribute one at a time.
2. **Never transmit keywords** via email, chat, text message, or any electronic channel.
3. **Rotate per event.** Each ceremony generates a fresh secret. Do not reuse keywords across events.
4. **Respect TTL.** Keywords expire 1 hour after generation. Plan the ceremony timeline accordingly.
5. **Passphrase strength matters.** Use the built-in generator (10-word diceware or 32-char random). A weak passphrase undermines the encryption even with valid keywords.
6. **Verify before trusting.** Use the Verify tab (or the standalone Verifier tool) to check any ceremony JSON before relying on it.
7. **Air-gapped is best.** Run the tool on a machine with no network connection for maximum assurance.

## Troubleshooting

| Issue | Cause | Fix |
|---|---|---|
| Self-test fails | Browser crypto issue | Try a different browser (Chrome, Firefox, Edge) |
| Chain breaks at tile N | Right side of tile N does not match left side of tile N+1 | Flip the tile or swap with an adjacent participant |
| TTL expired | More than 1 hour since keyword generation | Start a new ceremony — keywords cannot be reused after expiry |
| Decryption fails | Wrong keywords or wrong passphrase | Verify you have at least 4 correct keywords and the exact passphrase |
| Keyword fingerprint mismatch | Wrong keyword for this ceremony | Each keyword is bound to its ceremony. Ensure keywords match the loaded ceremony JSON |
| Console shows "EDGE hardening" error | Code attempted a blocked operation | This is expected — the hardening shim prevents network access and other forbidden APIs |
