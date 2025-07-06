#!/usr/bin/env python3
import os
from steampy.guard import generate_one_time_code

shared = os.environ.get("STEAM_SHARED_SECRET")
if not shared:
    raise RuntimeError("Please set STEAM_SHARED_SECRET")

print(generate_one_time_code(shared))
