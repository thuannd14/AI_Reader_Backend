"""CLI: import vocabulary CSV / XLSX files into the database.

Usage:
    python -m scripts.import_vocab "path/to/_vocab.csv" --source "ETS 2026" --lang en --level B1
    python -m scripts.import_vocab "path/to/file.xlsx" --lang zh --level HSK1+
    python -m scripts.import_vocab "*.csv" "*.xlsx"
"""
from __future__ import annotations

import argparse
import glob
import sys
from pathlib import Path

from sqlmodel import Session

from app.db import engine, init_db
from app.importer import import_file

_SUPPORTED = {".csv", ".xlsx", ".xlsm"}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Import vocabulary CSV/XLSX into the database."
    )
    parser.add_argument("paths", nargs="+", help="CSV/XLSX file(s) or glob patterns")
    parser.add_argument("--source", help="Source name (default: file name / stem)")
    parser.add_argument("--lang", choices=["en", "zh"], help="Override language")
    parser.add_argument("--level", help="Override level (e.g. B1, HSK3, HSK1+)")
    return parser


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
        except (AttributeError, ValueError):
            pass

    args = _build_parser().parse_args(argv)
    files: list[Path] = []
    for pattern in args.paths:
        matched = glob.glob(pattern)
        files.extend(Path(p) for p in (matched or [pattern]))

    # Deduplicate while keeping order
    seen: set[Path] = set()
    unique: list[Path] = []
    for path in files:
        key = path.resolve() if path.exists() else path
        if key in seen:
            continue
        seen.add(key)
        unique.append(path)
    files = unique

    if not files:
        sys.stderr.write("ERROR: no input files found.\n")
        return 1

    init_db()
    total = 0
    with Session(engine) as session:
        for path in files:
            if not path.exists():
                sys.stderr.write(f"SKIP (not found): {path}\n")
                continue
            if path.suffix.lower() not in _SUPPORTED:
                sys.stderr.write(f"SKIP (unsupported type): {path}\n")
                continue
            try:
                result = import_file(
                    session,
                    path,
                    source_name=args.source or None,
                    language=args.lang,
                    level=args.level,
                )
            except Exception as exc:
                sys.stderr.write(f"ERROR {path.name}: {exc}\n")
                return 1
            total += result["imported"]
            print(
                f"Imported {result['imported']:>4} words "
                f"[{result['language']}/{result['level']}] <- {path.name}"
                f"  (skipped {result['skipped']}, source_id={result['source_id']})"
            )
    print(f"\nDone. {total} words inserted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
