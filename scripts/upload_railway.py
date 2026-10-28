"""Upload vocabulary CSV/XLSX to the Railway production API.

Never put the API key in git. Set it once per shell:

    # PowerShell
    $env:AIREADER_API_KEY="your_key_here"

    # cmd
    set AIreader_API_KEY=your_key_here

Usage:
    # Chinese (HSK)
    python -m scripts.upload_railway "path\\file.xlsx" --lang zh --level HSK2+
    # English (CEFR)
    python -m scripts.upload_railway "path\\file.csv" --lang en --level B2
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import sys
import uuid
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_BASE = "https://aireaderbackend-production.up.railway.app"
_SUPPORTED = {".csv", ".xlsx", ".xlsm"}


def _api_key(cli_key: str | None) -> str:
    key = (cli_key or os.environ.get("AIREADER_API_KEY") or "").strip()
    if not key:
        sys.stderr.write(
            "ERROR: missing API key.\n"
            "  PowerShell:  $env:AIREADER_API_KEY=\"...\"\n"
            "  Or pass:     --key ...  (avoid: key stays in shell history)\n"
        )
        raise SystemExit(2)
    return key


def _xlsx_to_csv_bytes(path: Path) -> bytes:
    try:
        import openpyxl
    except ImportError as exc:
        raise SystemExit(
            "ERROR: openpyxl required for .xlsx. Run: pip install openpyxl"
        ) from exc

    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    buf = io.StringIO()
    writer = csv.writer(buf)
    for row in ws.iter_rows(values_only=True):
        writer.writerow([("" if c is None else c) for c in row])
    wb.close()
    # utf-8-sig helps Excel; API accepts UTF-8 fine
    return buf.getvalue().encode("utf-8-sig")


def _file_payload(path: Path) -> tuple[str, bytes]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return path.name, path.read_bytes()
    if suffix in (".xlsx", ".xlsm"):
        return path.with_suffix(".csv").name, _xlsx_to_csv_bytes(path)
    raise SystemExit(f"ERROR: unsupported type {suffix} (use .csv / .xlsx)")


def _multipart(
    fields: dict[str, str],
    file_field: str,
    filename: str,
    content: bytes,
) -> tuple[bytes, str]:
    boundary = f"----AIReader{uuid.uuid4().hex}"
    body = bytearray()
    for name, value in fields.items():
        body.extend(f"--{boundary}\r\n".encode())
        body.extend(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
        body.extend(value.encode("utf-8"))
        body.extend(b"\r\n")
    body.extend(f"--{boundary}\r\n".encode())
    body.extend(
        f'Content-Disposition: form-data; name="{file_field}"; '
        f'filename="{filename}"\r\n'.encode()
    )
    body.extend(b"Content-Type: text/csv\r\n\r\n")
    body.extend(content)
    body.extend(b"\r\n")
    body.extend(f"--{boundary}--\r\n".encode())
    return bytes(body), f"multipart/form-data; boundary={boundary}"


def upload(
    path: Path,
    *,
    base: str,
    key: str,
    language: str | None,
    level: str | None,
    source_name: str | None,
) -> dict:
    filename, content = _file_payload(path)
    fields: dict[str, str] = {}
    if language:
        fields["language"] = language
    if level:
        fields["level"] = level
    fields["source_name"] = source_name or path.stem

    body, content_type = _multipart(fields, "file", filename, content)
    url = base.rstrip("/") + "/import"
    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Content-Type": content_type,
            "X-API-Key": key,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            raw = response.read().decode("utf-8")
            status = response.status
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace")
        status = exc.code
        raise SystemExit(f"ERROR HTTP {status}: {raw}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"ERROR: cannot reach {url}: {exc.reason}") from exc

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        raise SystemExit(f"ERROR: non-JSON response ({status}): {raw}") from None


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
        except (AttributeError, ValueError):
            pass

    parser = argparse.ArgumentParser(
        description="Upload vocabulary CSV/XLSX to Railway production."
    )
    parser.add_argument("path", help="CSV or XLSX file")
    parser.add_argument("--lang", choices=["en", "zh"], help="language override")
    parser.add_argument("--level", help="level override (e.g. HSK2+)")
    parser.add_argument("--source", help="source_name (default: file stem)")
    parser.add_argument(
        "--base",
        default=os.environ.get("AIREADER_API_BASE", DEFAULT_BASE),
        help=f"API base URL (default: {DEFAULT_BASE})",
    )
    parser.add_argument(
        "--key",
        help="API key (prefer env AIreader_API_KEY — do not commit the key)",
    )
    args = parser.parse_args(argv)

    path = Path(args.path)
    if not path.exists():
        sys.stderr.write(f"ERROR: file not found: {path}\n")
        return 1
    if path.suffix.lower() not in _SUPPORTED:
        sys.stderr.write(f"ERROR: unsupported type: {path.suffix}\n")
        return 1

    key = _api_key(args.key)
    result = upload(
        path,
        base=args.base,
        key=key,
        language=args.lang,
        level=args.level,
        source_name=args.source,
    )
    imported = result.get("imported", "?")
    skipped = result.get("skipped", "?")
    source_id = result.get("source_id", "?")
    source = result.get("source", path.stem)
    lang = result.get("language", args.lang or "?")
    level = result.get("level", args.level or "?")
    print(
        f"Uploaded {imported} words [{lang}/{level}] <- {source}  "
        f"(skipped {skipped}, source_id={source_id})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
