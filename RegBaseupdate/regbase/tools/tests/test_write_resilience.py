#!/usr/bin/env python3
"""A single unwritable file must never end a harvest run.

A real run fetched 531 documents successfully and then died on document 532,
when Windows refused the write of one PDF into C:\\RegBaseCorpus\\raw. Antivirus
real-time scanning and Controlled Folder Access both do this, PDFs especially.
Everything already downloaded stayed on disk, but the run stopped and the
remaining sources went unfetched.

store() now retries briefly, then records the error and carries on. The raw
bytes are only a cache; the extracted text is the product, and it is still in
memory at that point, so a blocked raw write costs nothing that matters.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]

HTML = (b"<html><body><h1>Chapter 23</h1>"
        b"<p>No compressor shall be located within 500 feet of a dwelling.</p>"
        b"</body></html>")


class _Resp:
    status_code = 200
    content = HTML
    headers = {"Content-Type": "text/html"}
    url = "https://example.gov/code"


def main() -> int:
    tmp = tempfile.mkdtemp(prefix="regbase-write-")
    # Redirect the whole corpus, not just raw: otherwise the fixture text

    # lands in the committed corpus and is indexed as a real document.

    os.environ["REGBASE_CORPUS"] = tmp

    os.environ["REGBASE_RAW"] = str(Path(tmp) / "raw")
    sys.path.insert(0, str(TOOLS))

    import common, harvest

    src = common.Source(id="co-write-test", jurisdiction_level="county",
                        state="CO", name="Write Test", county="Write")

    # Occupy the target path with a directory so write_bytes raises an OSError,
    # the same class of failure a blocked or locked file produces.
    raw_path, _ = harvest.local_paths(src, _Resp.url, "Chapter 23", ".html")
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.mkdir()

    try:
        rec = harvest.store(src, "Chapter 23", "code", "Write Test",
                            _Resp.url, _Resp())
    except OSError as exc:
        print(f"FAIL  store() still raises {type(exc).__name__}: {exc}")
        return 1

    text_file = common.TEXT_DIR / rec["text_path"] if rec["text_path"] else None
    checks = [
        ("store() returns instead of raising", True),
        ("the write error is recorded", bool(rec.get("raw_write_error"))),
        ("raw_path is blanked, not falsely claimed", rec["raw_path"] == ""),
        ("text was still extracted", rec["text_chars"] > 0),
        ("text file written to disk", bool(text_file and text_file.exists())),
    ]
    if text_file and text_file.exists():
        body = text_file.read_text(encoding="utf-8")
        checks.append(("regulatory content intact", "500 feet" in body))

    failed = 0
    for label, ok in checks:
        print(f"{'PASS' if ok else 'FAIL'}  {label}")
        failed += not ok

    print("\n" + ("a blocked raw write no longer ends the run"
                  if not failed else f"{failed} check(s) failed"))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
