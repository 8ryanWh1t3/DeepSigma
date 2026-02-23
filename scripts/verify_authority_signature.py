#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import hmac
import os
import tempfile
from pathlib import Path


def fail(msg: str) -> int:
    print(f"FAIL: {msg}")
    return 1


def verify(message: str, signature_hex: str, key: str) -> bool:
    digest = hmac.new(key.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, signature_hex)


def run_self_check() -> int:
    message = "rotate:key-1:v2"
    key = "build-88-self-check-key"
    signature = hmac.new(key.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).hexdigest()
    if not verify(message, signature, key):
        return fail("self-check signature did not verify")

    with tempfile.TemporaryDirectory() as tmp:
        msg_path = Path(tmp) / "message.txt"
        sig_path = Path(tmp) / "signature.txt"
        msg_path.write_text(message, encoding="utf-8")
        sig_path.write_text(signature, encoding="utf-8")
        if not verify(msg_path.read_text(encoding="utf-8"), sig_path.read_text(encoding="utf-8").strip(), key):
            return fail("file-based self-check signature did not verify")

    print("PASS: authority signature self-check passed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify authority signature")
    parser.add_argument("--message", help="message string", default=None)
    parser.add_argument("--message-file", default=None)
    parser.add_argument("--signature", help="hex signature", default=None)
    parser.add_argument("--signature-file", default=None)
    parser.add_argument("--key-env", default="DEEPSIGMA_SIGNING_KEY")
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args()

    if args.self_check:
        return run_self_check()

    key = os.environ.get(args.key_env, "")
    if not key:
        return fail(f"missing signing key env var: {args.key_env}")

    message = args.message
    if args.message_file:
        message = Path(args.message_file).read_text(encoding="utf-8")
    signature = args.signature
    if args.signature_file:
        signature = Path(args.signature_file).read_text(encoding="utf-8").strip()

    if not message or not signature:
        return fail("provide --message/--message-file and --signature/--signature-file")

    if not verify(message, signature, key):
        return fail("signature verification failed")

    print("PASS: authority signature verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
