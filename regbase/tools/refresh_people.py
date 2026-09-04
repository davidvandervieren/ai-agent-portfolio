#!/usr/bin/env python3
"""refresh_people.py — build the prioritized research queue for the people layer.

DIVISION OF LABOR (read this before changing anything here)
-----------------------------------------------------------
This tool does **not** scrape, search, or collect anything about any person.
It never touches the network. It is a *queue builder*:

    refresh_people.py                  ->  reads regbase/people/people.seed.yaml
                                           + regbase/sources/*.yaml
                                       ->  finds records that are stale or
                                           unverified
                                       ->  writes corpus/reports/
                                           people_refresh_queue_<date>.md

    a Claude research subagent         ->  reads that queue, one entry at a
                                           time, and performs the actual
                                           web research for that one seat,
                                           following
                                           regbase/people/collection_playbook.md

    a human / the same agent           ->  edits regbase/people/people.seed.yaml
                                           per regbase/people/refresh_task.md's
                                           "How to diff" rules

The split exists because the research half needs judgment (is this the agency's
own roster page or a cached mirror? do two sources conflict?) that a scraper
cannot exercise, and because the ethics boundary in
``regbase/people/README.md`` has to be enforced in the *instruction* the
researcher reads, not in a post-hoc filter. Each queue entry is therefore a
complete, standalone, ready-to-run prompt: it names the seat, the
jurisdiction, the official URLs already known from the sources layer, exactly
which fields are missing, the playbook query patterns to use, and — verbatim,
in every single prompt — the collection prohibitions.

STALENESS
---------
A record is queued when either:
  * ``confidence: unverified`` (always — an unverified record is a placeholder,
    not data), or
  * ``last_reviewed`` is older than ``--stale-days`` (default 90, matching the
    quarterly cadence in ``refresh_task.md``), or missing/unparseable.

PRIORITY
--------
Ranked by leverage over midstream permitting, highest first:
  1. decision-makers (``staff_or_decision_maker: decides``) over staff;
  2. bodies whose ``portfolio`` covers midstream project types;
  3. state oil & gas regulators and county land-use bodies over everything else;
  4. most stale first.

    python3 regbase/tools/refresh_people.py --stale-days 90
    python3 regbase/tools/refresh_people.py --state CO --limit 10 --json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import CORPUS_DIR, PEOPLE_DIR, ROOT, load_sources, now_iso  # noqa: E402
from check_updates import _tolerate_sigpipe  # noqa: E402

SEED = PEOPLE_DIR / "people.seed.yaml"
REPORTS_DIR = CORPUS_DIR / "reports"

MIDSTREAM_PORTFOLIO = {
    "midstream_pipeline", "produced_water_line", "swd_well", "compressor_station",
    "gas_processing_plant", "tank_battery", "metering", "well_pad",
    "access_road", "water_crossing", "electrical_line", "temporary_workspace",
}

# fields the researcher is expected to try to fill, and what each needs
FIELD_GUIDE: dict[str, str] = {
    "full_name": "the current holder of this seat, confirmed on the body's own roster page",
    "official_contact.office_url": "the agency's own page for this seat/office",
    "official_contact.office_phone": "office phone as published BY THE AGENCY",
    "official_contact.office_email": "office email as published BY THE AGENCY",
    "term_start": "term start date (elected/appointed seats)",
    "term_end": "term end date (elected/appointed seats)",
    "next_election": "next election date (elected seats only)",
    "public_positions": "dated, sourced public statements on midstream-relevant matters",
    "voting_record": "per-member votes on midstream-relevant matters, from minutes",
    "decision_patterns": "observed approval rate (with denominator + window), common "
                         "conditions imposed, typical questions, hot buttons",
    "process_notes": "submittal format, pre-application meeting requirement, typical "
                     "review time, known completeness pitfalls",
    "campaign_finance": "public filing URL — ELECTED officials only",
    "review_source_urls": "every URL actually opened this run",
}

# Verbatim ethics boundary — regbase/people/README.md. This block is embedded in
# EVERY generated prompt; do not shorten it, and do not make it conditional.
ETHICS_BLOCK = """\
### Collection boundary — binding, not advisory

