#!/usr/bin/env python3
"""One chapter stored under several titles is indexed once.

Municode answers any node with its enclosing chapter, and an earlier
harvester stored that answer once per section, each file with its own
title and URL in the front matter. The indexer's duplicate check hashed
the whole file, so front matter alone made every copy look distinct and a
Colorado corpus of ~25,000 such files became 1.9 million chunks.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

BODY = ("Sec. 24-1101. - Purpose. This chapter governs oil and gas facilities "
        "within the city, including setbacks, noise and reclamation. " * 6)


def main() -> int:
    tmp = tempfile.mkdtemp(prefix="regbase-dedup-")
    os.environ["REGBASE_CORPUS"] = str(Path(tmp) / "corpus")
    import build_index, common

    src = common.Source(id="co-test-municode", jurisdiction_level="municipal", state="CO",
                        municipality="Test", name="Test Municipal Code",
                        code_platform="municode", documents=[])
    tdir = common.TEXT_DIR / "CO" / "co-test-municode"
    tdir.mkdir(parents=True, exist_ok=True)
    for i, title in enumerate(["Sec. 24-1101. - Purpose.", "Sec. 24-1102. - Setbacks.",
                               "Sec. 24-1103. - Noise."]):
        f = tdir / f"sec-24-110{i + 1}-{i:02d}.md"
        url = f"https://example.test/code?nodeId=CH11_S24-110{i + 1}"
        f.write_text(f"---\ntitle: {title}\nurl: {url}\n---\n\n{BODY}\n", encoding="utf-8")
        common.manifest_append({"key": f"co-test-municode::{url}", "source_id": "co-test-municode",
                                "url": url, "title": title, "doc_type": "code",
                                "http_status": 200, "text_chars": len(BODY),
                                "text_path": str(f.relative_to(common.CORPUS_DIR))})

    con = build_index.connect(Path(tmp) / "index.sqlite", rebuild=True)
    build_index.upsert_sources(con, [src])
    stats = build_index.index_documents(con, [src], common.manifest_read())
    n_chunks = con.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
    con.close()

    failed = 0
    def check(label, ok):
        nonlocal failed
        print(f"{'PASS' if ok else 'FAIL'}  {label}"); failed += not ok

    check("three records found with text", stats["with_text"] == 3)
    check("two of them recognised as the same body", stats.get("dup_body") == 2)
    check("the chapter is chunked once", stats["chunked"] == 1 and n_chunks >= 1)
    print("\n" + ("identical bodies index once whatever their front matter"
                  if not failed else f"{failed} check(s) failed"))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
