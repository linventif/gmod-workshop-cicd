#!/usr/bin/env python3
"""Steam's five-character TOTP, using only Python's standard library."""

import base64
import binascii
import hashlib
import hmac
import json
import os
import struct
import sys
import time
from urllib.request import Request, urlopen


STEAM_TIME_URL = "https://api.steampowered.com/ITwoFactorService/QueryTime/v1/"
MIN_CODE_VALIDITY = 15


def decode_secret(shared_secret):
    try:
        key = base64.b64decode(shared_secret, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ValueError("STEAM_SHARED_SECRET must be valid base64") from exc
    if len(key) != 20:
        raise ValueError("STEAM_SHARED_SECRET must decode to 20 bytes")
    return key


def generate_one_time_code(shared_secret, timestamp=None):
    key = decode_secret(shared_secret)
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


def steam_clock():
    """Anchor Steam's public server time to a monotonic clock, without credentials."""
    started = time.monotonic()
    local_started = time.time()
    request = Request(STEAM_TIME_URL, data=b"", method="POST", headers={
        "Accept": "application/json",
        "Cache-Control": "no-cache",
    })
    try:
        with urlopen(request, timeout=5) as response:
            payload = json.loads(response.read(65536))
        server_time = int(payload["response"]["server_time"])
        if server_time <= 0:
            raise ValueError("Invalid server time")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise ValueError("Unable to query Steam time; automatic Steam Guard generation stopped") from exc
    finished = time.monotonic()
    # QueryTime has second precision; account for half the round-trip latency.
    server_at_finish = server_time + (finished - started) / 2
    offset = server_at_finish - (local_started + finished - started)
    return server_at_finish, finished, offset


def generate_fresh_code(secret):
    # Reject malformed secrets before making any network request.
    decode_secret(secret)
    server_time, anchor, offset = steam_clock()

    def now():
        return server_time + time.monotonic() - anchor

    remaining = 30 - now() % 30
    if remaining < MIN_CODE_VALIDITY:
        time.sleep(remaining + 0.1)
    timestamp = now()
    remaining = 30 - timestamp % 30
    print(f"Steam Guard timing: Steam clock offset={offset:+.1f}s; "
          f"code valid for {remaining:.1f}s", file=sys.stderr)
    return generate_one_time_code(secret, timestamp)


def main():
    secret = os.environ.get("STEAM_SHARED_SECRET", "")
    if not secret:
        raise ValueError("Please set STEAM_SHARED_SECRET")
    print(generate_fresh_code(secret))


if __name__ == "__main__":
    try:
        main()
    except ValueError as exc:
        sys.exit(str(exc))
