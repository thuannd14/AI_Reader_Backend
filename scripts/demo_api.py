"""Ping a running AI Reader API and pretty-print the JSON responses.

Usage:
    python -m scripts.demo_api                         # http://localhost:8000
    python -m scripts.demo_api --key secret123         # with API key
    python -m scripts.demo_api --base http://1.2.3.4:8000 --key K
    python -m scripts.demo_api --endpoints /words?level=B1 /stats
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request

DEFAULT_ENDPOINTS = ["/health", "/stats", "/sources", "/words?limit=3", "/words/1"]


def _get(url: str, key: str | None) -> tuple[int, str]:
    request = urllib.request.Request(url)
    if key:
        request.add_header("X-API-Key", key)
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return response.status, response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")
    except urllib.error.URLError as exc:
        return 0, f'{{"error": "{exc.reason}"}}'


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
        except (AttributeError, ValueError):
            pass

    parser = argparse.ArgumentParser(description="Test the API and print JSON.")
    parser.add_argument("--base", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--key", help="API key (X-API-Key)")
    parser.add_argument("--endpoints", nargs="*", default=DEFAULT_ENDPOINTS)
    args = parser.parse_args(argv)

    base = args.base.rstrip("/")
    print(f"Testing {base}\n")
    for endpoint in args.endpoints:
        status, body = _get(base + endpoint, args.key)
        try:
            body = json.dumps(json.loads(body), ensure_ascii=False, indent=2)
        except json.JSONDecodeError:
            pass
        print(f"### GET {endpoint}  ->  {status}")
        print(body)
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
