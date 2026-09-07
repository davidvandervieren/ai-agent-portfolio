#!/usr/bin/env python3
"""Every text file the toolchain reads or writes must specify UTF-8 explicitly.

Python's open()/read_text()/write_text() default to the *locale* encoding. On
Windows that is a legacy code page (cp1252 on a US install), not UTF-8, so a
registry file containing a section symbol, an em dash, or a curly quote decodes
into mojibake - silently, with no exception. The corrupted text then flows into
the index, into the citations, and into the generated review.

This was a real defect, caught only because an em dash from a YAML file
rendered as garbage on Windows while the identical dash in a Python source
literal rendered fine - the kind of clue that is easy to dismiss as cosmetic.

Regulatory text is the product here; it has to survive the round trip.

Uses the AST rather than a line regex, so occurrences inside docstrings and
string literals are not mistaken for calls.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]

TEXT_METHODS = {"read_text", "write_text"}
BINARY_MODES = {"rb", "wb", "ab", "r+b", "w+b", "a+b", "xb"}

# Modules with an `open` that is not encoded text I/O, so demanding an
# encoding= of them is meaningless: webbrowser.open takes a URL, and os.open
# returns a raw file descriptor.
NON_FILE_OPENERS = {"webbrowser", "os"}


def call_name(node: ast.Call) -> str:
    f = node.func
    if isinstance(f, ast.Attribute):
        return f.attr
    if isinstance(f, ast.Name):
        return f.id
    return ""


def is_binary(node: ast.Call) -> bool:
    """open(path, 'rb') and Path.open('rb') never guess an encoding.

    The mode argument sits in a different position for each: builtin
    open(path, mode) puts it second, Path.open(mode) puts it first.
    """
    mode_args = (node.args if isinstance(node.func, ast.Attribute)
                 else node.args[1:])
    for arg in mode_args:
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            if arg.value in BINARY_MODES or "b" in arg.value:
                return True
    for kw in node.keywords:
        if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
            if "b" in str(kw.value.value):
                return True
    return False


def scan(path: Path) -> list[str]:
    src = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(src, filename=str(path))
    except SyntaxError as exc:
        return [f"{path.name}: does not parse: {exc}"]

    lines = src.splitlines()
    problems: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = call_name(node)
        if name not in TEXT_METHODS and name != "open":
            continue
        if (isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id in NON_FILE_OPENERS):
            continue
        if is_binary(node):
            continue
        if any(kw.arg == "encoding" for kw in node.keywords):
            continue
        snippet = lines[node.lineno - 1].strip() if node.lineno <= len(lines) else ""
        problems.append(f"{path.name}:{node.lineno}: {snippet[:90]}")
    return problems


def main() -> int:
    failures: list[str] = []
    checked = 0
    for py in sorted(TOOLS.rglob("*.py")):
        if "__pycache__" in py.parts:
            continue
        checked += 1
        problems = scan(py)
        failures.extend(problems)
        for p in problems:
            print(f"FAIL  no explicit encoding: {p}")

    if failures:
        print(f"\n{len(failures)} unencoded text I/O site(s) across {checked} file(s).")
        print('Add encoding="utf-8" - the locale default silently corrupts data on Windows.')
        return 1

    print(f"all text I/O across {checked} file(s) specifies an encoding explicitly")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
