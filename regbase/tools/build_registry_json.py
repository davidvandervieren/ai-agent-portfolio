#!/usr/bin/env python3
"""Flatten regbase/sources/*.yaml into a single web/registry.json bundle.

The HTML review tool and the chat agent both read this file, so it is the one
place that has to stay in sync with the YAML registry.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import common


def build() -> dict:
    sources = common.load_sources()
    records = []
    for s in sources:
        records.append({
            "id": s.id,
            "level": s.jurisdiction_level,
            "state": s.state,
            "county": s.county,
            "municipality": s.municipality,
            "name": s.name,
            "agency": s.agency,
            "label": s.jurisdiction_label,
            "authority_type": s.authority_type,
            "applies_to": s.applies_to,
            "code_platform": s.code_platform,
            "landing_url": s.landing_url,
            "documents": s.documents,
            "permits": s.permits,
            "gis": s.gis,
            "contacts": s.contacts,
            "confidence": s.confidence,
            "last_reviewed": s.last_reviewed,
            "source_file": s._file,
        })
    by_state = Counter(r["state"] for r in records)
    by_level = Counter(r["level"] for r in records)
    return {
        "generated_at": common.now_iso(),
        "counts": {
            "sources": len(records),
            "documents": sum(len(r["documents"] or []) for r in records),
            "permits": sum(len(r["permits"] or []) for r in records),
            "by_state": dict(sorted(by_state.items())),
            "by_level": dict(sorted(by_level.items())),
        },
        "sources": records,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("-o", "--out", default=str(common.ROOT / "web" / "registry.json"))
    ap.add_argument("--indent", type=int, default=None, help="pretty-print with N spaces")
    args = ap.parse_args()

    bundle = build()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(bundle, indent=args.indent, ensure_ascii=False), encoding="utf-8")
    c = bundle["counts"]
    print(f"wrote {out}  sources={c['sources']} documents={c['documents']} permits={c['permits']}")
    print("  by state:", c["by_state"])
    print("  by level:", c["by_level"])


if __name__ == "__main__":
    main()
