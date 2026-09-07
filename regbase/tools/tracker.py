#!/usr/bin/env python3
"""Render a single-file HTML status tracker for the RegBase corpus.

Reads the two live sources of truth -- corpus/manifest.jsonl (appended as a
harvest runs) and corpus/regbase.sqlite (rewritten by build_index.py) -- and
writes a self-contained page. No server, no external assets, no network.

Because the manifest is appended during a harvest, regenerating this page
while one is running shows real progress. `--watch` does exactly that: it
rewrites the page on an interval, and the page reloads itself to match, so an
open browser tab tracks a running harvest.

  python3 regbase/tools/tracker.py --open
  python3 regbase/tools/tracker.py --watch 20        # refresh every 20s
  python3 regbase/tools/tracker.py -o "%USERPROFILE%/Desktop/regbase.html"
"""
from __future__ import annotations

import argparse
import html
import json
import os
import sqlite3
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

STATES = ["CO", "WY", "NM", "UT", "TX", "US"]
STATE_NAMES = {"CO": "Colorado", "WY": "Wyoming", "NM": "New Mexico",
               "UT": "Utah", "TX": "Texas", "US": "Federal"}


# ------------------------------------------------------------------ collect

def read_manifest() -> dict[str, dict]:
    try:
        return common.manifest_read()
    except Exception:
        return {}


def read_index() -> dict:
    """Index totals. Returns {} when the database has not been built yet."""
    if not common.INDEX_DB.exists():
        return {}
    try:
        con = sqlite3.connect(f"file:{common.INDEX_DB}?mode=ro", uri=True, timeout=5)
        con.row_factory = sqlite3.Row
        out: dict = {}
        for table in ("sources", "documents", "permits", "people", "chunks"):
            try:
                out[table] = con.execute(f"SELECT COUNT(*) n FROM {table}").fetchone()["n"]
            except sqlite3.Error:
                out[table] = 0
        try:
            out["meta"] = {r["key"]: r["value"] for r in con.execute("SELECT key, value FROM meta")}
        except sqlite3.Error:
            out["meta"] = {}
        try:
            out["chunks_by_state"] = {
                r["state"]: r["n"] for r in
                con.execute("SELECT state, COUNT(*) n FROM chunks GROUP BY state")}
        except sqlite3.Error:
            out["chunks_by_state"] = {}
        con.close()
        return out
    except sqlite3.Error as exc:
        return {"error": str(exc)}


def collect() -> dict:
    """Everything the page shows, as plain data."""
    sources = common.load_sources()
    manifest = read_manifest()
    index = read_index()

    per: dict[str, dict] = {s: {"sources": 0, "docs": 0, "ok": 0, "failed": 0,
                                "pending": 0, "crawl_only": 0, "chars": 0}
                            for s in STATES}
    failures: list[dict] = []
    seen_keys: set[str] = set()

    for src in sources:
        st = src.state.upper()
        row = per.setdefault(st, {"sources": 0, "docs": 0, "ok": 0, "failed": 0,
                                  "pending": 0, "crawl_only": 0, "chars": 0})
        row["sources"] += 1
        for doc in src.docs():
            if not doc.url:
                continue
            key = f"{src.id}::{doc.url}"
            seen_keys.add(key)
            row["docs"] += 1
            rec = manifest.get(key)
            if rec is None:
                # A municode landing page naming no node is skipped by design:
                # harvest.py routes it to --crawl. Counting it as pending work
                # would overstate what is left to fetch (27 of Colorado's docs).
                if "library.municode.com" in doc.url and "nodeId=" not in doc.url:
                    row["crawl_only"] += 1
                else:
                    row["pending"] += 1
                continue
            status = rec.get("http_status")
            if status == 200:
                row["ok"] += 1
                row["chars"] += int(rec.get("text_chars") or 0)
            else:
                row["failed"] += 1
                failures.append({
                    "state": st,
                    "status": status if status is not None else 0,
                    "url": rec.get("url") or doc.url,
                    "title": rec.get("title") or doc.title,
                    "jurisdiction": src.jurisdiction_label,
                })

    # Crawled pages are not registry documents; count them separately so the
    # per-state coverage bar stays an honest "of what the registry lists".
    crawled = 0
    crawled_chars = 0
    for key, rec in manifest.items():
        if key in seen_keys:
            continue
        crawled += 1
        crawled_chars += int(rec.get("text_chars") or 0)
        st = (rec.get("state") or "").upper()
        if st in per:
            per[st]["chars"] += int(rec.get("text_chars") or 0)

    by_status = Counter(f["status"] for f in failures)
    by_host = Counter(urlsplit(f["url"]).netloc for f in failures)

    # Thin extractions are the signal that caught every extractor bug so far:
    # a document that downloaded fine but produced almost no text.
    thin = [
        {"state": r.get("state"), "title": r.get("title") or "",
         "bytes": int(r.get("bytes") or 0), "chars": int(r.get("text_chars") or 0),
         "url": r.get("url") or ""}
        for r in manifest.values()
        if int(r.get("bytes") or 0) > 20000 and int(r.get("text_chars") or 0) < 300
        and r.get("http_status") == 200
    ]
    thin.sort(key=lambda d: -d["bytes"])

    recent = sorted(
        (r for r in manifest.values() if r.get("fetched_at")),
        key=lambda r: str(r.get("fetched_at")), reverse=True)[:12]

    return {
        "generated_at": datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z"),
        "per_state": per,
        "failures": failures,
        "by_status": by_status.most_common(),
        "by_host": by_host.most_common(10),
        "thin": thin,
        "recent": recent,
        "crawled": crawled,
        "crawled_chars": crawled_chars,
        "index": index,
        "manifest_records": len(manifest),
        "corpus_dir": str(common.CORPUS_DIR),
        "raw_dir": str(common.RAW_DIR),
    }


