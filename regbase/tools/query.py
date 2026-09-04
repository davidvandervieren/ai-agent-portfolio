#!/usr/bin/env python3
"""RegBase query CLI — the retrieval layer an agent (or a human) talks to.

Every subcommand accepts --json so an agent can consume the result verbatim.

  search "<query>"      BM25 full-text over harvested code/rule text
  permits               flattened permit requirements for a jurisdiction
  jurisdiction          full profile of one jurisdiction + what is missing
  stack                 federal -> state -> county -> municipal permit stack
  gaps                  honest coverage holes in the registry
  people                decision makers / staff for a jurisdiction

Examples
  python3 regbase/tools/query.py stack --state CO --county Weld --asset compressor_station
  python3 regbase/tools/query.py permits --state NM --county Lea --asset swd_well --json
  python3 regbase/tools/query.py search "flowline setback" --state CO -n 5
  python3 regbase/tools/query.py gaps --state TX

The database is built by regbase/tools/build_index.py. Nothing here reaches the
network: if a fact is not in the registry, this tool reports it as MISSING
rather than inventing it.
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from collections import OrderedDict, defaultdict
from pathlib import Path
from typing import Any, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

import common  # noqa: E402

LEVEL_ORDER = ["federal", "state", "county", "municipal", "special_district", "tribal"]
LEVEL_TITLE = {
    "federal": "FEDERAL",
    "state": "STATE",
    "county": "COUNTY",
    "municipal": "MUNICIPAL",
    "special_district": "SPECIAL DISTRICT",
    "tribal": "TRIBAL",
}


# ------------------------------------------------------------------ db helpers

def open_db(path: Optional[str] = None) -> sqlite3.Connection:
    p = Path(path or common.INDEX_DB)
    if not p.exists():
        raise SystemExit(
            f"no index at {p}\n"
            f"build it first:  python3 {Path(__file__).parent / 'build_index.py'} --rebuild"
        )
    con = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def jl(value: str) -> Any:
    """Parse a JSON column, tolerating junk."""
    try:
        return json.loads(value) if value else []
    except (TypeError, json.JSONDecodeError):
        return []


def norm_county(name: str) -> str:
    return re.sub(r"\s+county\s*$", "", (name or "").strip(), flags=re.I).strip()


def county_clause(col: str = "county") -> str:
    """SQL fragment matching a county even in combined values like 'Adams/Weld'."""
    return (f"(',' || lower(replace(replace(replace({col}, ' / ', '/'), '/ ', '/'), '/', ',')) "
            f"|| ',') LIKE ?")


def county_param(name: str) -> str:
    return f"%,{norm_county(name).lower()},%"


def asset_clause(col: str = "applies_to") -> str:
    return f"{col} LIKE ?"


def asset_param(asset: str) -> str:
    return f'%"{asset}"%'


def citation(row: sqlite3.Row | dict) -> str:
    """Render a citable string: 'Weld County Code Ch. 23-3-40 — <title> (<url>)'."""
    get = row.__getitem__ if isinstance(row, sqlite3.Row) else row.get
    root = (get("citation_root") or "").strip()
    heading = (get("heading_path") or "").strip()
    tail = heading.split(" > ")[-1].strip() if heading else ""
    if root and tail:
        # avoid 'Weld County Code Ch. 23 Weld County Code Ch. 23-3-40'
        if tail.startswith(root):
            root = ""
        elif root.startswith(tail):
            tail = ""
    left = " ".join(x for x in (root, tail) if x).strip()
    if not left:
        left = (get("jurisdiction_label") or "").strip() or "uncited"
    title = (get("title") or "untitled").strip()
    url = (get("url") or "").strip()
    return f"{left} — {title} ({url})" if url else f"{left} — {title}"


def out(payload: Any, human, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        human(payload)


def hr(title: str) -> str:
    return f"\n{title}\n" + "-" * max(len(title), 8)


# ------------------------------------------------------------------ search

FTS_SPECIAL = re.compile(r'["*()]|\b(?:AND|OR|NOT|NEAR)\b')


def fts_expr(query: str) -> str:
    """Turn a human query into a safe FTS5 MATCH expression.

    A query already containing FTS syntax (quotes, *, parens, boolean ops) is
    passed through untouched so power users keep full control.
    """
    if FTS_SPECIAL.search(query):
        return query
    tokens = re.findall(r"[\w][\w'\-]*", query)
    if not tokens:
        raise SystemExit("empty search query")
    return " AND ".join('"' + t.replace('"', "") + '"' for t in tokens)


def cmd_search(args, con: sqlite3.Connection) -> None:
    where, params = ["chunks_fts MATCH ?"], [fts_expr(args.query)]
    if args.state:
        where.append("c.state = ?"); params.append(args.state.upper())
    if args.county:
        where.append(county_clause("c.county")); params.append(county_param(args.county))
    if args.muni:
        where.append("lower(c.municipality) = ?"); params.append(args.muni.strip().lower())
    if args.level:
        where.append("s.jurisdiction_level = ?"); params.append(args.level)
    if args.doc_type:
        where.append("d.doc_type = ?"); params.append(args.doc_type)
    for a in args.asset or []:
        where.append(asset_clause("s.applies_to")); params.append(asset_param(a))

    sql = f"""
        SELECT c.id, c.source_id, c.jurisdiction_label, c.state, c.county, c.municipality,
               c.citation_root, c.heading_path, c.chunk_index, c.char_start, c.char_end,
               d.title, d.url, d.doc_type, d.local_text_path,
               s.jurisdiction_level, s.confidence, s.agency,
               bm25(chunks_fts, 10.0, 4.0, 2.0, 1.0) AS score,
               snippet(chunks_fts, 0, '[', ']', ' … ', 24) AS snip
        FROM chunks_fts
        JOIN chunks    c ON c.id = chunks_fts.rowid
        JOIN documents d ON d.id = c.document_id
        JOIN sources   s ON s.id = c.source_id
        WHERE {' AND '.join(where)}
        ORDER BY score
        LIMIT ?"""
    params.append(args.limit)
    try:
        rows = con.execute(sql, params).fetchall()
    except sqlite3.OperationalError as exc:
        raise SystemExit(f"FTS query error: {exc}\n(query was: {fts_expr(args.query)})")

    total_chunks = con.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
    results = [{
        "rank": i + 1,
        "score": round(r["score"], 4),
        "source_id": r["source_id"],
        "jurisdiction": r["jurisdiction_label"],
        "level": r["jurisdiction_level"],
        "state": r["state"], "county": r["county"], "municipality": r["municipality"],
        "doc_type": r["doc_type"],
        "heading_path": r["heading_path"],
        "citation": citation(r),
        "url": r["url"],
        "confidence": r["confidence"],
        "snippet": r["snip"],
        "chunk": {"id": r["id"], "index": r["chunk_index"],
                  "char_start": r["char_start"], "char_end": r["char_end"],
                  "text_path": r["local_text_path"]},
    } for i, r in enumerate(rows)]

    payload = {
        "query": args.query,
        "fts_expression": fts_expr(args.query),
        "filters": {"state": args.state, "county": args.county, "muni": args.muni,
                    "level": args.level, "doc_type": args.doc_type, "asset": args.asset},
        "corpus_chunks_indexed": total_chunks,
        "result_count": len(results),
        "results": results,
        "note": ("corpus/text is empty — no document text has been harvested yet, so "
                 "full-text search cannot answer anything. Use `permits`, `stack` and "
                 "`jurisdiction` (registry-backed) instead." if total_chunks == 0 else ""),
    }

    def human(p):
        if p["corpus_chunks_indexed"] == 0:
            print("0 chunks indexed — no harvested document text in this corpus yet.")
            print("Nothing to full-text search. Registry-backed commands still work:")
            print("  query.py permits / stack / jurisdiction / gaps / people")
            return
        if not p["results"]:
            print(f"no matches for {p['query']!r} "
                  f"across {p['corpus_chunks_indexed']} chunks with those filters")
            return
        print(f"{len(p['results'])} of {p['corpus_chunks_indexed']} chunks — {p['query']!r}")
        for r in p["results"]:
            print(f"\n[{r['rank']}] {r['jurisdiction']}  ({r['level']}, "
                  f"confidence={r['confidence']}, bm25={r['score']})")
            print(f"    {r['citation']}")
            if r["heading_path"]:
                print(f"    heading: {r['heading_path']}")
            print(f"    …{r['snippet']}…")

    out(payload, human, args.json)


# ------------------------------------------------------------------ permits

def permit_rows(con, state=None, county=None, muni=None, level=None,
                assets=None, source_ids=None) -> list[sqlite3.Row]:
    where, params = ["1=1"], []
    if state:
        where.append("p.state = ?"); params.append(state.upper())
    if county:
        where.append(county_clause("p.county")); params.append(county_param(county))
    if muni:
        where.append("lower(p.municipality) = ?"); params.append(muni.strip().lower())
    if level:
        where.append("p.jurisdiction_level = ?"); params.append(level)
    for a in assets or []:
        where.append(asset_clause("p.applies_to")); params.append(asset_param(a))
    if source_ids is not None:
        if not source_ids:
            return []
        where.append(f"p.source_id IN ({','.join('?' * len(source_ids))})")
        params.extend(source_ids)
    sql = f"""SELECT p.*, s.name AS source_name, s.code_platform, s.last_reviewed
              FROM permits p JOIN sources s ON s.id = p.source_id
              WHERE {' AND '.join(where)}
              ORDER BY CASE p.jurisdiction_level
                         WHEN 'federal' THEN 0 WHEN 'state' THEN 1 WHEN 'county' THEN 2
                         WHEN 'municipal' THEN 3 WHEN 'special_district' THEN 4 ELSE 5 END,
                       p.jurisdiction_label, p.permit_index"""
    return con.execute(sql, params).fetchall()


def permit_dict(r: sqlite3.Row) -> dict:
    return {
        "source_id": r["source_id"],
        "jurisdiction": r["jurisdiction_label"],
        "level": r["jurisdiction_level"],
        "state": r["state"], "county": r["county"], "municipality": r["municipality"],
        "agency": r["agency"] or r["source_name"],
        "permit": r["name"],
        "trigger": r["trigger"] or None,
        "form_id": r["form_id"] or None,
        "form_url": r["form_url"] or None,
        "typical_timeline_days": r["typical_timeline_days"] or None,
        "decision_body": r["decision_body"] or None,
        "public_hearing": (None if r["public_hearing"] is None else bool(r["public_hearing"])),
        "fee": r["fee"] or None,
        "applies_to": jl(r["applies_to"]),
        "authority_type": jl(r["authority_type"]),
        "landing_url": r["landing_url"] or None,
        "confidence": r["confidence"],
        "last_reviewed": r["last_reviewed"] or None,
        "missing": [f for f, v in (("trigger", r["trigger"]), ("form_id", r["form_id"]),
                                   ("fee", r["fee"]),
                                   ("typical_timeline_days", r["typical_timeline_days"]),
                                   ("decision_body", r["decision_body"])) if not v],
    }


NUMERIC_TIMELINE_RE = re.compile(r"^\s*\d+(\s*[-–]\s*\d+)?\s*$")


def fmt_timeline(value: str) -> str:
    """Registry timelines are free text ('30-60', 'CX: weeks; EIS: 1-3 years')."""
    v = (value or "").strip()
    return f"~{v} days" if NUMERIC_TIMELINE_RE.match(v) else v


def print_permits(items: list[dict], indent: str = "") -> None:
    by_j = OrderedDict()
    for it in items:
        by_j.setdefault((it["level"], it["jurisdiction"], it["agency"]), []).append(it)
    for (level, juris, agency), group in by_j.items():
        conf = group[0]["confidence"]
        head = juris if (not agency or agency in juris) else f"{juris} — {agency}"
        print(f"{indent}{head}  [{level}]  (confidence: {conf})")
        for it in group:
            bits = []
            if it["form_id"]:
                bits.append(it["form_id"])
            if it["decision_body"]:
                bits.append(f"decided by {it['decision_body']}")
            if it["public_hearing"]:
                bits.append("public hearing")
            if it["fee"]:
                bits.append(f"fee: {it['fee']}")
            print(f"{indent}  • {it['permit']}" + (f"   [{'; '.join(bits)}]" if bits else ""))
            if it["typical_timeline_days"]:
                print(f"{indent}      timeline: {fmt_timeline(it['typical_timeline_days'])}")
            if it["trigger"]:
                print(f"{indent}      trigger: {it['trigger']}")
            if it["form_url"]:
                print(f"{indent}      form: {it['form_url']}")
            if it["missing"]:
                print(f"{indent}      MISSING in registry: {', '.join(it['missing'])}")
        if group[0]["landing_url"]:
            print(f"{indent}  source: {group[0]['landing_url']}")
        print()


def cmd_permits(args, con) -> None:
    rows = permit_rows(con, state=args.state, county=args.county, muni=args.muni,
                       level=args.level, assets=args.asset)
    items = [permit_dict(r) for r in rows]
    payload = {
        "filters": {"state": args.state, "county": args.county, "muni": args.muni,
                    "level": args.level, "asset": args.asset},
        "count": len(items),
        "permits": items,
        "caveat": ("Registry-derived only. A jurisdiction with no permit rows here has NOT "
                   "been shown to require nothing — it means nothing has been recorded. "
                   "Run `query.py gaps` before treating this list as complete."),
    }

    def human(p):
        f = p["filters"]
        scope = " / ".join(x for x in [f["state"], f["county"], f["muni"], f["level"]] if x)
        assets = ", ".join(f["asset"] or []) or "any asset"
        print(f"{p['count']} permit(s) — {scope or 'all jurisdictions'} — {assets}")
        print()
        if not p["permits"]:
            print("NO PERMIT RECORDS for that filter. That is a registry gap, not a finding")
            print("that no permit is required. See: query.py gaps --state <ST>")
            return
        print_permits(p["permits"])
        print(p["caveat"])

    out(payload, human, args.json)


# ------------------------------------------------------------------ jurisdiction

def source_profile(con, r: sqlite3.Row) -> dict:
    docs = con.execute(
        "SELECT title, url, doc_type, format, citation_root, notes, local_text_path, "
        "n_chunks, fetched_at, http_status FROM documents WHERE source_id=? ORDER BY id",
        (r["id"],)).fetchall()
    permits = [permit_dict(x) for x in con.execute(
        "SELECT p.*, s.name AS source_name, s.code_platform, s.last_reviewed FROM permits p "
        "JOIN sources s ON s.id=p.source_id WHERE p.source_id=? ORDER BY p.permit_index",
        (r["id"],)).fetchall()]
    people = [dict(x) for x in con.execute(
        "SELECT id, title, body, role_type, full_name, staff_or_decision_maker, confidence "
        "FROM people WHERE jurisdiction_id=?", (r["id"],)).fetchall()]

    missing = []
    if not docs:
        missing.append("no documents registered")
    if not permits:
        missing.append("no permits registered")
    if not r["landing_url"]:
        missing.append("no landing_url")
    if not jl(r["gis"]):
        missing.append("no GIS endpoints")
    if not jl(r["contacts"]):
        missing.append("no contacts")
    if not jl(r["applies_to"]):
        missing.append("no applies_to asset tags")
    if r["confidence"] != "verified":
        missing.append(f"confidence is '{r['confidence']}' (not independently verified)")
    if docs and not any(d["n_chunks"] for d in docs):
        missing.append("no harvested document text (nothing full-text searchable)")
    if not any(p["full_name"] for p in [dict(x) for x in people]) and people:
        missing.append("people records exist but no verified names")

    return {
        "id": r["id"], "name": r["name"], "agency": r["agency"],
        "jurisdiction": r["jurisdiction_label"], "level": r["jurisdiction_level"],
        "state": r["state"], "county": r["county"], "municipality": r["municipality"],
        "code_platform": r["code_platform"], "landing_url": r["landing_url"],
        "authority_type": jl(r["authority_type"]), "applies_to": jl(r["applies_to"]),
        "confidence": r["confidence"], "last_reviewed": r["last_reviewed"],
        "source_file": r["source_file"],
        "documents": [dict(d) for d in docs],
        "permits": permits,
        "gis": jl(r["gis"]), "contacts": jl(r["contacts"]),
        "update_watch": jl(r["update_watch"]) or {},
        "people": people,
        "missing": missing,
    }


def cmd_jurisdiction(args, con) -> None:
    state = args.state.upper()
    where, params = ["s.state = ?"], [state]
    scope = state
    if args.municipality:
        where.append("lower(s.municipality) = ?")
        params.append(args.municipality.strip().lower())
        scope = f"{args.municipality}, {state}"
    elif args.county:
        where.append(county_clause("s.county"))
        params.append(county_param(args.county))
        scope = f"{norm_county(args.county)} County, {state}"
    rows = con.execute(f"SELECT * FROM sources s WHERE {' AND '.join(where)} "
                       f"ORDER BY CASE s.jurisdiction_level WHEN 'state' THEN 0 "
                       f"WHEN 'county' THEN 1 WHEN 'municipal' THEN 2 ELSE 3 END, s.name",
                       params).fetchall()
    profiles = [source_profile(con, r) for r in rows]

    context = {}
    if not args.county and not args.municipality:
        context = {
            "counties_with_records": [x[0] for x in con.execute(
                "SELECT DISTINCT county FROM sources WHERE state=? AND county<>'' "
                "ORDER BY county", (state,)).fetchall()],
            "municipalities_with_records": [x[0] for x in con.execute(
                "SELECT DISTINCT municipality FROM sources WHERE state=? AND municipality<>'' "
                "ORDER BY municipality", (state,)).fetchall()],
        }

    payload = {"scope": scope, "record_count": len(profiles),
               "records": profiles, "context": context,
               "note": ("No registry record matches that jurisdiction. Do not infer its "
                        "requirements — say the registry has no record and name what to "
                        "check (county land use code, municipal code platform, state agency)."
                        if not profiles else "")}

    def human(p):
        print(f"{p['scope']} — {p['record_count']} registry record(s)")
        if not p["records"]:
            print("\nNO RECORD IN REGISTRY for that jurisdiction.")
            print(p["note"])
            if p["context"].get("counties_with_records"):
                print("\ncounties with records in this state:")
                print("  " + ", ".join(p["context"]["counties_with_records"]))
            return
        for r in p["records"]:
            print(hr(f"{r['jurisdiction']} — {r['name']}  [{r['level']}]"))
            print(f"  id            : {r['id']}   (from {r['source_file']})")
            print(f"  agency        : {r['agency'] or '(none recorded)'}")
            print(f"  code platform : {r['code_platform']}")
            print(f"  landing       : {r['landing_url'] or '(none)'}")
            print(f"  authority     : {', '.join(r['authority_type']) or '(none)'}")
            print(f"  applies to    : {', '.join(r['applies_to']) or '(none)'}")
            print(f"  confidence    : {r['confidence']}   last reviewed: "
                  f"{r['last_reviewed'] or '(never)'}")
            print(f"  documents     : {len(r['documents'])}  "
                  f"(text harvested for {sum(1 for d in r['documents'] if d['n_chunks'])})")
            for d in r["documents"][:8]:
                print(f"     - [{d['doc_type']}] {d['title']}")
                print(f"       {d['url']}")
            if len(r["documents"]) > 8:
                print(f"     … {len(r['documents']) - 8} more")
            if r["permits"]:
                print(f"  permits       : {len(r['permits'])}")
                print_permits(r["permits"], indent="     ")
            else:
                print("  permits       : NONE RECORDED")
            for label, key in (("gis", "gis"), ("contacts", "contacts")):
                if r[key]:
                    print(f"  {label}:")
                    for g in r[key]:
                        print("     - " + json.dumps(g, ensure_ascii=False))
            if r["people"]:
                print("  people:")
                for pp in r["people"]:
                    print(f"     - {pp['full_name'] or '(name unverified)'} — {pp['title']} "
                          f"({pp['body']}, {pp['staff_or_decision_maker'] or '?'}, "
                          f"confidence={pp['confidence']})")
            print("  MISSING / TO VERIFY:")
            for m in r["missing"] or ["(nothing flagged)"]:
                print(f"     ! {m}")
        if p["context"].get("counties_with_records"):
            print(hr("state coverage"))
            print("  counties with records: "
                  + ", ".join(p["context"]["counties_with_records"]))
            print("  municipalities       : "
                  + ", ".join(p["context"]["municipalities_with_records"]) or "(none)")

    out(payload, human, args.json)


# ------------------------------------------------------------------ stack

def cmd_stack(args, con) -> None:
    state = args.state.upper()
    assets = args.asset or []
    groups: "OrderedDict[str, list[dict]]" = OrderedDict((lv, []) for lv in LEVEL_ORDER)
    selected: dict[str, sqlite3.Row] = {}
    reasons: dict[str, str] = {}

    def collect(sql: str, params: list, reason: str) -> None:
        for r in con.execute(sql, params).fetchall():
            if assets:
                at = jl(r["applies_to"])
                if at and not any(a in at for a in assets):
                    continue
            if r["id"] not in selected:
                selected[r["id"]] = r
                reasons[r["id"]] = reason

    collect("SELECT * FROM sources WHERE state='US' ORDER BY name", [],
            "federal — applies everywhere")
    collect("SELECT * FROM sources WHERE state=? AND jurisdiction_level='state' ORDER BY name",
            [state], f"{state} statewide authority")
    if args.county:
        collect(f"SELECT * FROM sources WHERE state=? AND {county_clause('county')} "
                f"AND jurisdiction_level IN ('county','special_district','tribal') ORDER BY name",
                [state, county_param(args.county)], f"{norm_county(args.county)} County")
    for m in args.muni or []:
        collect("SELECT * FROM sources WHERE state=? AND lower(municipality)=? ORDER BY name",
                [state, m.strip().lower()], f"municipality: {m}")
    collect("SELECT * FROM sources WHERE state=? AND jurisdiction_level='special_district' "
            "AND county='' AND municipality='' ORDER BY name", [state],
            f"{state} special district (statewide scope)")

    seen: set[tuple] = set()
    permits_by_source = defaultdict(list)
    for r in permit_rows(con, source_ids=list(selected)):
        permits_by_source[r["source_id"]].append(r)

    no_permit_sources: list[dict] = []
    for sid, r in selected.items():
        entries = []
        for pr in permits_by_source.get(sid, []):
            if assets:
                at = jl(pr["applies_to"])
                if at and not any(a in at for a in assets):
                    continue
            key = (r["jurisdiction_level"], r["jurisdiction_label"].lower(),
                   (pr["name"] or "").strip().lower())
            if key in seen:
                continue
            seen.add(key)
            entries.append(permit_dict(pr))
        if entries:
            groups[r["jurisdiction_level"]].extend(entries)
        else:
            no_permit_sources.append({
                "source_id": sid, "jurisdiction": r["jurisdiction_label"],
                "level": r["jurisdiction_level"], "name": r["name"],
                "agency": r["agency"], "landing_url": r["landing_url"],
                "confidence": r["confidence"],
                "authority_type": jl(r["authority_type"]),
                "why_included": reasons[sid],
                "gap": "authority is in the registry but NO permit has been recorded for it",
            })

    coverage_warnings = []
    if args.county and not any(
            g["level"] == "county" for g in
            [{"level": s["jurisdiction_level"]} for s in selected.values()]):
        coverage_warnings.append(
            f"no county-level record for {norm_county(args.county)} County, {state} — "
            f"county requirements are UNKNOWN, not zero")
    for m in args.muni or []:
        if not any(s["municipality"].lower() == m.strip().lower() for s in selected.values()):
            coverage_warnings.append(
                f"no municipal record for {m}, {state} — municipal requirements are UNKNOWN. "
                f"Check the town/city code platform and any oil & gas overlay directly.")
    unverified = sorted({s["jurisdiction_label"] for s in selected.values()
                         if s["confidence"] == "unverified"})
    if unverified:
        coverage_warnings.append("unverified-confidence jurisdictions in this stack: "
                                 + ", ".join(unverified))

    payload = {
        "project": {"state": state, "county": norm_county(args.county) if args.county else None,
                    "municipalities": args.muni or [], "assets": assets},
        "review_order": LEVEL_ORDER,
        "counts": {lv: len(v) for lv, v in groups.items()},
        "total_permits": sum(len(v) for v in groups.values()),
        "authorities_considered": len(selected),
        "stack": {lv: v for lv, v in groups.items() if v},
        "authorities_without_recorded_permits": no_permit_sources,
        "coverage_warnings": coverage_warnings,
        "caveat": ("This stack is only as complete as the registry. Treat every "
                   "'authorities_without_recorded_permits' entry and every coverage warning as "
                   "an open question to confirm with the agency — never as 'no permit required'."),
    }

    def human(p):
        pr = p["project"]
        head = (f"PERMIT STACK — {pr['state']}"
                + (f" / {pr['county']} County" if pr["county"] else "")
                + (f" / {', '.join(pr['municipalities'])}" if pr["municipalities"] else "")
                + (f" — assets: {', '.join(pr['assets'])}" if pr["assets"] else ""))
        print(head)
        print("=" * len(head))
        print(f"{p['total_permits']} recorded permit(s) across "
              f"{p['authorities_considered']} authorities\n")
        for lv in p["review_order"]:
            items = p["stack"].get(lv)
            if not items:
                continue
            print(hr(f"{LEVEL_TITLE[lv]}  ({len(items)} permit(s))"))
            print_permits(items, indent="  ")
        if p["authorities_without_recorded_permits"]:
            print(hr("AUTHORITIES WITH NO PERMIT RECORDED (open questions)"))
            for a in p["authorities_without_recorded_permits"]:
                print(f"  ? [{a['level']}] {a['jurisdiction']} — {a['name']}")
                print(f"      authority: {', '.join(a['authority_type']) or '(untagged)'}"
                      f"   confidence: {a['confidence']}")
                if a["landing_url"]:
                    print(f"      {a['landing_url']}")
        if p["coverage_warnings"]:
            print(hr("COVERAGE WARNINGS"))
            for w in p["coverage_warnings"]:
                print(f"  ! {w}")
        print("\n" + p["caveat"])

    out(payload, human, args.json)


# ------------------------------------------------------------------ gaps

COUNTY_MENTION_RE = re.compile(r"\b([A-Z][a-z]+(?:[ -][A-Z][a-z]+)?)\s+County\b")
# "Midland, Ector, Reeves, Loving, Ward and Winkler counties" style enumerations
COUNTY_LIST_RE = re.compile(
    r"((?:[A-Z][a-zA-Z]+(?:\s[A-Z][a-zA-Z]+)?(?:,\s*|,?\s+and\s+)){2,}"
    r"[A-Z][a-zA-Z]+(?:\s[A-Z][a-zA-Z]+)?)\s+counties\b")
COUNTY_STOPWORDS = {"The", "This", "That", "Each", "Every", "Some", "Most", "Other", "Same",
                    "Texas", "Colorado", "Wyoming", "Utah", "New", "In", "For", "All", "Any",
                    "No", "Per", "Which", "State", "Home", "Rule", "One", "Two", "Both"}
NOTES_STATE = {"co": "CO", "wy": "WY", "nm": "NM", "ut": "UT",
               "tx-west": "TX", "tx-east": "TX"}


def counties_named_in_notes(state: str) -> dict[str, list[str]]:
    """Counties named in regbase/sources/*.notes.md for this state.

    These are counties the research notes themselves flag as in-scope. Using the
    repo's own notes (rather than a model-memory county roster) keeps this
    honest: it reports what THIS project said it needed, not what a model
    believes the county list to be.
    """
    found: dict[str, list[str]] = {}
    for p in sorted(common.SOURCES_DIR.glob("*.notes.md")):
        st = NOTES_STATE.get(p.stem.replace(".notes", ""))
        if st != state:
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        names: list[str] = [m.group(1).strip() for m in COUNTY_MENTION_RE.finditer(text)]
        for m in COUNTY_LIST_RE.finditer(text):
            names.extend(re.split(r",\s*|\s+and\s+", m.group(1)))
        for name in names:
            name = name.strip().strip(".,;:")
            if not name or name.split()[0] in COUNTY_STOPWORDS:
                continue
            found.setdefault(name, [])
            if p.name not in found[name]:
                found[name].append(p.name)
    return found


def cmd_gaps(args, con) -> None:
    states = [args.state.upper()] if args.state else [
        r[0] for r in con.execute("SELECT DISTINCT state FROM sources ORDER BY state")]
    report = {"states": [], "generated_from": str(common.INDEX_DB)}

    for st in states:
        srcs = con.execute("SELECT * FROM sources WHERE state=? ORDER BY id", (st,)).fetchall()
        no_docs, no_permits, no_landing, unverified, stale = [], [], [], [], []
        for r in srcs:
            entry = {"id": r["id"], "jurisdiction": r["jurisdiction_label"],
                     "level": r["jurisdiction_level"], "confidence": r["confidence"]}
            if r["n_documents"] == 0:
                no_docs.append(entry)
            if r["n_permits"] == 0:
                no_permits.append(entry)
            if not r["landing_url"]:
                no_landing.append(entry)
            if r["confidence"] == "unverified":
                unverified.append(entry)
            if not r["last_reviewed"]:
                stale.append(entry)

        counties_present = {norm_county(c).lower()
                            for row in srcs for c in (row["county"] or "").split("/") if c.strip()}
        mentioned = counties_named_in_notes(st)
        missing_counties = sorted(
            {name: files for name, files in mentioned.items()
             if name.lower() not in counties_present}.items())

        docs_total, docs_with_text = con.execute(
            "SELECT COUNT(*), COALESCE(SUM(CASE WHEN n_chunks>0 THEN 1 ELSE 0 END),0) "
            "FROM documents d JOIN sources s ON s.id=d.source_id WHERE s.state=?",
            (st,)).fetchone()

        report["states"].append({
            "state": st,
            "sources": len(srcs),
            "by_level": dict(con.execute(
                "SELECT jurisdiction_level, COUNT(*) FROM sources WHERE state=? "
                "GROUP BY jurisdiction_level", (st,)).fetchall()),
            "documents": docs_total,
            "documents_with_harvested_text": docs_with_text,
            "permits": con.execute("SELECT COUNT(*) FROM permits WHERE state=?", (st,)).fetchone()[0],
            "sources_with_no_documents": no_docs,
            "sources_with_no_permits": no_permits,
            "sources_missing_landing_url": no_landing,
            "sources_unverified": unverified,
            "sources_never_reviewed": stale,
            "counties_with_records": sorted(
                {row["county"] for row in srcs if row["county"]}),
            "counties_named_in_research_notes_with_no_record": [
                {"county": name, "notes_file": files} for name, files in missing_counties],
        })

    def human(p):
        for s in p["states"]:
            print(hr(f"COVERAGE GAPS — {s['state']}"))
            print(f"  sources {s['sources']}  ({', '.join(f'{k}={v}' for k, v in s['by_level'].items()) or 'none'})")
            print(f"  documents {s['documents']}  "
                  f"(text harvested: {s['documents_with_harvested_text']})")
            print(f"  permits {s['permits']}")
            if s["sources"] == 0:
                print("  ** THIS STATE HAS NO REGISTRY RECORDS AT ALL. Any answer about it "
                      "would be a guess. **")
            def show(label, items, limit=12):
                if not items:
                    return
                print(f"\n  {label}: {len(items)}")
                for e in items[:limit]:
                    print(f"     - {e['id']}  ({e['jurisdiction']}, {e['level']})")
                if len(items) > limit:
                    print(f"     … {len(items) - limit} more")
            show("sources with NO documents", s["sources_with_no_documents"])
            show("sources with NO permits recorded", s["sources_with_no_permits"])
            show("sources missing landing_url", s["sources_missing_landing_url"])
            show("sources at confidence=unverified", s["sources_unverified"])
            show("sources never reviewed", s["sources_never_reviewed"])
            if s["documents"] and not s["documents_with_harvested_text"]:
                print("\n  ! NO document text harvested for this state — full-text search "
                      "(query.py search) cannot answer anything here yet.")
            miss = s["counties_named_in_research_notes_with_no_record"]
            if miss:
                print(f"\n  counties named in the research notes with NO registry record: "
                      f"{len(miss)}")
                print("     " + ", ".join(m["county"] for m in miss[:40]))
                if len(miss) > 40:
                    print(f"     … {len(miss) - 40} more")
            print(f"\n  counties WITH records ({len(s['counties_with_records'])}): "
                  + (", ".join(s["counties_with_records"]) or "NONE"))

    out(report, human, args.json)


# ------------------------------------------------------------------ people

def cmd_people(args, con) -> None:
    where, params = ["1=1"], []
    if args.state:
        where.append("state = ?"); params.append(args.state.upper())
    if args.jurisdiction:
        where.append("lower(jurisdiction_id) = ?"); params.append(args.jurisdiction.lower())
    if args.level:
        where.append("level = ?"); params.append(args.level)
    rows = con.execute(f"SELECT * FROM people WHERE {' AND '.join(where)} "
                       f"ORDER BY state, level, body, title", params).fetchall()
    items = []
    for r in rows:
        j = con.execute("SELECT jurisdiction_label FROM sources WHERE id=?",
                        (r["jurisdiction_id"],)).fetchone()
        items.append({
            "id": r["id"], "full_name": r["full_name"] or None,
            "title": r["title"], "body": r["body"], "role_type": r["role_type"],
            "department": r["department"] or None,
            "staff_or_decision_maker": r["staff_or_decision_maker"] or None,
            "state": r["state"], "level": r["level"],
            "jurisdiction_id": r["jurisdiction_id"],
            "jurisdiction_in_registry": bool(j),
            "jurisdiction_label": j["jurisdiction_label"] if j else None,
            "portfolio": jl(r["portfolio"]),
            "official_contact": jl(r["official_contact"]) or {},
            "confidence": r["confidence"], "last_reviewed": r["last_reviewed"] or None,
        })
    payload = {"filters": {"state": args.state, "jurisdiction": args.jurisdiction,
                           "level": args.level},
               "count": len(items), "people": items,
               "caveat": ("Records with confidence 'unverified' and no full_name are STRUCTURAL "
                          "PLACEHOLDERS for a seat/office, not claims about who holds it. Never "
                          "name an incumbent from these rows.")}

    def human(p):
        print(f"{p['count']} people record(s)")
        cur = None
        for it in p["people"]:
            key = (it["state"], it["level"], it["body"])
            if key != cur:
                cur = key
                print(hr(f"{it['state']} / {it['level']} / {it['body']}"))
            print(f"  {it['full_name'] or '(name UNVERIFIED — seat placeholder)'} — {it['title']}")
            print(f"      role={it['role_type']} {it['staff_or_decision_maker'] or ''} "
                  f"confidence={it['confidence']} jurisdiction={it['jurisdiction_id']}"
                  + ("" if it["jurisdiction_in_registry"] else "  [NOT in sources registry]"))
        if p["people"]:
            print("\n" + p["caveat"])

    out(payload, human, args.json)


# ------------------------------------------------------------------ cli

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="query.py", description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default=None, help="path to regbase.sqlite")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common_flags(p):
        p.add_argument("--json", action="store_true", help="machine-readable output")

    s = sub.add_parser("search", help="BM25 full-text search over harvested text")
    s.add_argument("query")
    s.add_argument("--state"); s.add_argument("--county"); s.add_argument("--muni")
    s.add_argument("--level", choices=LEVEL_ORDER)
    s.add_argument("--asset", action="append")
    s.add_argument("--doc-type", dest="doc_type")
    s.add_argument("-n", "--limit", type=int, default=10)
    common_flags(s); s.set_defaults(func=cmd_search)

    p = sub.add_parser("permits", help="permits applying to a jurisdiction")
    p.add_argument("--state"); p.add_argument("--county"); p.add_argument("--muni")
    p.add_argument("--level", choices=LEVEL_ORDER)
    p.add_argument("--asset", action="append")
    common_flags(p); p.set_defaults(func=cmd_permits)

    j = sub.add_parser("jurisdiction", help="full profile of one jurisdiction")
    j.add_argument("state"); j.add_argument("county", nargs="?")
    j.add_argument("municipality", nargs="?")
    common_flags(j); j.set_defaults(func=cmd_jurisdiction)

    k = sub.add_parser("stack", help="full federal->state->county->municipal permit stack")
    k.add_argument("--state", required=True)
    k.add_argument("--county")
    k.add_argument("--muni", action="append")
    k.add_argument("--asset", action="append")
    common_flags(k); k.set_defaults(func=cmd_stack)

    g = sub.add_parser("gaps", help="registry coverage holes")
    g.add_argument("--state")
    common_flags(g); g.set_defaults(func=cmd_gaps)

    pe = sub.add_parser("people", help="decision makers and staff")
    pe.add_argument("--state"); pe.add_argument("--jurisdiction")
    pe.add_argument("--level", choices=["federal", "state", "county", "municipal"])
    common_flags(pe); pe.set_defaults(func=cmd_people)
    return ap


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    con = open_db(args.db)
    try:
        args.func(args, con)
    except BrokenPipeError:                      # `| head`
        try:
            sys.stdout.close()
        except Exception:
            pass
    finally:
        con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