COLLECT ONLY public, professional, ROLE-RELATED information:
  * official title, agency/body, term dates;
  * public voting record and published decisions (votes, orders, dockets);
  * public meeting statements — minutes, agendas, staff reports, testimony;
  * official contact information PUBLISHED BY THE AGENCY ITSELF (office phone,
    office email, agency web page, office mailing address);
  * public campaign-finance filings, for ELECTED officials only, and only facts
    stated in the filing itself.

NEVER collect, infer, store, or mention that you saw any of the following —
regardless of how easy it is to find, how relevant it seems, or who asks:
  * home address, personal phone, or personal email;
  * family members or personal relationships;
  * health, religion, or any other personal/protected characteristic;
  * non-public financial data (anything beyond what a public campaign-finance
    filing itself discloses);
  * anything scraped or inferred from a PERSONAL (non-official-capacity) social
    media account.

If a search result surfaces one of these, discard it, do not quote it, do not
note that it exists, and move on. `regbase/schemas/person.schema.json` is
`additionalProperties: false` — there is no field for any of it, and none may
be added.

This data exists to understand institutional decision-making patterns and
process. It must never be used to contact, pressure, or attempt to influence a
public official outside the normal public process, nor to build a profile of an
official for any other purpose. Consult counsel before any outreach informed by
this data.

### Never guess

