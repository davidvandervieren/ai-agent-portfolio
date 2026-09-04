#!/usr/bin/env python3
"""watch_agendas.py — early warning: find regulatory changes BEFORE adoption.

RegBase change-monitoring, half two. ``check_updates.py`` tells you a rule
already moved; by then a midstream project is re-planning against a fait
accompli. This tool watches the meeting pipeline — agendas, packets, and
minutes of the bodies that adopt land-use codes, 1041 regulations, setbacks,
moratoria, and ROW/franchise terms — and flags items whose text touches oil &
gas midstream while they are still pending.

    python3 regbase/tools/watch_agendas.py --state CO --days 45
    python3 regbase/tools/watch_agendas.py --dry-run --state WY

HOW TARGETS ARE FOUND
---------------------
1. ``update_watch.check_urls`` on sources whose ``update_watch.method`` is
   ``agenda_scan`` (the explicit opt-in).
2. ``documents[]`` entries with ``doc_type: agenda`` or ``meeting_minutes``.
3. Any ``landing_url`` / ``check_urls`` / document URL whose host matches a
   known meeting-management platform (table below).
4. Everything else that *should* have an agenda feed but doesn't yet — every
   county/municipal source with no agenda target — is emitted as a
   **discovery queue** in the report, with the exact playbook search patterns
   to run. A jurisdiction we cannot watch is itself a finding.

PLATFORM PATTERN TABLE
----------------------
Detection (host/path markers) is reliable: it comes from
``regbase/people/collection_playbook.md`` step 2 and from the URL shapes the
platforms themselves publish. The *listing endpoints* are a different matter —
several are private/AJAX APIs whose exact shape could not be confirmed in this
environment (no outbound network). Anything not confirmed is carried with
``verified=False`` and is used only as a **candidate** URL: the tool tries it,
and on a non-200 falls back to the human-facing page it was derived from,
rather than asserting the endpoint is correct. See ``PLATFORMS`` below; every
entry carries an inline note about what is and is not verified.

WHAT COUNTS AS A HIT
--------------------
Agenda/minutes text is keyword-scanned for the midstream permitting
vocabulary in ``KEYWORDS`` (oil, gas, pipeline, midstream, compressor,
produced/saltwater water, injection, disposal, flowline, gathering, setback,
1041, special use, land use code amendment, moratorium, zoning text
amendment, right-of-way, franchise). Each hit records the jurisdiction,
meeting date, body, the agenda item text around the match, and a link.

OUTPUT
------
``corpus/reports/agenda_watch_<YYYY-MM-DD>.md``  (plus ``--json`` to stdout).

Same discipline as ``check_updates.py``: ``--dry-run`` makes zero network
calls and prints exactly what would be fetched; a blocked egress path exits
non-zero with actionable instructions instead of hundreds of failures.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import urlsplit, urljoin

sys.path.insert(0, str(Path(__file__).resolve().parent))

import common  # noqa: E402
from common import CORPUS_DIR, Source, egress_ok, load_sources, now_iso  # noqa: E402
from check_updates import (  # noqa: E402
    EGRESS_HELP,
    _tolerate_sigpipe,
    decode_body,
    normalize_html,
    strip_html_volatiles,
)

REPORTS_DIR = CORPUS_DIR / "reports"

# --------------------------------------------------------------- platforms

@dataclass
class Platform:
    key: str
    label: str
    host_markers: tuple[str, ...]
    path_markers: tuple[str, ...]
    listing: str = ""          # template, {host}/{scheme}/{client} substituted
    verified: bool = False     # True only if the endpoint shape is confirmed
    note: str = ""


PLATFORMS: list[Platform] = [
    Platform(
        key="legistar", label="Legistar (Granicus)",
        host_markers=("legistar.com",),
        path_markers=("calendar.aspx", "meetingdetail.aspx", "legislationdetail.aspx"),
        # The human-facing calendar page is a stable, publicly documented URL
        # shape for every Legistar client site.
        listing="{scheme}://{host}/Calendar.aspx", verified=True,
        note="UNVERIFIED alternative: the Legistar Web API at "
             "https://webapi.legistar.com/v1/<client>/events with OData "
             "$filter/$top params. The base path is widely used, but the exact "
             "filter syntax and whether a given client exposes it publicly was "
             "NOT confirmed in this environment — not used automatically.",
    ),
    Platform(
        key="granicus", label="Granicus ViewPublisher",
        host_markers=("granicus.com",),
        path_markers=("viewpublisher.php", "mediaplayer.php", "agendaviewer.php"),
        # view_id is jurisdiction-specific and cannot be guessed; we only reuse
        # a view_id already present in the configured URL.
        listing="{url}", verified=True,
        note="ViewPublisher.php?view_id=<n> is the standard public listing page, "
             "but view_id MUST come from the jurisdiction's own site. This tool "
             "never invents one — it reuses the URL as configured. "
             "UNVERIFIED: the Granicus Open Platform REST API "
             "(/api/v2/...) shape and public availability.",
    ),
    Platform(
        key="civicplus", label="CivicPlus Agenda Center",
        # NOTE: civiclive.com / revize.com are file CDNs used by these vendors,
        # not app hosts — matching on them would synthesize bogus /AgendaCenter
        # URLs on a CDN, so they are deliberately NOT host markers here.
        host_markers=("civicplus.com",),
        path_markers=("/agendacenter", "/agendacenter/search"),
        listing="{scheme}://{host}/AgendaCenter", verified=True,
        note="/AgendaCenter is the standard CivicPlus module path. "
             "UNVERIFIED: the RSS variant /RSSFeed.aspx?ModID=<n>&CID=<n> — "
             "ModID/CID are per-site and were not confirmed; not used.",
    ),
    Platform(
        key="civicclerk", label="CivicClerk / CivicPlus Meetings",
        host_markers=("civicclerk.com",),
        path_markers=("/web/portal", "/web/home"),
        listing="{scheme}://{host}/Web/Portal.aspx", verified=False,
        note="UNVERIFIED: newer CivicClerk portals are a JS app backed by a "
             "/api/v1/Meetings JSON endpoint whose exact path/params were not "
             "confirmed. Treated as a candidate only; falls back to the "
             "configured URL on any non-200.",
    ),
    Platform(
        key="novusagenda", label="NovusAgenda",
        host_markers=("novusagenda.com",),
        path_markers=("/agendapublic", "displayagendapublic.aspx", "meetingview.aspx"),
        listing="{scheme}://{host}/agendapublic/", verified=False,
        note="UNVERIFIED: /agendapublic/ is the usual public root and "
             "MeetingView.aspx?MeetingID=<n> the usual item page, but the "
             "default landing document varies by tenant. Candidate only.",
    ),
    Platform(
        key="boarddocs", label="BoardDocs",
        host_markers=("boarddocs.com",),
        path_markers=("/board.nsf", "/public"),
        listing="{url}", verified=False,
        note="UNVERIFIED: BoardDocs renders meetings via XHR POSTs to "
             "Board.nsf/BD-GetMeetingsList?open (and BD-GetAgenda?open). "
             "Shape not confirmed here; this tool only scans the public "
             "landing page it was given and reports low coverage.",
    ),
    Platform(
        key="municode_meetings", label="Municode Meetings",
        host_markers=("meetings.municode.com",),
        path_markers=("/meeting", "/citydocuments"),
        listing="{url}", verified=False,
        note="UNVERIFIED: meetings.municode.com/<client>/meeting/ appears to be "
             "the public listing, backed by a JSON API. Neither confirmed; the "
             "configured URL is scanned as-is.",
    ),
    Platform(
        key="primegov", label="PrimeGov",
        host_markers=("primegov.com",),
        path_markers=("/public/portal", "/portal"),
        listing="{scheme}://{host}/public/portal", verified=False,
        note="UNVERIFIED: PrimeGov portals are a JS app; a "
             "/api/v2/PublicPortal/ListArchivedMeetings-style endpoint is "
             "referenced in the wild but was not confirmed. Candidate only.",
    ),
    Platform(
        key="iqm2", label="IQM2 / Accela Legislative Management",
        host_markers=("iqm2.com",),
        path_markers=("/citizens/", "/detail_meeting.aspx"),
        listing="{scheme}://{host}/Citizens/Calendar.aspx", verified=False,
        note="UNVERIFIED endpoint shape; IQM2 is legacy Accela and many tenants "
             "have migrated to Legistar. Candidate only.",
    ),
    Platform(
        key="escribe", label="eSCRIBE",
        host_markers=("escribemeetings.com", "esolutionsgroup.ca"),
        path_markers=("/meeting.aspx", "/filestream.ashx"),
        listing="{url}", verified=False,
        note="UNVERIFIED. Configured URL scanned as-is.",
    ),
    Platform(
        key="selfhosted", label="Self-hosted / clerk page",
        host_markers=(),
        path_markers=("/agenda", "/agendas", "/minutes", "/meetings",
                      "/boards-and-commissions", "/commission-meetings",
                      "/agendas-and-minutes", "/agendas-minutes"),
        listing="{url}", verified=True,
        note="Plain .gov agenda/minutes page — scanned directly, no API assumed.",
    ),
]


def detect_platform(url: str) -> Optional[Platform]:
    parts = urlsplit(url.lower())
    host, path = parts.netloc, parts.path + ("?" + parts.query if parts.query else "")
    for p in PLATFORMS:
        if any(h in host for h in p.host_markers):
            return p
    for p in PLATFORMS:
        if p.host_markers:
            continue
        if any(m in path for m in p.path_markers):
            return p
    return None


def listing_url(platform: Platform, url: str) -> str:
    """Derive the listing URL. A host-template is only applied when the URL's
    HOST is the platform's own app host; matching on a path marker alone means
    we are looking at a plain .gov page, so the configured URL is used as-is
    rather than synthesizing an endpoint that may not exist."""
    parts = urlsplit(url)
    if platform.host_markers and not any(h in parts.netloc.lower()
                                         for h in platform.host_markers):
        return url
    try:
        return platform.listing.format(scheme=parts.scheme or "https",
                                       host=parts.netloc, url=url)
    except (KeyError, IndexError):
        return url


# --------------------------------------------------------------- keywords

KEYWORDS: dict[str, str] = {
    # label -> regex
    "oil & gas": r"\boil\s*(?:&|and)?\s*gas\b|\boil\b(?=[^.]{0,40}\bgas\b)",
    "pipeline": r"\bpipe\s?lines?\b",
    "midstream": r"\bmidstream\b",
    "compressor": r"\bcompress(?:or|ion)\s*(?:station|facilit\w+)?\b",
    "produced/saltwater water": r"\bproduced\s+water\b|\bsalt\s?water\b|\bSWD\b|\bbrine\b",
    "injection": r"\binjection\s*(?:well|permit)?\b|\bClass\s*II\b|\bUIC\b",
    "disposal": r"\bdisposal\s*(?:well|facilit\w+|site)?\b",
    "flowline": r"\bflow\s?lines?\b",
    "gathering": r"\bgathering\s*(?:line|system|pipeline)?\b",
    "setback": r"\bset\s?backs?\b",
    "1041": r"\b1041\b|\bareas?\s+and\s+activities\s+of\s+state\s+interest\b",
    "special use": r"\bspecial\s+(?:use|review)\b|\bconditional\s+use\b|\bUSR\b|\bSUP\b",
    "land use code amendment": r"\bland\s+use\s+(?:code|regulation)s?\s+amendment\b"
                               r"|\bamend\w*\s+the\s+land\s+use\s+code\b|\bLUC\s+amendment\b",
    "moratorium": r"\bmoratori(?:um|a)\b",
    "zoning text amendment": r"\bzoning\s+(?:text|code|ordinance)\s+amendment\b"
                             r"|\btext\s+amendment\b|\brezon\w+\b",
    "right-of-way": r"\bright[\s-]?of[\s-]?ways?\b|\bROW\b|\beasements?\b",
    "franchise": r"\bfranchise\b",
    "well pad / tank battery": r"\bwell\s?pads?\b|\btank\s+batter(?:y|ies)\b",
    "gas processing": r"\bgas\s+processing\b|\bprocessing\s+plant\b",
    "operator agreement": r"\boperator\s+agreement\b|\bmemorandum\s+of\s+understanding\b",
}
_COMPILED = {k: re.compile(v, re.I) for k, v in KEYWORDS.items()}

# strong signals — a hit on any of these is high priority even alone
HIGH_SIGNAL = {"midstream", "flowline", "gathering", "compressor", "1041",
               "produced/saltwater water", "injection", "moratorium",
               "land use code amendment", "setback"}

_DATE_RE = re.compile(
    r"\b(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4}"
    r"|\d{1,2}/\d{1,2}/\d{2,4}"
    r"|\d{4}-\d{2}-\d{2})\b", re.I)

_BODY_RE = re.compile(
    r"\b((?:board\s+of\s+county\s+commissioners|county\s+commission(?:ers)?|"
    r"commissioners?\s+court|city\s+council|town\s+council|town\s+board|"
    r"planning\s+(?:and\s+zoning\s+)?commission|planning\s+commission|"
    r"board\s+of\s+adjustment|zoning\s+board|city\s+commission|"
    r"board\s+of\s+trustees|county\s+council))\b", re.I)


# --------------------------------------------------------------- targets

@dataclass
class AgendaTarget:
    url: str
    source_id: str
    state: str
    jurisdiction: str
    level: str
    title: str
    platform: str
    platform_label: str
    platform_verified: bool
    fetch_url: str
    origin: str


@dataclass
class Hit:
    source_id: str
    state: str
    jurisdiction: str
    body: str
    meeting_date: str
    keywords: list[str]
    snippet: str
    link: str
    listing_url: str
    high_signal: bool = False


def plan_targets(sources: list[Source]) -> tuple[list[AgendaTarget], list[Source]]:
    """Return (agenda targets, sources needing platform discovery)."""
    targets: list[AgendaTarget] = []
    seen: set[tuple[str, str]] = set()

    def add(src: Source, url: str, title: str, origin: str) -> bool:
        url = (url or "").strip()
        if not url.lower().startswith(("http://", "https://")):
            return False
        plat = detect_platform(url)
        if plat is None:
            return False
        key = (src.id, url)
        if key in seen:
            return False
        seen.add(key)
        targets.append(AgendaTarget(
            url=url, source_id=src.id, state=src.state,
            jurisdiction=src.jurisdiction_label, level=src.jurisdiction_level,
            title=title, platform=plat.key, platform_label=plat.label,
            platform_verified=plat.verified, fetch_url=listing_url(plat, url),
            origin=origin))
        return True

    needs_discovery: list[Source] = []
    for src in sources:
        uw = src.update_watch or {}
        found = False
        if (uw.get("method") or "") == "agenda_scan":
            for u in uw.get("check_urls") or []:
                found |= add(src, u, f"{src.name} — agenda_scan watch URL", "agenda_scan")
        for d in src.docs():
            if d.doc_type in ("agenda", "meeting_minutes"):
                found |= add(src, d.url, d.title, f"document:{d.doc_type}")
        for u in uw.get("check_urls") or []:
            found |= add(src, u, f"{src.name} — watch URL", "check_urls")
        if src.landing_url:
            found |= add(src, src.landing_url, f"{src.name} — landing page", "landing_url")
        for d in src.docs():
            found |= add(src, d.url, d.title, "document")
        if not found and src.jurisdiction_level in ("county", "municipal", "special_district"):
            needs_discovery.append(src)
    targets.sort(key=lambda t: (t.state, t.jurisdiction, t.url))
    return targets, needs_discovery


# --------------------------------------------------------------- scanning

def _links(base_url: str, markup: str) -> list[tuple[str, str]]:
    out = []
    for m in re.finditer(r"<a\b[^>]*href\s*=\s*[\"']([^\"'#]+)[\"'][^>]*>(.*?)</a>",
                         markup, re.S | re.I):
        href, label = m.group(1).strip(), re.sub(r"<[^>]+>", " ", m.group(2))
        label = re.sub(r"\s+", " ", label).strip()
        if href.lower().startswith(("mailto:", "javascript:", "tel:")):
            continue
        out.append((urljoin(base_url, href), label))
    return out


def scan_text(text: str, target: AgendaTarget, link: str, days: int) -> list[Hit]:
    """Keyword-scan already-extracted text, one Hit per matching line/paragraph."""
    hits: list[Hit] = []
    cutoff = date.today() - timedelta(days=days)
    body_guess = ""
    bm = _BODY_RE.search(text[:4000])
    if bm:
        body_guess = bm.group(1).title()
    for para in [p.strip() for p in text.split("\n") if p.strip()]:
        if len(para) < 12:
            continue
        matched = [k for k, rx in _COMPILED.items() if rx.search(para)]
        if not matched:
            continue
        # a lone "right-of-way"/"franchise"/"rezoning" hit with nothing else is
        # usually unrelated municipal business — require corroboration
        if not (set(matched) & HIGH_SIGNAL) and len(matched) < 2:
            continue
        mdate = ""
        dm = _DATE_RE.search(para) or _DATE_RE.search(text[:2000])
        if dm:
            mdate = dm.group(0)
            parsed = _parse_date(mdate)
            if parsed and parsed < cutoff:
                continue
        pbody = _BODY_RE.search(para)
        hits.append(Hit(
            source_id=target.source_id, state=target.state,
            jurisdiction=target.jurisdiction,
            body=(pbody.group(1).title() if pbody else body_guess) or "(body not stated)",
            meeting_date=mdate or "(date not stated)",
            keywords=sorted(matched), snippet=para[:400],
            link=link, listing_url=target.fetch_url,
            high_signal=bool(set(matched) & HIGH_SIGNAL),
        ))
    return hits


def _parse_date(raw: str) -> Optional[date]:
    for fmt in ("%B %d, %Y", "%b %d, %Y", "%B %d %Y", "%b %d %Y",
                "%m/%d/%Y", "%m/%d/%y", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw.replace(".", ""), fmt).date()
        except ValueError:
            continue
    return None


def _dedupe(hits: list[Hit]) -> list[Hit]:
    seen, out = set(), []
    for h in hits:
        key = (h.source_id, h.link, h.snippet[:120])
        if key in seen:
            continue
        seen.add(key)
        out.append(h)
    return out


def scan_target(target: AgendaTarget, fetcher, days: int, follow: int) -> tuple[list[Hit], str]:
    """Fetch a listing page, scan it, then scan up to `follow` linked documents."""
    r = fetcher.get(target.fetch_url)
    status = getattr(r, "status_code", 0)
    if status >= 400 or status == 0:
        # unverified endpoints get one fallback attempt at the configured URL
        if target.fetch_url != target.url:
            r = fetcher.get(target.url)
            status = getattr(r, "status_code", 0)
        if status >= 400 or status == 0:
            return [], f"HTTP {status} {getattr(r, 'reason', '')}".strip()

    raw = getattr(r, "content", b"") or b""
    ctype = (getattr(r, "headers", {}) or {}).get("Content-Type", "")
    markup = decode_body(raw, ctype)
    text = normalize_html(markup)
    hits = scan_text(text, target, target.fetch_url, days)

    # follow agenda/packet/minutes links found on the listing page
    followed = 0
    for href, label in _links(target.fetch_url, strip_html_volatiles(markup)):
        if followed >= follow:
            break
        low = (href + " " + label).lower()
        if not any(w in low for w in ("agenda", "packet", "minutes", "meeting",
                                      "legislationdetail", "meetingdetail")):
            continue
        if href == target.fetch_url:
            continue
        rr = fetcher.get(href)
        if getattr(rr, "status_code", 0) != 200:
            continue
        followed += 1
        sub_raw = getattr(rr, "content", b"") or b""
        sub_ct = (getattr(rr, "headers", {}) or {}).get("Content-Type", "")
        if "pdf" in sub_ct.lower() or href.lower().endswith(".pdf") or sub_raw[:5] == b"%PDF-":
            from check_updates import extract_pdf_text, scrub_text_volatiles
            sub_text = scrub_text_volatiles(extract_pdf_text(sub_raw))
        else:
            sub_text = normalize_html(decode_body(sub_raw, sub_ct))
        if sub_text:
            hits.extend(scan_text(sub_text, target, href, days))
    return _dedupe(hits), ""


# --------------------------------------------------------------- reporting

DISCOVERY_QUERIES = [
    '"<body name>" agenda granicus',
    '"<body name>" legistar agenda',
    '"<body name>" "agenda center" civicplus',
    '"<body name>" novusagenda',
    '"<body name>" boarddocs',
    '"<body name>" municode meetings',
    '"<county name>" clerk and recorder meeting minutes search',
]


def render_markdown(hits: list[Hit], targets: list[AgendaTarget],
                    errors: list[tuple[AgendaTarget, str]],
                    discovery: list[Source], args) -> str:
    today = date.today().isoformat()
    L: list[str] = []
    L.append(f"# RegBase agenda watch — {today}")
    L.append("")
    scope = ", ".join(s.upper() for s in (args.state or [])) or "all states"
    L.append(f"*Generated {now_iso()} · scope: {scope} · look-back "
             f"{args.days} days · {len(targets)} agenda target(s) scanned*")
    L.append("")
    L.append("Pending items only — these are **proposals**, not adopted rules. "
             "Confirm against the jurisdiction's own posted packet before "
             "relying on any of it.")
    L.append("")
    L.append("| | count |")
    L.append("|---|---:|")
    L.append(f"| High-signal hits | {sum(1 for h in hits if h.high_signal)} |")
    L.append(f"| Total hits | {len(hits)} |")
    L.append(f"| Agenda targets scanned | {len(targets)} |")
    L.append(f"| Targets erroring | {len(errors)} |")
    L.append(f"| Jurisdictions with no agenda source yet | {len(discovery)} |")
    L.append("")

    if hits:
        L.append("## Hits")
        L.append("")
        for st in sorted({h.state for h in hits}):
            L.append(f"### {st}")
            L.append("")
            rows = [h for h in hits if h.state == st]
            for juris in sorted({h.jurisdiction for h in rows}):
                L.append(f"#### {juris}")
                L.append("")
                jrows = sorted([h for h in rows if h.jurisdiction == juris],
                               key=lambda h: (not h.high_signal, h.meeting_date))
                for h in jrows:
                    flag = " :rotating_light:" if h.high_signal else ""
                    L.append(f"- **{h.meeting_date} — {h.body}**{flag}")
                    L.append(f"  - Keywords: {', '.join('`' + k + '`' for k in h.keywords)}")
                    L.append(f"  - Item: {h.snippet}")
                    L.append(f"  - Link: <{h.link}>")
                    L.append(f"  - Source record: `{h.source_id}`")
                    L.append("")
            L.append("")
    else:
        L.append("## Hits")
        L.append("")
        L.append("_No agenda items matched the midstream keyword set in this window._")
        L.append("")

    if errors:
        L.append("## Targets that could not be scanned")
        L.append("")
        L.append("| state | jurisdiction | platform | verified endpoint? | error | url |")
        L.append("|---|---|---|---|---|---|")
        for t, err in errors:
            L.append(f"| {t.state} | {t.jurisdiction} | {t.platform_label} | "
                     f"{'yes' if t.platform_verified else 'NO (candidate)'} | {err} | "
                     f"<{t.fetch_url}> |")
        L.append("")

    if discovery:
        L.append("## Discovery queue — jurisdictions with no agenda source")
        L.append("")
        L.append("These county/municipal sources have no agenda or minutes URL in "
                 "`regbase/sources/*.yaml`, so nothing pending can be seen for them. "
                 "For each, run the `collection_playbook.md` step-2 queries below, "
                 "then add the result as `documents: [{doc_type: agenda, ...}]` or as "
                 "`update_watch: {method: agenda_scan, check_urls: [...]}`.")
        L.append("")
        L.append("Query patterns (substitute the body/county name):")
        L.append("")
        for q in DISCOVERY_QUERIES:
            L.append(f"- `{q}`")
        L.append("")
        L.append("| state | jurisdiction | source id | landing url |")
        L.append("|---|---|---|---|")
        for s in sorted(discovery, key=lambda s: (s.state, s.jurisdiction_label))[:args.discovery_limit]:
            L.append(f"| {s.state} | {s.jurisdiction_label} | `{s.id}` | "
                     f"{('<' + s.landing_url + '>') if s.landing_url else '—'} |")
        if len(discovery) > args.discovery_limit:
            L.append(f"| … | _{len(discovery) - args.discovery_limit} more elided_ | | |")
        L.append("")

    L.append("---")
    L.append("")
    L.append("### Platform coverage notes")
    L.append("")
    L.append("| platform | listing endpoint | confirmed? |")
    L.append("|---|---|---|")
    for p in PLATFORMS:
        L.append(f"| {p.label} | `{p.listing or '(as configured)'}` | "
                 f"{'yes' if p.verified else '**no — candidate only**'} |")
    L.append("")
    L.append("Endpoints marked *candidate only* were not confirmed against a live "
             "service; the tool tries them and falls back to the configured URL. "
             "See the `PLATFORMS` table in `watch_agendas.py` for per-platform notes.")
    L.append("")
    return "\n".join(L) + "\n"


# --------------------------------------------------------------- cli

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="watch_agendas.py",
        description="Scan meeting agendas/minutes for pending midstream-relevant items.")
    p.add_argument("--state", action="append", default=[],
                   help="limit to a state (CO/WY/NM/UT/TX/US); repeatable")
    p.add_argument("--source-id", action="append", default=[],
                   help="limit to a specific source id; repeatable")
    p.add_argument("--days", type=int, default=45,
                   help="only consider meetings dated within N days (default 45)")
    p.add_argument("--limit", type=int, default=0, help="max agenda targets to scan")
    p.add_argument("--follow", type=int, default=6,
                   help="max linked agendas/packets to open per listing (default 6)")
    p.add_argument("--dry-run", action="store_true",
                   help="list exactly what would be fetched; makes no network calls")
    p.add_argument("--delay", type=float, default=2.0,
                   help="per-host politeness delay in seconds (default 2.0)")
    p.add_argument("--json", action="store_true", help="machine-readable JSON to stdout")
    p.add_argument("--no-egress-check", action="store_true")
    p.add_argument("--discovery-limit", type=int, default=60,
                   help="max rows in the discovery queue table (default 60)")
    p.add_argument("--reports-dir", default=str(REPORTS_DIR))
    return p


def main(argv: Optional[list[str]] = None) -> int:
    _tolerate_sigpipe()
    args = build_parser().parse_args(argv)

    sources = load_sources()
    states = {s.upper() for s in args.state}
    ids = set(args.source_id)
    if states:
        sources = [s for s in sources if s.state in states]
    if ids:
        sources = [s for s in sources if s.id in ids]

    targets, discovery = plan_targets(sources)
    if args.limit:
        targets = targets[:args.limit]

    if args.dry_run:
        plan = {
            "tool": "watch_agendas.py", "mode": "dry-run", "generated": now_iso(),
            "filters": {"state": sorted(states), "source_id": sorted(ids),
                        "days": args.days, "limit": args.limit or None},
            "delay_seconds": args.delay, "follow_per_listing": args.follow,
            "would_fetch_listings": len(targets),
            "would_follow_up_to": len(targets) * args.follow,
            "keywords": sorted(KEYWORDS),
            "targets": [t.__dict__ for t in targets],
            "needs_platform_discovery": [
                {"source_id": s.id, "state": s.state,
                 "jurisdiction": s.jurisdiction_label, "landing_url": s.landing_url}
                for s in discovery],
        }
        if args.json:
            print(json.dumps(plan, indent=1))
            return 0
        print(f"DRY RUN — would fetch {len(targets)} agenda listing(s), following up "
              f"to {args.follow} linked documents each "
              f"(<= {len(targets) * args.follow} extra requests), "
              f"{args.delay}s per-host delay. No network calls made.")
        print()
        if targets:
            hdr = f"{'STATE':<6} {'PLATFORM':<20} {'VERIFIED':<9} {'ORIGIN':<22} URL"
            print(hdr)
            print("-" * len(hdr))
            for t in targets:
                print(f"{t.state:<6} {t.platform_label[:20]:<20} "
                      f"{('yes' if t.platform_verified else 'candidate'):<9} "
                      f"{t.origin[:22]:<22} {t.fetch_url}")
        else:
            print("No agenda targets: no source in scope has an agenda/minutes URL "
                  "or a recognized meeting-platform host.")
        print()
        print(f"{len(discovery)} county/municipal source(s) in scope need agenda "
              f"platform discovery (see the report's discovery queue).")
        for s in discovery[:15]:
            print(f"  - [{s.state}] {s.jurisdiction_label} ({s.id})"
                  + (f" — {s.landing_url}" if s.landing_url else ""))
        if len(discovery) > 15:
            print(f"  ... and {len(discovery) - 15} more")
        print()
        print(f"keywords scanned: {', '.join(sorted(KEYWORDS))}")
        print(f"report would be written to: {args.reports_dir}/agenda_watch_"
              f"{date.today().isoformat()}.md")
        return 0

    if not args.no_egress_check and not egress_ok():
        print(EGRESS_HELP.replace("check_updates.py", "watch_agendas.py"), file=sys.stderr)
        return 2

    fetcher = common.Fetcher(delay=args.delay)
    hits: list[Hit] = []
    errors: list[tuple[AgendaTarget, str]] = []
    for i, t in enumerate(targets, 1):
        if not args.json:
            print(f"[{i}/{len(targets)}] {t.fetch_url}", file=sys.stderr)
        got, err = scan_target(t, fetcher, args.days, args.follow)
        if err:
            errors.append((t, err))
        hits.extend(got)
    hits = _dedupe(hits)

    reports = Path(args.reports_dir)
    reports.mkdir(parents=True, exist_ok=True)
    out = reports / f"agenda_watch_{date.today().isoformat()}.md"
    out.write_text(render_markdown(hits, targets, errors, discovery, args))

    if args.json:
        print(json.dumps({
            "tool": "watch_agendas.py", "generated": now_iso(),
            "targets_scanned": len(targets), "hits": [h.__dict__ for h in hits],
            "errors": [{"url": t.fetch_url, "error": e} for t, e in errors],
            "needs_platform_discovery": [s.id for s in discovery],
            "report": str(out),
        }, indent=1))
    else:
        print(f"\nhits {len(hits)} ({sum(1 for h in hits if h.high_signal)} high-signal) "
              f"· targets {len(targets)} · errors {len(errors)}")
        print(f"report: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
