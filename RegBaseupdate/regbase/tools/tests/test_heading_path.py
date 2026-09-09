#!/usr/bin/env python3
"""Citation heading trails must not repeat themselves.

A live search returned:

    heading: Regulation & Guiding Documents > Comparison of Reciprocal Oil and
             Gas Setback Standards > Regulation & Guiding Documents >
             Comparison of Reciprocal Oil and Gas Setback Standards

The extractor emits a full `<!-- heading-path: A > B -->` marker AND the
heading line itself, so the segments arrive twice: A > B from the marker, then
A and B from the heading stack. The dedup compared each segment only against
its immediate predecessor, so the non-adjacent repeat survived into every
citation.

Cosmetic in a terminal, but these trails are what a reader uses to locate a
provision in the source document, and a doubled trail undermines that.
"""
from __future__ import annotations

import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

import build_index  # noqa: E402

DOC = """---
title: Regulation & Guiding Documents
---

<!-- heading-path: Regulation & Guiding Documents -->
# Regulation & Guiding Documents

<!-- heading-path: Regulation & Guiding Documents > Comparison of Reciprocal Oil and Gas Setback Standards -->
## Comparison of Reciprocal Oil and Gas Setback Standards

Provision | Pre-Jan. 2021 UDC | Current UDC

<!-- heading-path: Regulation & Guiding Documents > Reciprocal Setbacks -->
## Reciprocal Setbacks

The following options for setbacks were created to allow Erie to develop.

<!-- heading-path: Regulation & Guiding Documents > Reciprocal Setbacks > Option A -->
### Option A

Setbacks from planned, yet to be completed oil and gas facilities.
"""


def main() -> int:
    paths = [p for p, a, b in build_index.segment_by_headings(DOC) if DOC[a:b].strip()]
    failed = 0

    for p in paths:
        segs = [x for x in p.split(" > ") if x]
        if len(segs) != len(set(segs)):
            print(f"FAIL  repeated segment in trail: {p}")
            failed += 1

    if not failed:
        print(f"PASS  no repeated segments across {len(paths)} trail(s)")

    # Nesting must still be preserved - dedup must not flatten the hierarchy.
    deepest = max(paths, key=lambda p: p.count(" > ")) if paths else ""
    ok = deepest.endswith("Option A") and "Reciprocal Setbacks" in deepest
    print(f"{'PASS' if ok else 'FAIL'}  nesting preserved: {deepest}")
    failed += not ok

    # A document with no headings at all must still yield one section.
    plain = build_index.segment_by_headings("Just some regulatory text, no headings.")
    ok = len(plain) == 1
    print(f"{'PASS' if ok else 'FAIL'}  heading-free document yields one section")
    failed += not ok

    print("\n" + ("citation trails are clean" if not failed
                  else f"{failed} problem(s)"))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