If you cannot confirm a fact against a public source you actually opened this
run, DO NOT write it in. Leave the field out, keep `confidence: unverified`,
and add a one-line note in `review_source_urls` pointing at what you did find.
A wrong name in this system is worse than a blank one. Every URL you record
must be pasted verbatim from a tool result — never typed from memory, never
reconstructed by pattern-matching a domain name.
"""


# --------------------------------------------------------------- loading

def load_people(path: Path = SEED) -> list[dict]:
    if not path.exists():
        raise SystemExit(f"{path} not found")
    data = yaml.safe_load(path.read_text()) or []
    if isinstance(data, dict):                     # tolerate {people: [...]}
        data = data.get("people") or data.get("records") or []
    return [r for r in data if isinstance(r, dict) and r.get("id")]


def _parse_day(value) -> Optional[date]:
    if not value:
        return None
    if isinstance(value, date):
        return value
    try:
        return datetime.fromisoformat(str(value).strip().strip('"')).date()
    except ValueError:
        return None


# --------------------------------------------------------------- queue items

@dataclass
class QueueItem:
    person_id: str
    jurisdiction_id: str
    state: str
    level: str
    body: str
    title: str
    role_type: str
    confidence: str
    last_reviewed: str
    age_days: Optional[int]
    reasons: list[str]
    missing_fields: list[str]
    priority: int
    official_urls: list[str] = field(default_factory=list)
    source_name: str = ""
    source_missing: bool = False
    portfolio: list[str] = field(default_factory=list)
    department: str = ""
    appointed_by: str = ""


def missing_fields(rec: dict) -> list[str]:
    out: list[str] = []
    contact = rec.get("official_contact") or {}
    for fld in FIELD_GUIDE:
        if fld.startswith("official_contact."):
            if not contact.get(fld.split(".", 1)[1]):
                out.append(fld)
            continue
        if fld == "next_election" and rec.get("role_type") != "elected":
            continue
        if fld == "campaign_finance" and rec.get("role_type") != "elected":
            continue
        if fld in ("term_start", "term_end") and rec.get("role_type") == "career_staff":
            continue
        if not rec.get(fld):
            out.append(fld)
    return out


def score(rec: dict, age_days: Optional[int]) -> int:
    p = 0
    if (rec.get("confidence") or "unverified") == "unverified":
        p += 60
    elif rec.get("confidence") == "probable":
        p += 20
    if (rec.get("staff_or_decision_maker") or "") == "decides":
        p += 40
    if set(rec.get("portfolio") or []) & MIDSTREAM_PORTFOLIO:
        p += 25
    if rec.get("level") in ("state", "county"):
        p += 15
    if rec.get("role_type") == "elected":
        p += 10
    p += min(int((age_days or 0) / 30) * 5, 40)
    return p


def build_queue(people: list[dict], sources_by_id: dict, stale_days: int,
                states: set[str], levels: set[str], today: Optional[date] = None
                ) -> list[QueueItem]:
    today = today or date.today()
    items: list[QueueItem] = []
    for rec in people:
        if states and (rec.get("state") or "").upper() not in states:
            continue
        if levels and (rec.get("level") or "") not in levels:
            continue
        reviewed = _parse_day(rec.get("last_reviewed"))
        age = (today - reviewed).days if reviewed else None
        conf = (rec.get("confidence") or "unverified").lower()

        reasons: list[str] = []
        if conf == "unverified":
            reasons.append("confidence: unverified (placeholder, never confirmed)")
        elif conf == "probable":
            reasons.append("confidence: probable (not confirmed on the agency's own page)")
        if age is None:
            reasons.append("last_reviewed missing or unparseable")
        elif age >= stale_days:
            reasons.append(f"last_reviewed {age} day(s) ago (>= --stale-days {stale_days})")
        if not reasons:
            continue

        src = sources_by_id.get(rec.get("jurisdiction_id") or "")
        urls: list[str] = []
        source_name = ""
        if src is not None:
            source_name = src.name
            if src.landing_url:
                urls.append(src.landing_url)
            for c in src.contacts or []:
                if isinstance(c, dict) and c.get("url"):
                    urls.append(c["url"])
            for u in (src.update_watch or {}).get("check_urls") or []:
                urls.append(u)
            for d in src.docs():
                if d.doc_type in ("agenda", "meeting_minutes") and d.url:
                    urls.append(d.url)
        seen, uniq = set(), []
        for u in urls:
            if u not in seen:
                seen.add(u)
                uniq.append(u)

        items.append(QueueItem(
            person_id=rec["id"], jurisdiction_id=rec.get("jurisdiction_id", ""),
            state=(rec.get("state") or "").upper(), level=rec.get("level", ""),
            body=rec.get("body", ""), title=rec.get("title", ""),
            role_type=rec.get("role_type", ""), confidence=conf,
            last_reviewed=str(rec.get("last_reviewed") or ""), age_days=age,
            reasons=reasons, missing_fields=missing_fields(rec),
            priority=score(rec, age), official_urls=uniq[:8],
            source_name=source_name, source_missing=src is None,
            portfolio=list(rec.get("portfolio") or []),
            department=rec.get("department", "") or "",
            appointed_by=rec.get("appointed_by", "") or "",
        ))
    items.sort(key=lambda i: (-i.priority, i.state, i.body, i.title))
    return items


# --------------------------------------------------------------- prompt text

def _query_title(title: str) -> str:
    """Strip the seed file's parenthetical caveats so query strings stay usable.

    e.g. "County Commissioner (board seat/district to verify)" -> "County Commissioner"
    """
    cleaned = re.sub(r"\s*\([^)]*\)", "", title or "").strip(" -—,")
    return cleaned or (title or "").strip()


def render_prompt(item: QueueItem, stale_days: int) -> str:
    urls = ("\n".join(f"  - {u}" for u in item.official_urls)
            if item.official_urls
            else "  - (none recorded in regbase/sources/"
                 f"{item.jurisdiction_id or '?'} — find the body's own roster page "
                 "first, per playbook step 1, and record what you open)")
    fields = "\n".join(f"  - `{f}` — {FIELD_GUIDE[f]}" for f in item.missing_fields) \
        or "  - (all schema fields populated; re-confirm the name and term dates only)"
    body = item.body or "(body not recorded)"
    who = f"{item.title} — {body}"

    return f"""\
**Task: refresh RegBase person record `{item.person_id}`**

You are refreshing ONE seat in the RegBase people layer. Work only on this
seat. Do not batch other records into this run.

