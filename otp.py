#!/usr/bin/env python3
"""Steam's five-character TOTP, using only Python's standard library."""

import base64
import binascii
import hashlib
import hmac
import os
import struct
import sys
import time


def generate_one_time_code(shared_secret, timestamp=None):
    try:
        key = base64.b64decode(shared_secret, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ValueError("STEAM_SHARED_SECRET must be valid base64") from exc
    if len(key) != 20:
        raise ValueError("STEAM_SHARED_SECRET must decode to 20 bytes")
    counter = int(time.time() if timestamp is None else timestamp) // 30
    digest = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 15
    value = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7fffffff
    alphabet = "23456789BCDFGHJKMNPQRTVWXY"
    code = ""
    for _ in range(5):
        value, index = divmod(value, len(alphabet))
        code += alphabet[index]
    return code


def main():
    secret = os.environ.get("STEAM_SHARED_SECRET", "")
    if not secret:
        raise ValueError("Please set STEAM_SHARED_SECRET")
    # Avoid handing SteamCMD a code about to expire during connection.
    remaining = 30 - time.time() % 30
    if remaining < 5:
        time.sleep(remaining + 0.1)
    print(generate_one_time_code(secret))


if __name__ == "__main__":
    try:
        main()
    except ValueError as exc:
        sys.exit(str(exc))
