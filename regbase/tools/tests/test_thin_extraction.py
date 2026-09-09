#!/usr/bin/env python3
"""A JavaScript shell must not be recorded as a harvested document.

A real Colorado run "fetched" about forty municipal codes from Municode. Each
returned 6,095 bytes and 16 characters of text, because library.municode.com
delivers a bootstrap page and loads the ordinance itself over XHR. Nothing was
harvested, but the manifest recorded success and the indexer chunked the
result - so a search could return a citation reading "Greeley Chapter 18 - Oil
and Gas Operations" with no ordinance behind it.

An empty file wearing an authoritative title is worse than a failed fetch,
because a failure is visible and this is not.

The detector is a ratio, not a fixed floor: a short page is fine, but a
substantial response that strips to almost nothing means the text never
arrived.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]

# ~6 KB of chrome, no content: the Municode signature.
SHELL = (b"<html><head><title>Municode Library</title>"
         + b"<script>window.__CONFIG__={};</script>" * 60
         + b"</head><body><div id='app'></div><noscript>Enable JavaScript"
           b"</noscript></body></html>")

REAL = (b"<html><body><h1>Chapter 18 - Oil and Gas Operations</h1>"
        + b"<p>No compressor station shall be located within 1,000 feet of a "
          b"platted residential subdivision without a special use permit.</p>" * 12
        + b"</body></html>")


def _resp(payload: bytes):
    class R:
        status_code = 200
        content = payload
        headers = {"Content-Type": "text/html"}
        url = "https://library.municode.com/co/greeley/codes/code_of_ordinances"
    return R()


def main() -> int:
    tmp = tempfile.mkdtemp(prefix="regbase-thin-")
    # Redirect the whole corpus, not just raw: otherwise the fixture text

    # lands in the committed corpus and is indexed as a real document.

    os.environ["REGBASE_CORPUS"] = tmp

    os.environ["REGBASE_RAW"] = str(Path(tmp) / "raw")
    sys.path.insert(0, str(TOOLS))

    import common, harvest

    src = common.Source(id="co-thin-test", jurisdiction_level="municipal",
                        state="CO", name="Greeley Code", municipality="Greeley",
                        code_platform="municode")

    checks = []

    shell_rec = harvest.store(src, "Chapter 18 - Oil and Gas Operations", "code",
                              "Greeley Code",
                              "https://library.municode.com/co/greeley/a",
                              _resp(SHELL))
    checks += [
        ("shell flagged as thin", bool(shell_rec.get("thin_extraction"))),
        ("shell writes NO text file", shell_rec["text_path"] == ""),
        ("shell reports zero text chars", shell_rec["text_chars"] == 0),
    ]

    real_rec = harvest.store(src, "Chapter 18 - Oil and Gas Operations", "code",
                             "Greeley Code",
                             "https://library.municode.com/co/greeley/b",
                             _resp(REAL))
    checks += [
        ("real content NOT flagged", not real_rec.get("thin_extraction")),
        ("real content writes a text file", real_rec["text_path"] != ""),
        ("real content keeps its text", real_rec["text_chars"] > 200),
    ]

    # A genuinely small response must not be misread as a shell.
    tiny = harvest.store(src, "Notice", "guidance", "Greeley Code",
                         "https://example.gov/notice",
                         _resp(b"<html><body><p>Short notice.</p></body></html>"))
    checks.append(("a genuinely tiny page is not flagged",
                   not tiny.get("thin_extraction")))

    failed = 0
    for label, ok in checks:
        print(f"{'PASS' if ok else 'FAIL'}  {label}")
        failed += not ok

    print("\n" + ("JavaScript shells are refused, real ordinances are kept"
                  if not failed else f"{failed} check(s) failed"))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