# ------------------------------------------------------------------- render

def _e(value) -> str:
    return html.escape(str(value), quote=True)


def _n(value) -> str:
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return "0"


def _status_label(status) -> str:
    if status in (0, None):
        return "unreachable"
    return str(status)


def render(data: dict, refresh: int) -> str:
    per = data["per_state"]
    idx = data["index"]
    meta = idx.get("meta", {}) if idx else {}

    totals = {k: sum(v[k] for v in per.values())
              for k in ("sources", "docs", "ok", "failed", "pending",
                        "crawl_only", "chars")}
    fetchable = totals["docs"] - totals["crawl_only"]
    pct = (totals["ok"] / fetchable * 100) if fetchable else 0.0

    refresh_tag = (f'<meta http-equiv="refresh" content="{refresh}">'
                   if refresh else "")

    rows = []
    for st in sorted(per, key=lambda s: (STATES.index(s) if s in STATES else 99, s)):
        v = per[st]
        if not v["docs"] and not v["sources"]:
            continue
        fetchable_st = v["docs"] - v["crawl_only"]
        got = v["ok"] / fetchable_st * 100 if fetchable_st else 0
        chunks = (idx.get("chunks_by_state", {}) or {}).get(st, 0)
        rows.append(f"""
      <tr>
        <td class="jur"><strong>{_e(st)}</strong><span class="muted"> {_e(STATE_NAMES.get(st, ''))}</span></td>
        <td class="num">{_n(v['sources'])}</td>
        <td class="num">{_n(v['docs'])}</td>
        <td class="num ok">{_n(v['ok'])}</td>
        <td class="num bad">{_n(v['failed']) if v['failed'] else '<span class="muted">0</span>'}</td>
        <td class="num warn">{_n(v['pending']) if v['pending'] else '<span class="muted">0</span>'}</td>
        <td class="num muted">{_n(v['crawl_only']) if v['crawl_only'] else '0'}</td>
        <td class="num">{_n(chunks)}</td>
        <td class="num">{_n(v['chars'])}</td>
        <td class="barcell">
          <div class="bar" title="{got:.0f}% of listed documents fetched">
            <span style="width:{got:.1f}%"></span>
          </div>
        </td>
      </tr>""")

    status_chips = "".join(
        f'<span class="chip s{_e(_status_label(s)).replace(" ", "-")}">'
        f'{_e(_status_label(s))} <b>{n}</b></span>'
        for s, n in data["by_status"]) or '<span class="muted">none</span>'

    host_rows = "".join(
        f'<tr><td class="mono">{_e(h or "—")}</td><td class="num">{n}</td></tr>'
        for h, n in data["by_host"]) or '<tr><td colspan="2" class="muted">none</td></tr>'

    fail_rows = "".join(
        f'<tr><td>{_e(f["state"])}</td>'
        f'<td><span class="chip s{_e(_status_label(f["status"])).replace(" ", "-")}">'
        f'{_e(_status_label(f["status"]))}</span></td>'
        f'<td>{_e(f["jurisdiction"])}</td>'
        f'<td class="mono trunc" title="{_e(f["url"])}">{_e(f["url"])}</td></tr>'
        for f in sorted(data["failures"], key=lambda f: (f["state"], str(f["status"]))))
    if not fail_rows:
        fail_rows = '<tr><td colspan="4" class="muted">No failures.</td></tr>'

    thin_rows = "".join(
        f'<tr><td>{_e(t["state"])}</td><td class="trunc" title="{_e(t["title"])}">{_e(t["title"])}</td>'
        f'<td class="num">{_n(t["bytes"])}</td><td class="num bad">{_n(t["chars"])}</td></tr>'
        for t in data["thin"][:14])
    if not thin_rows:
        thin_rows = '<tr><td colspan="4" class="muted">Nothing suspicious.</td></tr>'

    recent_rows = "".join(
        f'<tr><td class="mono nowrap">{_e(str(r.get("fetched_at"))[:19].replace("T", " "))}</td>'
        f'<td>{_e(r.get("state") or "")}</td>'
        f'<td class="trunc" title="{_e(r.get("title") or "")}">{_e(r.get("title") or "")}</td>'
        f'<td class="num">{_n(r.get("text_chars"))}</td></tr>'
        for r in data["recent"])
    if not recent_rows:
        recent_rows = '<tr><td colspan="4" class="muted">Nothing harvested yet.</td></tr>'

    built = meta.get("built_at", "")
    built_note = (f'index built {_e(str(built)[:19].replace("T", " "))} UTC'
                  if built else '<span class="warn-text">index not built yet</span>')
    stale = ""
    if built and data["manifest_records"]:
        try:
            b = datetime.fromisoformat(str(built).replace("Z", "+00:00"))
            newest = max((str(r.get("fetched_at") or "") for r in data["recent"]), default="")
            if newest:
                n = datetime.fromisoformat(newest.replace("Z", "+00:00"))
                if n > b:
                    stale = ('<div class="banner">The manifest has newer fetches than the '
                             'index. Run <code>build_index.py --rebuild</code> to pick them up.</div>')
        except (ValueError, TypeError):
            pass

    # A full document, not a fragment: this file is opened straight from disk,
    # and without an explicit charset the browser guesses the encoding and
    # mangles every dash and section symbol in the page.
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>RegBase Tracker</title>
{refresh_tag}
<style>
  img {{ max-width:100%; }}
  :root {{
    --bg:#f6f7f9; --panel:#ffffff; --ink:#15181d; --muted:#6b7280;
    --line:#e3e6ea; --ok:#0f7b3f; --bad:#b3261e; --warn:#8a5a00;
    --accent:#1f4e79; --bar:#d7dde5; --barfill:#2f6fab;
  }}
  @media (prefers-color-scheme: dark) {{
    :root:not([data-theme="light"]) {{
      --bg:#101317; --panel:#171b21; --ink:#e6e9ee; --muted:#9aa3af;
      --line:#262c34; --ok:#5fd08a; --bad:#ff8a80; --warn:#e0b355;
      --accent:#8ab4e8; --bar:#262c34; --barfill:#4a8fd0;
    }}
  }}
  :root[data-theme="dark"] {{
    --bg:#101317; --panel:#171b21; --ink:#e6e9ee; --muted:#9aa3af;
    --line:#262c34; --ok:#5fd08a; --bad:#ff8a80; --warn:#e0b355;
    --accent:#8ab4e8; --bar:#262c34; --barfill:#4a8fd0;
  }}
  body {{ background:var(--bg); color:var(--ink); font:14px/1.5 -apple-system,
         "Segoe UI", Roboto, Helvetica, Arial, sans-serif; margin:0; padding:22px; }}
  .wrap {{ max-width:1180px; margin:0 auto; }}
  h1 {{ font-size:19px; margin:0 0 2px; letter-spacing:-.01em; }}
  h2 {{ font-size:13px; text-transform:uppercase; letter-spacing:.07em;
        color:var(--muted); margin:26px 0 8px; font-weight:600; }}
  .sub {{ color:var(--muted); font-size:12.5px; margin-bottom:18px; }}
  .cards {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:10px; }}
  .card {{ background:var(--panel); border:1px solid var(--line); border-radius:9px; padding:13px 15px; }}
  .card .k {{ color:var(--muted); font-size:11.5px; text-transform:uppercase; letter-spacing:.05em; }}
  .card .v {{ font-size:23px; font-weight:650; margin-top:3px; letter-spacing:-.02em;
              font-variant-numeric:tabular-nums; }}
  .card .n {{ color:var(--muted); font-size:11.5px; margin-top:2px; }}
  .panel {{ background:var(--panel); border:1px solid var(--line);
            border-radius:9px; overflow:auto; }}
  table {{ width:100%; border-collapse:collapse; font-size:13px; }}
  th {{ text-align:left; font-weight:600; color:var(--muted); font-size:11.5px;
        text-transform:uppercase; letter-spacing:.05em; padding:9px 11px;
        border-bottom:1px solid var(--line); white-space:nowrap; }}
  td {{ padding:8px 11px; border-bottom:1px solid var(--line); vertical-align:top; }}
  tr:last-child td {{ border-bottom:none; }}
  .num {{ text-align:right; font-variant-numeric:tabular-nums; white-space:nowrap; }}
  .mono {{ font-family:ui-monospace, SFMono-Regular, Consolas, monospace; font-size:12px; }}
  .muted {{ color:var(--muted); font-weight:400; }}
  .ok {{ color:var(--ok); }} .bad {{ color:var(--bad); }} .warn {{ color:var(--warn); }}
  .warn-text {{ color:var(--warn); }}
  .nowrap {{ white-space:nowrap; }}
  .trunc {{ max-width:520px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
  .jur {{ white-space:nowrap; }}
  .barcell {{ width:150px; }}
  .bar {{ background:var(--bar); border-radius:4px; height:8px; width:140px; overflow:hidden; }}
  .bar span {{ display:block; height:100%; background:var(--barfill); border-radius:4px; }}
  .chip {{ display:inline-block; padding:1px 7px; border-radius:20px; font-size:11.5px;
           border:1px solid var(--line); margin-right:5px; font-variant-numeric:tabular-nums; }}
  .chip.s403, .chip.s404, .chip.sunreachable {{ color:var(--bad); }}
  .cols {{ display:grid; grid-template-columns:1fr 1fr; gap:14px; align-items:start; }}
  @media (max-width:820px) {{ .cols {{ grid-template-columns:1fr; }} }}
  .banner {{ background:var(--panel); border:1px solid var(--warn); border-left-width:3px;
             border-radius:7px; padding:9px 12px; margin:14px 0; font-size:13px; }}
  code {{ font-family:ui-monospace, SFMono-Regular, Consolas, monospace; font-size:12px; }}
  footer {{ color:var(--muted); font-size:11.5px; margin-top:26px; padding-top:12px;
            border-top:1px solid var(--line); }}
</style>
</head>
<body>

<div class="wrap">
  <h1>RegBase corpus tracker</h1>
  <div class="sub">
    {_e(data['generated_at'])} &middot; {built_note}
    {' &middot; auto-refresh ' + str(refresh) + 's' if refresh else ''}
  </div>
  {stale}

  <div class="cards">
    <div class="card"><div class="k">Coverage</div><div class="v">{pct:.0f}%</div>
      <div class="n">{_n(totals['ok'])} of {_n(fetchable)} fetchable docs</div></div>
    <div class="card"><div class="k">Chunks</div><div class="v">{_n(idx.get('chunks', 0))}</div>
      <div class="n">searchable passages</div></div>
    <div class="card"><div class="k">Text</div><div class="v">{_n(totals['chars'] // 1000)}k</div>
      <div class="n">characters extracted</div></div>
    <div class="card"><div class="k">Sources</div><div class="v">{_n(idx.get('sources', totals['sources']))}</div>
      <div class="n">{_n(idx.get('permits', 0))} permits &middot; {_n(idx.get('people', 0))} people</div></div>
    <div class="card"><div class="k">Failed</div><div class="v bad">{_n(totals['failed'])}</div>
      <div class="n">{_n(totals['pending'])} pending &middot; {_n(totals['crawl_only'])} crawl-only</div></div>
    <div class="card"><div class="k">Crawled</div><div class="v">{_n(data['crawled'])}</div>
      <div class="n">pages beyond the registry</div></div>
  </div>

  <h2>By jurisdiction</h2>
  <div class="panel"><table>
    <tr><th>State</th><th class="num">Sources</th><th class="num">Docs</th>
        <th class="num">OK</th><th class="num">Failed</th><th class="num">Pending</th>
        <th class="num" title="Municode landing pages with no nodeId: fetched by --crawl, not documents mode">Crawl-only</th>
        <th class="num">Chunks</th><th class="num">Chars</th><th>Coverage</th></tr>
    {''.join(rows)}
  </table></div>

  <h2>Failures &middot; {status_chips}</h2>
  <div class="cols">
    <div class="panel"><table>
      <tr><th>State</th><th>Status</th><th>Jurisdiction</th><th>URL</th></tr>
      {fail_rows}
    </table></div>
    <div>
      <div class="panel"><table>
        <tr><th>Host</th><th class="num">Fails</th></tr>
        {host_rows}
      </table></div>
      <h2>Thin extractions</h2>
      <div class="panel"><table>
        <tr><th>St</th><th>Document</th><th class="num">Bytes</th><th class="num">Chars</th></tr>
        {thin_rows}
      </table></div>
    </div>
  </div>

  <h2>Recent fetches</h2>
  <div class="panel"><table>
    <tr><th>Fetched</th><th>St</th><th>Title</th><th class="num">Chars</th></tr>
    {recent_rows}
  </table></div>

  <footer>
    manifest {_n(data['manifest_records'])} records &middot;
    corpus <code>{_e(data['corpus_dir'])}</code> &middot;
    raw <code>{_e(data['raw_dir'])}</code><br>
    Regenerate with <code>py regbase\\tools\\tracker.py</code>.
    Thin extractions are documents that downloaded fine but yielded almost no
    text &mdash; the signal that has caught every extractor bug so far.
  </footer>
</div>
</body>
</html>
"""


# --------------------------------------------------------------------- main

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    default_out = Path(os.path.expanduser("~")) / "Desktop" / "RegBase-tracker.html"
    ap.add_argument("-o", "--out", default=str(default_out),
                    help=f"output HTML path (default: {default_out})")
    ap.add_argument("--watch", type=int, metavar="SECONDS", default=0,
                    help="rewrite on this interval until interrupted; the page "
                         "reloads itself to match")
    ap.add_argument("--open", action="store_true", help="open the page when done")
    ap.add_argument("--json", action="store_true", help="print the data as JSON and exit")
    args = ap.parse_args(argv)

    if args.json:
        data = collect()
        data["by_status"] = [[str(s), n] for s, n in data["by_status"]]
        print(json.dumps(data, indent=1, default=str))
        return 0

    out = Path(os.path.expandvars(args.out)).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)

    def write_once() -> dict:
        data = collect()
        out.write_text(render(data, args.watch), encoding="utf-8")
        return data

    data = write_once()
    print(f"wrote {out}")
    if args.open:
        try:
            os.startfile(str(out))              # noqa: SIM105  (Windows only)
        except (AttributeError, OSError):
            import webbrowser
            webbrowser.open(out.as_uri())

    if args.watch:
        print(f"watching every {args.watch}s — Ctrl+C to stop")
        try:
            while True:
                time.sleep(args.watch)
                data = write_once()
                idx = data["index"]
                print(f"  {datetime.now().strftime('%H:%M:%S')}  "
                      f"manifest={data['manifest_records']}  chunks={idx.get('chunks', 0)}")
        except KeyboardInterrupt:
            print("\nstopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