**Seat:** {who}
**Jurisdiction:** {item.state} · {item.level} · sources-layer id `{item.jurisdiction_id or '(unlinked)'}`{
'  ⚠️ this jurisdiction_id does not resolve to any record in regbase/sources/*.yaml — note that in your summary' if item.source_missing else f' ({item.source_name})'}
**Role type:** {item.role_type or 'unknown'}{f' · appointed by {item.appointed_by}' if item.appointed_by else ''}{f' · department: {item.department}' if item.department else ''}
**Current confidence:** {item.confidence} · **last_reviewed:** {item.last_reviewed or '(none)'}{f' ({item.age_days} days ago)' if item.age_days is not None else ''}
**Why it is queued:** {'; '.join(item.reasons)}

**Official URLs already known for this jurisdiction — start here:**
{urls}

**Fields to fill (leave any you cannot confirm EMPTY):**
{fields}

**Procedure** — follow `regbase/people/collection_playbook.md` steps 1-7 in
order. Use these query patterns, substituting the body/jurisdiction name above:
  - `"{body}" commissioners OR members OR roster current site:.gov`
  - `"{body}" staff directory OR leadership OR "org chart"`
  - `"{body}" {_query_title(item.title)} appointed OR elected {date.today().year}`
  - `"{body}" agenda granicus OR legistar OR "agenda center" OR novusagenda OR boarddocs`
  - `"{body}" minutes approved "compressor station" OR "gathering line" OR "produced water" OR "special use"`
  - `"{body}" staff report conditions of approval midstream OR pipeline`
Only the body's OWN page (step 1) supports `confidence: verified`. A dated news
article naming the holder supports `probable` and nothing more.

If you record `decision_patterns.approval_rate_observed`, it must be reproducible
from `evidence_urls` and written with its denominator and window, e.g.
`"7/9 (78%) midstream-related matters approved, regular agenda, Jan 2024-Dec 2025"`
— never a bare percentage. Say so explicitly if n < 5.

**Write-back** — per `regbase/people/refresh_task.md` "How to diff": never
overwrite a `verified` name on a single conflicting source (move it to
`probable`, cite both URLs, and flag it for a human instead); append to, never
replace, `public_positions` / `voting_record` / `decision_patterns.evidence_urls`;
set `last_reviewed` to today ({date.today().isoformat()}) even if nothing
changed, and append every URL you opened to `review_source_urls`.

