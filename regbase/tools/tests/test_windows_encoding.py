#!/usr/bin/env python3
"""Guard against the encoding trap that broke setup-windows.ps1.

Windows PowerShell 5.1 - still the default on Windows 10/11 - decodes .ps1
files as the system ANSI code page unless a UTF-8 byte-order mark is present.
A single non-ASCII character (an em dash, a curly quote) therefore turns into
mojibake inside a quoted string and unwinds the parser, producing a cascade of
misleading 'missing closing brace' errors far from the real line.

So every shipped PowerShell script must be ASCII-only in its body AND carry a
BOM. This test enforces both.
"""
from __future__ import annotations

import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
BOM = b"\xef\xbb\xbf"

REPLACEMENTS = {
    "—": "-", "–": "-", "‘": "'", "’": "'",
    "“": '"', "”": '"', "…": "...", " ": " ",
    "→": "->", "≥": ">=", "≤": "<=",
}


def check(path: Path) -> list[str]:
    data = path.read_bytes()
    problems: list[str] = []

    if not data.startswith(BOM):
        problems.append(
            f"{path.name}: no UTF-8 BOM - PowerShell 5.1 will decode this as ANSI"
        )
    body = data[len(BOM):] if data.startswith(BOM) else data

    for lineno, raw in enumerate(body.split(b"\n"), 1):
        for col, byte in enumerate(raw, 1):
            if byte > 127:
                try:
                    ctx = raw.decode("utf-8", errors="replace").strip()
                except Exception:
                    ctx = "<undecodable>"
                problems.append(
                    f"{path.name}:{lineno}:{col}: non-ASCII byte 0x{byte:02x} - {ctx[:80]}"
                )
                break

    if b"\r\n" not in body and body.strip():
        problems.append(f"{path.name}: LF line endings; prefer CRLF for Windows")

    text = body.decode("ascii", errors="replace")
    if text.count("{") != text.count("}"):
        problems.append(
            f"{path.name}: unbalanced braces ({text.count('{')} open, "
            f"{text.count('}')} close)"
        )
    if text.count("(") != text.count(")"):
        problems.append(
            f"{path.name}: unbalanced parens ({text.count('(')} open, "
            f"{text.count(')')} close)"
        )
    return problems


def main() -> int:
    scripts = sorted(TOOLS.rglob("*.ps1"))
    if not scripts:
        print("no PowerShell scripts found - nothing to check")
        return 0

    failures: list[str] = []
    for s in scripts:
        problems = check(s)
        if problems:
            failures.extend(problems)
            for p in problems:
                print(f"FAIL  {p}")
        else:
            print(f"PASS  {s.name}: ASCII body, BOM present, CRLF, balanced")

    if failures:
        print(f"\n{len(failures)} problem(s). Fix with the REPLACEMENTS table above, "
              f"then rewrite as BOM + CRLF + ASCII.")
        return 1
    print(f"\nall {len(scripts)} PowerShell script(s) safe for Windows PowerShell 5.1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
