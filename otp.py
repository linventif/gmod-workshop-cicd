#!/usr/bin/env python3
import os
import sys
from steampy.guard import generate_one_time_code

def main():
    secret = os.environ.get('STEAM_SHARED_SECRET')
    if not secret:
        print("Error: STEAM_SHARED_SECRET environment variable is not set.", file=sys.stderr)
        sys.exit(1)
    # Generate and print the 5-character alphanumeric Steam Guard code
    code = generate_one_time_code(secret)
    print(code)

if __name__ == "__main__":
    main()