{ETHICS_BLOCK}"""


# --------------------------------------------------------------- report

def render_markdown(items: list[QueueItem], all_count: int, args) -> str:
    today = date.today().isoformat()
    L: list[str] = []
    L.append(f"# RegBase people refresh queue — {today}")
    L.append("")
    scope = ", ".join(sorted(s.upper() for s in (args.state or []))) or "all states"
    L.append(f"*Generated {now_iso()} · scope: {scope} · threshold: "
             f"--stale-days {args.stale_days} · {len(items)} of {all_count} "
             f"person record(s) queued*")
    L.append("")
    L.append("This file is a **work queue for a research agent**, not a dataset. "
             "`refresh_people.py` collected nothing about anyone; it read "
             "`regbase/people/people.seed.yaml`, found the records that are stale "
             "or unverified, and wrote one ready-to-run research prompt per seat. "
             "Work them top to bottom — they are ordered by leverage over "
             "midstream permitting decisions. Each prompt is standalone: paste it "
             "into a fresh subagent, one seat per run.")
    L.append("")

    if not items:
        L.append("**Nothing is due.** Every person record in scope is within the "
                 f"{args.stale_days}-day review window and none is `unverified`.")
        L.append("")
        return "\n".join(L) + "\n"

    by_state: dict[str, int] = {}
    by_conf: dict[str, int] = {}
    for i in items:
        by_state[i.state] = by_state.get(i.state, 0) + 1
        by_conf[i.confidence] = by_conf.get(i.confidence, 0) + 1
    L.append("| dimension | breakdown |")
    L.append("|---|---|")
    L.append("| by state | " + ", ".join(f"{k}={v}" for k, v in sorted(by_state.items())) + " |")
    L.append("| by confidence | " + ", ".join(f"{k}={v}" for k, v in sorted(by_conf.items())) + " |")
    L.append(f"| decision-makers | {sum(1 for i in items if i.priority >= 100)} high-priority |")
    L.append(f"| unlinked jurisdiction_id | {sum(1 for i in items if i.source_missing)} |")
    L.append("")

    L.append("## Work order")
    L.append("")
    L.append("| # | pri | state | body | seat | confidence | last reviewed |")
    L.append("|---:|---:|---|---|---|---|---|")
    for n, i in enumerate(items, 1):
        L.append(f"| {n} | {i.priority} | {i.state} | {i.body} | {i.title} | "
                 f"{i.confidence} | {i.last_reviewed or '—'} |")
    L.append("")
    L.append("---")
    L.append("")
    L.append("## Prompts")
    L.append("")
    for n, i in enumerate(items, 1):
        L.append(f"### {n}. `{i.person_id}` — {i.title}, {i.body} ({i.state})")
        L.append("")
        L.append(render_prompt(i, args.stale_days))
        L.append("")
        L.append("---")
        L.append("")
    return "\n".join(L) + "\n"


# --------------------------------------------------------------- cli

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="refresh_people.py",
        description="Build the prioritized research queue for the RegBase people layer. "
                    "Makes no network calls and collects nothing itself.")
    p.add_argument("--stale-days", type=int, default=90,
                   help="queue records whose last_reviewed is at least this old "
                        "(default 90; 0 queues everything)")
    p.add_argument("--state", action="append", default=[],
                   help="limit to a state; repeatable")
    p.add_argument("--level", action="append", default=[],
                   help="limit to federal/state/county/municipal/special_district/tribal")
    p.add_argument("--limit", type=int, default=0, help="max queue entries to emit")
    p.add_argument("--seed", default=str(SEED), help=f"people file (default {SEED})")
    p.add_argument("--json", action="store_true", help="machine-readable JSON to stdout")
    p.add_argument("--dry-run", action="store_true",
                   help="summarize the queue without writing the report file")
    p.add_argument("--reports-dir", default=str(REPORTS_DIR))
    return p


def main(argv: Optional[list[str]] = None) -> int:
    _tolerate_sigpipe()
    args = build_parser().parse_args(argv)

    people = load_people(Path(args.seed))
    sources_by_id = {s.id: s for s in load_sources()}
    items = build_queue(people, sources_by_id, args.stale_days,
                        {s.upper() for s in args.state}, set(args.level))
    total = len(items)
    if args.limit:
        items = items[:args.limit]

    payload = {
        "tool": "refresh_people.py",
        "generated": now_iso(),
        "collects_nothing": True,
        "seed": str(Path(args.seed)),
        "people_records": len(people),
        "queued": total,
        "emitted": len(items),
        "filters": {"stale_days": args.stale_days,
                    "state": sorted(s.upper() for s in args.state),
                    "level": sorted(args.level), "limit": args.limit or None},
        "queue": [dict(i.__dict__) for i in items],
    }

    if args.json:
        print(json.dumps(payload, indent=1))
    if args.dry_run:
        if not args.json:
            print(f"DRY RUN — {total} of {len(people)} person record(s) would be "
                  f"queued (stale-days {args.stale_days}); no file written.")
            for n, i in enumerate(items[:20], 1):
                print(f"  {n:>3}. pri {i.priority:>3} [{i.state}] {i.title} — "
                      f"{i.body} ({'; '.join(i.reasons)})")
            if len(items) > 20:
                print(f"  ... and {len(items) - 20} more")
        return 0

    reports = Path(args.reports_dir)
    reports.mkdir(parents=True, exist_ok=True)
    out = reports / f"people_refresh_queue_{date.today().isoformat()}.md"
    out.write_text(render_markdown(items, len(people), args))
    if not args.json:
        print(f"people records read: {len(people)}  ({Path(args.seed)})")
        print(f"queued for refresh:  {total}"
              + (f" (emitting first {len(items)})" if args.limit else ""))
        print(f"queue written to:    {out}")
        print()
        print("Next: hand each prompt in that file to a research subagent, one "
              "seat per run, then write results back per "
              "regbase/people/refresh_task.md. This tool collected nothing itself.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
