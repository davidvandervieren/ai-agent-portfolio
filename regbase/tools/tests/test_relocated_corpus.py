#!/usr/bin/env python3
"""The raw corpus must work when REGBASE_RAW points outside the project.

That is the recommended setup: a project living in OneDrive or Dropbox should
not sync tens of gigabytes of harvested PDFs, so REGBASE_RAW gets pointed at a
local unsynced directory.

The first real crawl crashed on exactly this. store() recorded manifest paths
with `raw_path.relative_to(CORPUS_DIR)`, which raises ValueError the moment
RAW_DIR is not under CORPUS_DIR - after the page had been fetched and written,
so the failure landed at the end of a successful download rather than at
startup.

Manifest paths are now recorded relative to their own root (RAW_DIR for raw,
TEXT_DIR for text), and build_index._resolve() searches both.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]


class _Resp:
    status_code = 200
    content = (b"<html><body><h1>Chapter 23</h1>"
               b"<p>No compressor shall be located within 500 feet.</p></body></html>")
    headers = {"Content-Type": "text/html"}
    url = "https://example.gov/code"


def main() -> int:
    tmp = tempfile.mkdtemp(prefix="regbase-raw-")
    os.environ["REGBASE_RAW"] = str(Path(tmp) / "raw")
    sys.path.insert(0, str(TOOLS))

    import common, harvest, build_index

    if common.RAW_DIR.is_relative_to(common.CORPUS_DIR):
        print("FAIL  REGBASE_RAW was not honored; cannot exercise the bug")
        return 1
    print(f"RAW_DIR    {common.RAW_DIR}  (outside CORPUS_DIR)")

    src = common.Source(id="co-test-relocate", jurisdiction_level="county",
                        state="CO", name="Test County Code", county="Test")

    try:
        rec = harvest.store(src, "Chapter 23 Zoning", "code",
                            "Test County Code", "https://example.gov/code", _Resp())
    except ValueError as exc:
        print(f"FAIL  store() raised on a relocated raw corpus: {exc}")
        return 1

    checks = [
        ("raw_path recorded", bool(rec["raw_path"])),
        ("raw_path relative to its own root", not Path(rec["raw_path"]).is_absolute()),
        ("text_path recorded", bool(rec["text_path"])),
        ("text extracted", rec["text_chars"] > 0),
        ("raw resolves from the index", build_index._resolve(rec["raw_path"]) is not None),
        ("text resolves from the index", build_index._resolve(rec["text_path"]) is not None),
        ("raw actually written", (common.RAW_DIR / rec["raw_path"]).exists()),
        ("text actually written", (common.TEXT_DIR / rec["text_path"]).exists()),
    ]

    failed = 0
    for label, ok in checks:
        print(f"{'PASS' if ok else 'FAIL'}  {label}")
        failed += not ok

    # The extracted text must survive the round trip intact.
    body = (common.TEXT_DIR / rec["text_path"]).read_text(encoding="utf-8")
    ok = "500 feet" in body and "Chapter 23" in body
    print(f"{'PASS' if ok else 'FAIL'}  extracted text round-trips")
    failed += not ok

    print("\n" + ("all relocated-corpus checks passed"
                  if not failed else f"{failed} check(s) failed"))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
