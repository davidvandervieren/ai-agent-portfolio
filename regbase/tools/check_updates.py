#!/usr/bin/env python3
"""check_updates.py — detect when a jurisdiction's regulations actually changed.

RegBase change-monitoring, half one: the *already adopted* half.  Given the
source registry in ``regbase/sources/*.yaml`` this walks every watched URL,
issues a polite conditional GET through :class:`common.Fetcher`, and reports
which regulatory documents moved since the last run — with a unified diff of
the extracted text, so a reviewer sees the regulatory language that changed
rather than a bare "this page is different".

    python3 regbase/tools/check_updates.py --cadence weekly
    python3 regbase/tools/check_updates.py --state CO --limit 20 --dry-run

WHAT GETS WATCHED
-----------------
For each source, in order:

1. ``update_watch.check_urls`` when present — the curated watch list.
2. Otherwise ``landing_url`` plus every ``documents[].url`` — the fallback,
   so a source with no ``update_watch`` block is still monitored.

Identical URLs shared by several sources are fetched **once** and attributed
to every source that references them.

CHANGE SIGNALS, AND WHY THEY ARE RANKED THE WAY THEY ARE
--------------------------------------------------------
1. **HTTP 304 Not Modified** — the cheapest and most trustworthy signal.  We
   send ``If-None-Match``/``If-Modified-Since`` from stored state; a 304 ends
   the check with zero body transfer and zero risk of a false positive.
2. **ETag / Last-Modified delta** — recorded as a corroborating signal, and
   used as the *authoritative* signal only when the body cannot be normalized
   into text (e.g. a scanned image-only PDF).
3. **sha256 of the NORMALIZED body** — authoritative for everything else.

Deliberate deviation from a naive reading of "ETag delta beats hash": ETags
rotate constantly for reasons that have nothing to do with content (load
balancer swap, gzip level, CDN re-encode, CMS republish of an unchanged page,
weak-vs-strong validator differences).  Treating an ETag delta as "changed"
generates weekly noise on hundreds of URLs.  So when the ETag or
Last-Modified moved but the normalized content hash did **not**, this tool
records ``metadata_only`` on the state row and reports the URL as UNCHANGED.
The reverse — hash moved, ETag did not — is always reported as CHANGED.

NORMALIZATION RULES (the part that decides whether this tool is signal or noise)
-------------------------------------------------------------------------------
Hashing raw bytes produces a "change" on essentially every run of every
government CMS.  Before hashing, the body is reduced to stable text:

HTML / XHTML / XML
  * ``<!-- ... -->`` comments removed (build stamps, cache tags, CDN
    debug blocks, conditional comments all live here).
  * ``<script>``, ``<style>``, ``<noscript>``, ``<template>`` elements removed
    *with their contents* — inline analytics payloads, JSON blobs with request
    ids, and CSS build hashes are pure noise.
  * Volatile attributes stripped wherever they appear: ``nonce``,
    ``integrity``, ``crossorigin`` fingerprints, ``data-csrf*``,
    ``data-nonce``, ``data-token``, ``data-timestamp``, ``data-request-id``,
    ``data-build``, ``data-session*``.
  * Hidden form fields whose name/id matches ASP.NET view-state and CSRF
    machinery removed entirely: ``__VIEWSTATE``, ``__VIEWSTATEGENERATOR``,
    ``__EVENTVALIDATION``, ``__RequestVerificationToken``,
    ``authenticity_token``, anything containing ``csrf``/``nonce``/``session``.
  * ``<meta>`` tags carrying ``csrf-token``, ``request-id``, ``build``,
    ``generated``, ``nonce`` removed.
  * Cache-busting and session query strings normalized out of ``src``/``href``:
    ``?v=``, ``?ver=``, ``?rev=``, ``?cb=``, ``?_=``, ``?t=``, ``?nocache=``,
    ``jsessionid=``, ``phpsessid=``, ``sid=``, plus bare hex fingerprints.
  * Remaining tags dropped, entities unescaped.

Sitemaps / feeds
  * ``<lastmod>``, ``<lastBuildDate>``, ``<generator>``, ``<atom:updated>``
    (channel-level rotating markers) are dropped before text extraction.
    Item-level ``pubDate`` is KEPT — a new item genuinely is a change.

PDF
  * Text is extracted (pdfminer.six, falling back to pypdf) and the *text* is
    hashed, never the bytes.  PDF producers rewrite ``/CreationDate``,
    ``/ModDate``, ``/ID``, and object numbering on every regeneration, so byte
    hashing reports a change every time a clerk re-exports an unchanged rule.
  * If no text can be extracted (scanned/image-only PDF), the tool falls back
    to hashing bytes, marks the row ``normalizer: pdf_bytes`` and
    ``noisy: true``, and the report annotates the finding as low-confidence.

JSON (ArcGIS / REST endpoints)
  * Re-serialized with sorted keys after dropping volatile top-level keys
    (``timestamp``, ``generated``, ``requestId``, ``serverTime``, ``currentVersion``…).

Text-level scrubbing applied to every format after the above
  * Clock times (``3:04 PM``, ``15:04:05``) removed — never regulatory content.
  * Full ISO-8601 datetimes removed.
  * Dates removed **only when adjacent to a volatility marker**: "last
    updated / last modified / last reviewed / generated / printed / retrieved /
    accessed / current as of / page updated / © ".  A bare date is PRESERVED,
    on purpose: "effective January 15, 2021" is exactly the regulatory fact
    this system exists to notice moving.  This is the one place the tool
    chooses a possible false positive over a possible false negative.
  * Render-time counters removed: "page generated in 0.013 seconds", "query
    took …", "execution time …".
  * Visitor/hit/view counters removed ("Visitors: 12,345", "1,234 views").
  * Digit runs of 10+ (epoch ms, request ids) → ``<NUM>``; hex runs of 16+ and
    UUIDs → ``<HEX>`` — these are rotating ad/session/build markers.
  * Whitespace collapsed.  Two products come out of this: ``diff_text``
    (line structure preserved, for the unified diff) and ``hash_text``
    (fully collapsed, for the sha256).  The hash is taken over ``hash_text``
    so that pure re-wrapping never registers as a change.

STATE
-----
``corpus/watch_state.json``, keyed by check URL:
``sha256, etag, last_modified, last_checked, last_changed, http_status,
consecutive_error_count, normalizer, source_ids, bytes, metadata_only``.

OUTPUT
------
``corpus/reports/updates_<YYYY-MM-DD>.md``   — human, grouped by state then
jurisdiction, changed items first, with truncated unified diffs.
``corpus/reports/updates_<YYYY-MM-DD>.json`` — machine, same content.

The diff baseline is, in order: the extracted-text copy under ``corpus/text/``
written by ``harvest.py`` (preferred — it is the curated corpus the reviewer
already knows), else this tool's own previous snapshot under
``corpus/watch_text/``.  A fresh snapshot is always written afterwards, so
diffs work even when harvest has never run.
"""
from __future__ import annotations

import argparse
import difflib
import html as _html
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Iterable, Optional
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))

import common  # noqa: E402
from common import (  # noqa: E402
    CORPUS_DIR,
    ROOT,
    TEXT_DIR,
    Source,
    egress_ok,
    load_sources,
    manifest_read,
    now_iso,
    sha256_bytes,
    slugify,
)

WATCH_STATE = CORPUS_DIR / "watch_state.json"
REPORTS_DIR = CORPUS_DIR / "reports"
SNAPSHOT_DIR = CORPUS_DIR / "watch_text"
MAX_DIFF_LINES = 200
STATE_VERSION = 1

# --------------------------------------------------------------- normalization

_RE_COMMENT = re.compile(r"<!--.*?-->", re.S)
_RE_CDATA = re.compile(r"<!\[CDATA\[.*?\]\]>", re.S)
_RE_DROP_ELEMENT = re.compile(
    r"<\s*(script|style|noscript|template|svg)\b[^>]*>.*?<\s*/\s*\1\s*>", re.S | re.I
)
_RE_DROP_SELFCLOSED = re.compile(r"<\s*(script|style)\b[^>]*/?>", re.I)

# rotating channel-level feed / sitemap markers
_RE_FEED_MARKERS = re.compile(
    r"<\s*(lastmod|lastBuildDate|generator|atom:updated|sy:updatePeriod|sy:updateFrequency)\b[^>]*>"
    r".*?<\s*/\s*\1\s*>",
    re.S | re.I,
)

_VOLATILE_ATTR = re.compile(
    r"""\s(?:nonce|integrity|data-nonce|data-csrf[\w-]*|data-token|data-timestamp|
        data-request-id|data-requestid|data-build|data-session[\w-]*|data-cache[\w-]*|
        data-ts|data-time|data-version|data-hash)\s*=\s*("[^"]*"|'[^']*'|[^\s>]+)""",
    re.I | re.X,
)

_HIDDEN_TOKEN_INPUT = re.compile(
    r"<input\b[^>]*(?:__VIEWSTATE|__EVENTVALIDATION|__VIEWSTATEGENERATOR|"
    r"__EVENTTARGET|__EVENTARGUMENT|__RequestVerificationToken|authenticity_token|"
    r"csrf|nonce|session|_token)[^>]*>",
    re.I,
)

_VOLATILE_META = re.compile(
    r"<meta\b[^>]*(?:csrf|nonce|request-id|requestid|build[-_]?id|generated|"
    r"page-render|x-ua-timestamp)[^>]*>",
    re.I,
)

_CACHE_BUST_QS = re.compile(
    r"[?&](?:v|ver|version|rev|cb|_|t|ts|time|nocache|cache|bust|rand|r|hash|fp)"
    r"=[^\"'\s>&]{1,64}",
    re.I,
)
_SESSION_QS = re.compile(
    r"[;?&](?:jsessionid|phpsessid|aspsessionid[\w]*|sid|sessionid|session_id|"
    r"cfid|cftoken|utm_[a-z_]+)=[^\"'\s>&;]{1,120}",
    re.I,
)
_HEX_FINGERPRINT_QS = re.compile(r"[?&][a-z0-9_-]{1,12}=[0-9a-f]{16,}", re.I)

_RE_TAG = re.compile(r"<[^>]+>")

# ---- text-level scrubbers -------------------------------------------------

_MONTHS = (
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|"
    r"Aug(?:ust)?|Sep(?:t)?(?:ember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
)
_DATE_ANY = (
    r"(?:"
    r"\d{4}-\d{2}-\d{2}"
    r"|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}"
    rf"|{_MONTHS}\.?\s+\d{{1,2}}(?:st|nd|rd|th)?,?\s+\d{{4}}"
    rf"|\d{{1,2}}\s+{_MONTHS}\.?\s+\d{{4}}"
    rf"|{_MONTHS}\.?\s+\d{{4}}"
    r")"
)
_CLOCK = r"(?:\d{1,2}:\d{2}(?::\d{2})?(?:\.\d+)?\s*(?:[AaPp]\.?[Mm]\.?)?(?:\s*(?:UTC|GMT|[ECMP][SD]T|Z|[+-]\d{2}:?\d{2}))?)"

# markers that indicate a date/time is a RENDER artifact, not regulatory content
_VOLATILE_MARKER = (
    r"(?:last\s*(?:updated?|modified|reviewed|revised|refreshed|checked|edited|built)"
    r"|updated\s*(?:on|at)?|modified\s*(?:on|at)?|generated\s*(?:on|at)?|created\s*on"
    r"|printed\s*(?:on|at)?|retrieved\s*(?:on|at)?|accessed\s*(?:on|at)?"
    r"|downloaded\s*(?:on|at)?|current\s+as\s+of|as\s+of|page\s+(?:updated|generated|rendered)"
    r"|report\s+(?:date|run)|run\s*(?:on|at|date)|date\s+printed|timestamp"
    r"|copyright|©|&copy;)"
)

_RE_MARKER_DATETIME = re.compile(
    rf"{_VOLATILE_MARKER}\s*[:\-–]?\s*(?:{_DATE_ANY})?(?:\s*(?:at|,)?\s*{_CLOCK})?"
    rf"(?:\s*\d{{4}})?",
    re.I,
)
_RE_ISO_DATETIME = re.compile(
    r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(?::\d{2})?(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?"
)
_RE_CLOCK_ONLY = re.compile(_CLOCK)
_RE_RENDER_TIMER = re.compile(
    r"(?:page\s+)?(?:generated|rendered|processed|executed|query\s+took|execution\s+time|"
    r"load\s+time|elapsed)[^.\n]{0,24}?\d+(?:\.\d+)?\s*(?:ms|milliseconds?|s|seconds?)",
    re.I,
)
_RE_COUNTER = re.compile(
    r"(?:visitors?|visits?|hits?|views?|page\s*views?|downloads?|online\s+now|"
    r"users?\s+online|you\s+are\s+visitor(?:\s+number)?)\s*[:#]?\s*[\d,]{1,15}"
    r"|[\d,]{1,15}\s*(?:visitors?|visits?|hits?|views?|page\s*views?|downloads?)\b",
    re.I,
)
_RE_UUID = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I
)
_RE_LONG_HEX = re.compile(r"\b[0-9a-f]{16,}\b", re.I)
_RE_LONG_DIGITS = re.compile(r"\b\d{10,}\b")
_RE_WS_LINE = re.compile(r"[ \t\r\f\v]+")
_RE_BLANKS = re.compile(r"\n{2,}")

_VOLATILE_JSON_KEYS = {
    "timestamp", "generated", "generatedon", "servertime", "currenttime", "now",
    "requestid", "request_id", "traceid", "correlationid", "sessionid", "session_id",
    "token", "nonce", "csrf", "etag", "lastmod", "lastmodified", "last_modified",
    "currentversion", "buildnumber", "build", "cachekey", "expires", "servertimezone",
}


def scrub_text_volatiles(text: str) -> str:
    """Remove render-time artifacts from already-extracted text.

    Order matters: marker-adjacent datetimes go first (so "Last updated:
    Sept 4, 2026 3:04 PM" disappears whole), then bare ISO datetimes and clock
    times, then counters and rotating identifiers.  Bare calendar dates with no
    volatility marker survive deliberately — see module docstring.
    """
    text = _RE_RENDER_TIMER.sub(" ", text)   # before the marker rule: "page
    #                                          generated" is a prefix of both
    text = _RE_MARKER_DATETIME.sub(" ", text)
    text = _RE_ISO_DATETIME.sub(" ", text)
    text = _RE_COUNTER.sub(" ", text)
    text = _RE_CLOCK_ONLY.sub(" ", text)
    text = _RE_UUID.sub("<HEX>", text)
    text = _RE_LONG_HEX.sub("<HEX>", text)
    text = _RE_LONG_DIGITS.sub("<NUM>", text)
    lines = [_RE_WS_LINE.sub(" ", ln).strip() for ln in text.splitlines()]
    return _RE_BLANKS.sub("\n", "\n".join(ln for ln in lines if ln)).strip()


def strip_html_volatiles(markup: str) -> str:
    """Remove comments, script/style, tokens, view-state and cache-busters."""
    markup = _RE_COMMENT.sub(" ", markup)
    markup = _RE_CDATA.sub(" ", markup)
    markup = _RE_DROP_ELEMENT.sub(" ", markup)
    markup = _RE_DROP_SELFCLOSED.sub(" ", markup)
    markup = _RE_FEED_MARKERS.sub(" ", markup)
    markup = _HIDDEN_TOKEN_INPUT.sub(" ", markup)
    markup = _VOLATILE_META.sub(" ", markup)
    markup = _VOLATILE_ATTR.sub(" ", markup)
    markup = _HEX_FINGERPRINT_QS.sub("", markup)
    markup = _CACHE_BUST_QS.sub("", markup)
    markup = _SESSION_QS.sub("", markup)
    return markup


def normalize_html(markup: str) -> str:
    """HTML/XML -> stable, line-structured text suitable for hashing & diffing."""
    markup = strip_html_volatiles(markup)
    # give block elements a line break so the diff has usable granularity
    markup = re.sub(
        r"<\s*/?\s*(p|div|br|li|tr|h[1-6]|section|article|table|ul|ol|dl|dd|dt|"
        r"header|footer|nav|blockquote|pre|title|item|entry|url)\b[^>]*>",
        "\n",
        markup,
        flags=re.I,
    )
    text = _RE_TAG.sub(" ", markup)
    text = _html.unescape(text)
    return scrub_text_volatiles(text)


def normalize_json_bytes(raw: bytes) -> Optional[str]:
    try:
        data = json.loads(raw.decode("utf-8", "replace"))
    except Exception:
        return None

    def prune(obj):
        if isinstance(obj, dict):
            return {
                k: prune(v)
                for k, v in sorted(obj.items())
                if k.replace("-", "").replace("_", "").lower() not in _VOLATILE_JSON_KEYS
            }
        if isinstance(obj, list):
            return [prune(v) for v in obj]
        return obj

    return scrub_text_volatiles(json.dumps(prune(data), indent=1, sort_keys=True))


def extract_pdf_text(raw: bytes) -> str:
    """Best-effort PDF text extraction. Returns '' when nothing is extractable."""
    import io

    try:
        from pdfminer.high_level import extract_text  # type: ignore

        txt = extract_text(io.BytesIO(raw)) or ""
        if txt.strip():
            return txt
    except Exception:
        pass
    try:
        from pypdf import PdfReader  # type: ignore

        reader = PdfReader(io.BytesIO(raw))
        return "\n".join((p.extract_text() or "") for p in reader.pages)
    except Exception:
        return ""


def decode_body(raw: bytes, content_type: str) -> str:
    m = re.search(r"charset=([\w-]+)", content_type or "", re.I)
    if m:
        try:
            return raw.decode(m.group(1), "replace")
        except LookupError:
            pass
    m = re.search(rb"charset=[\"']?([\w-]{2,20})", raw[:4096], re.I)
    if m:
        try:
            return raw.decode(m.group(1).decode("ascii", "ignore"), "replace")
        except LookupError:
            pass
    return raw.decode("utf-8", "replace")


@dataclass
class Normalized:
    normalizer: str
    diff_text: str
    hash_text: str
    sha256: str
    noisy: bool = False       # True when the hash is over raw bytes -> false positives likely


def normalize_body(raw: bytes, content_type: str = "", url: str = "") -> Normalized:
    """Reduce a fetched body to (normalizer, diff_text, hash_text, sha256).

    ``hash_text`` is ``diff_text`` with all whitespace collapsed, so pure
    re-wrapping/re-indentation never registers as a change while the diff stays
    readable.
    """
    ct = (content_type or "").lower()
    path = urlsplit(url or "").path.lower()
    normalizer = "text"
    noisy = False

    if "pdf" in ct or path.endswith(".pdf") or raw[:5] == b"%PDF-":
        txt = extract_pdf_text(raw)
        if txt.strip():
            normalizer, body = "pdf_text", scrub_text_volatiles(txt)
        else:
            normalizer, noisy = "pdf_bytes", True
            body = ""
            return Normalized(normalizer, "", "", sha256_bytes(raw), True)
    elif "json" in ct or path.endswith((".json", ".geojson")):
        body = normalize_json_bytes(raw)
        if body is None:
            normalizer, body = "text", scrub_text_volatiles(decode_body(raw, ct))
        else:
            normalizer = "json"
    elif ("html" in ct or "xml" in ct or "rss" in ct or "atom" in ct
          or path.endswith((".html", ".htm", ".xml", ".aspx", ".php", ".rss"))
          or b"<html" in raw[:2048].lower() or b"<?xml" in raw[:64].lower()
          or not ct or ct.startswith("text/")):
        normalizer = "html"
        body = normalize_html(decode_body(raw, ct))
    else:
        normalizer, noisy = "bytes", True
        return Normalized(normalizer, "", "", sha256_bytes(raw), True)

    hash_text = " ".join(body.split())
    return Normalized(normalizer, body, hash_text, sha256_bytes(hash_text.encode()), noisy)


# --------------------------------------------------------------- watch state

def load_state() -> dict:
    if WATCH_STATE.exists():
        try:
            data = json.loads(WATCH_STATE.read_text(encoding="utf-8"))
            if isinstance(data, dict) and "urls" in data:
                return data
        except json.JSONDecodeError:
            print(f"warning: {WATCH_STATE} is corrupt; starting fresh", file=sys.stderr)
    return {"version": STATE_VERSION, "updated": "", "urls": {}}


def save_state(state: dict) -> None:
    state["version"] = STATE_VERSION
    state["updated"] = now_iso()
    WATCH_STATE.parent.mkdir(parents=True, exist_ok=True)
    tmp = WATCH_STATE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(WATCH_STATE)


# --------------------------------------------------------------- target plan

@dataclass
class Target:
    url: str
    source_ids: list[str] = field(default_factory=list)
    states: list[str] = field(default_factory=list)
    jurisdictions: list[str] = field(default_factory=list)
    titles: list[str] = field(default_factory=list)
    origin: str = "check_urls"        # check_urls | landing_url | document
    cadence: str = "quarterly"
    method: str = "hash"
    doc_type: str = ""
    fmt: str = ""

    @property
    def title(self) -> str:
        return self.titles[0] if self.titles else self.url

    @property
    def jurisdiction(self) -> str:
        return self.jurisdictions[0] if self.jurisdictions else ""

    @property
    def state(self) -> str:
        return self.states[0] if self.states else "US"


def _add(targets: dict[str, Target], url: str, src: Source, title: str,
         origin: str, doc_type: str = "", fmt: str = "") -> None:
    url = (url or "").strip()
    if not url or not url.lower().startswith(("http://", "https://")):
        return
    uw = src.update_watch or {}
    t = targets.get(url)
    if t is None:
        t = Target(url=url, origin=origin,
                   cadence=uw.get("cadence") or "quarterly",
                   method=uw.get("method") or "hash",
                   doc_type=doc_type, fmt=fmt)
        targets[url] = t
    if src.id not in t.source_ids:
        t.source_ids.append(src.id)
        t.states.append(src.state)
        t.jurisdictions.append(src.jurisdiction_label)
        t.titles.append(title or url)


def plan_targets(sources: Iterable[Source]) -> list[Target]:
    """Build the de-duplicated fetch plan (check_urls, else landing+documents)."""
    targets: dict[str, Target] = {}
    for src in sources:
        uw = src.update_watch or {}
        check_urls = [u for u in (uw.get("check_urls") or []) if u]
        if check_urls:
            for u in check_urls:
                _add(targets, u, src, f"{src.name} — watch URL", "check_urls")
            continue
        if src.landing_url:
            _add(targets, src.landing_url, src, f"{src.name} — landing page", "landing_url")
        for d in src.docs():
            _add(targets, d.url, src, d.title, "document", d.doc_type, d.format)
    return list(targets.values())


CADENCE_DAYS = {"weekly": 7, "monthly": 30, "quarterly": 90}


def is_due(target: Target, state: dict, today: Optional[datetime] = None) -> bool:
    """True when the target has never been checked, or its cadence has elapsed."""
    prev = state["urls"].get(target.url) or {}
    last = prev.get("last_checked")
    if not last:
        return True
    try:
        when = datetime.fromisoformat(last)
    except ValueError:
        return True
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    now = today or datetime.now(timezone.utc)
    return (now - when).days >= CADENCE_DAYS.get(target.cadence, 90)


def filter_targets(targets: list[Target], states: list[str], cadence: str,
                   source_ids: list[str], limit: int, due_only: bool = False,
                   state: Optional[dict] = None) -> list[Target]:
    out = []
    states_u = {s.upper() for s in states}
    ids = set(source_ids)
    for t in targets:
        if states_u and not (states_u & set(t.states)):
            continue
        if cadence and t.cadence != cadence:
            continue
        if ids and not (ids & set(t.source_ids)):
            continue
        if due_only and state is not None and not is_due(t, state):
            continue
        out.append(t)
    out.sort(key=lambda t: (t.state, t.jurisdiction, t.url))
    return out[:limit] if limit and limit > 0 else out


# --------------------------------------------------------------- text baseline

def _url_key(url: str) -> str:
    return sha256_bytes(url.encode())[:16]


def snapshot_path(url: str) -> Path:
    return SNAPSHOT_DIR / f"{_url_key(url)}.txt"


def find_text_baseline(url: str, source_ids: list[str], titles: list[str]
                       ) -> tuple[Optional[Path], str]:
    """Locate a previously extracted text copy for this URL.

    Tried in order (all conventions documented here because ``harvest.py`` is
    owned by another agent and its layout may evolve):

    1. ``corpus/manifest.jsonl`` record ``<source_id>::<url>`` carrying any of
       ``text_path`` / ``text_file`` / ``text`` (relative to repo root, to
       ``corpus/``, or absolute).
    2. ``corpus/text/<source_id>/<slug>.txt|.md``
    3. ``corpus/text/<state>/<source_id>/<slug>.txt|.md``
    4. ``corpus/text/**/<slug>.txt`` (single unambiguous match only)
    5. this tool's own snapshot, ``corpus/watch_text/<sha256(url)[:16]>.txt``
    """
    manifest = manifest_read()
    for sid in source_ids:
        rec = manifest.get(f"{sid}::{url}")
        if not rec:
            continue
        for key in ("text_path", "text_file", "text"):
            val = rec.get(key)
            if not val or not isinstance(val, str):
                continue
            for base in (Path("/"), ROOT, ROOT.parent, CORPUS_DIR):
                p = (base / val.lstrip("/")) if base != Path("/") else Path(val)
                if p.is_file():
                    return p, "corpus/text (manifest)"

    tail = urlsplit(url).path.rsplit("/", 1)[-1] or urlsplit(url).netloc
    slugs = {slugify(tail.rsplit(".", 1)[0] or tail)}
    slugs.update(slugify(t) for t in titles if t)
    for sid in source_ids:
        for slug in slugs:
            for ext in (".txt", ".md"):
                for cand in (TEXT_DIR / sid / f"{slug}{ext}",
                             TEXT_DIR / sid.split("-")[0] / sid / f"{slug}{ext}"):
                    if cand.is_file():
                        return cand, "corpus/text"
    for slug in slugs:
        hits = sorted(TEXT_DIR.glob(f"**/{slug}.txt"))
        if len(hits) == 1:
            return hits[0], "corpus/text (glob)"

    snap = snapshot_path(url)
    if snap.is_file():
        return snap, "watch snapshot"
    return None, ""


def make_diff(old_text: str, new_text: str, label_old: str, label_new: str
              ) -> tuple[str, int, int]:
    """Unified diff, truncated. Returns (text, shown_lines, elided_lines)."""
    lines = list(difflib.unified_diff(
        old_text.splitlines(), new_text.splitlines(),
        fromfile=label_old, tofile=label_new, lineterm="", n=2,
    ))
    if not lines:
        return "", 0, 0
    shown = lines[:MAX_DIFF_LINES]
    elided = max(0, len(lines) - MAX_DIFF_LINES)
    return "\n".join(shown), len(shown), elided


# --------------------------------------------------------------- checking

@dataclass
class Result:
    url: str
    source_ids: list[str]
    state: str
    jurisdiction: str
    title: str
    origin: str
    cadence: str
    changed: bool = False
    change_type: str = "unchanged"
    signal: str = ""
    http_status: int = 0
    sha256: str = ""
    previous_sha256: str = ""
    etag: str = ""
    last_modified: str = ""
    last_changed: str = ""
    previous_checked: str = ""
    normalizer: str = ""
    noisy: bool = False
    metadata_only: bool = False
    diff: str = ""
    diff_lines: int = 0
    diff_elided: int = 0
    diff_baseline: str = ""
    error: str = ""
    consecutive_error_count: int = 0

    def to_json(self) -> dict:
        d = dict(self.__dict__)
        return d


def check_target(t: Target, fetcher, state: dict, write_snapshots: bool = True) -> Result:
    prev = state["urls"].get(t.url, {})
    res = Result(
        url=t.url, source_ids=list(t.source_ids), state=t.state,
        jurisdiction=t.jurisdiction, title=t.title, origin=t.origin,
        cadence=t.cadence, previous_sha256=prev.get("sha256", ""),
        previous_checked=prev.get("last_checked", ""),
        last_changed=prev.get("last_changed", ""),
    )
    r = fetcher.get(t.url, etag=prev.get("etag", ""),
                    last_modified=prev.get("last_modified", ""))
    res.http_status = getattr(r, "status_code", 0)
    headers = getattr(r, "headers", {}) or {}

    # ---- transport-level failure ---------------------------------------
    if res.http_status == 0 or res.http_status >= 400:
        res.change_type = "error"
        res.error = (f"HTTP {res.http_status} "
                     f"{getattr(r, 'reason', '') or ''}").strip()
        res.consecutive_error_count = int(prev.get("consecutive_error_count", 0)) + 1
        res.etag, res.last_modified = prev.get("etag", ""), prev.get("last_modified", "")
        res.sha256 = res.previous_sha256
        res.normalizer = prev.get("normalizer", "")
        return res

    # ---- signal 1: 304 --------------------------------------------------
    if res.http_status == 304:
        res.change_type, res.signal = "unchanged", "http_304"
        res.sha256 = res.previous_sha256
        res.etag = prev.get("etag", "")
        res.last_modified = prev.get("last_modified", "")
        res.normalizer = prev.get("normalizer", "")
        return res

    body = getattr(r, "content", b"") or b""
    norm = normalize_body(body, headers.get("Content-Type", ""), t.url)
    res.sha256 = norm.sha256
    res.normalizer = norm.normalizer
    res.noisy = norm.noisy
    res.etag = headers.get("ETag", "") or ""
    res.last_modified = headers.get("Last-Modified", "") or ""

    # ---- signal 2: validator delta (corroborating; authoritative only when
    #      the body cannot be normalized into text) -----------------------
    etag_moved = bool(prev.get("etag")) and res.etag and res.etag != prev["etag"]
    lm_moved = (bool(prev.get("last_modified")) and res.last_modified
                and res.last_modified != prev["last_modified"])

    # ---- signal 3: normalized content hash ------------------------------
    if not res.previous_sha256:
        res.change_type, res.signal = "new", "first_seen"
        res.changed = False          # a first sighting is a baseline, not a change
        res.last_changed = res.last_changed or now_iso()
    elif norm.sha256 != res.previous_sha256:
        res.changed = True
        res.change_type = "changed"
        sigs = ["hash"]
        if etag_moved:
            sigs.append("etag")
        if lm_moved:
            sigs.append("last_modified")
        res.signal = "+".join(sigs)
        res.last_changed = now_iso()
    else:
        res.change_type, res.signal = "unchanged", "hash"
        if etag_moved or lm_moved:
            res.metadata_only = True
            res.signal = "hash (validator rotated, content identical)"

    # ---- diff -----------------------------------------------------------
    if res.changed and norm.diff_text:
        baseline_path, baseline_kind = find_text_baseline(t.url, t.source_ids, t.titles)
        if baseline_path:
            try:
                old = baseline_path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                old = ""
            if old:
                diff, shown, elided = make_diff(
                    scrub_text_volatiles(old), norm.diff_text,
                    f"{baseline_kind}: {baseline_path.name}",
                    f"fetched {now_iso()}",
                )
                res.diff, res.diff_lines, res.diff_elided = diff, shown, elided
                res.diff_baseline = f"{baseline_kind}: {baseline_path}"

    if write_snapshots and norm.diff_text:
        SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
        snapshot_path(t.url).write_text(norm.diff_text, encoding="utf-8")

    return res


def update_state(state: dict, res: Result, target: Target) -> None:
    state["urls"][res.url] = {
        "sha256": res.sha256,
        "etag": res.etag,
        "last_modified": res.last_modified,
        "last_checked": now_iso(),
        "last_changed": res.last_changed,
        "consecutive_error_count": res.consecutive_error_count,
        "http_status": res.http_status,
        "normalizer": res.normalizer,
        "metadata_only": res.metadata_only,
        "noisy": res.noisy,
        "source_ids": list(target.source_ids),
        "cadence": target.cadence,
    }


# --------------------------------------------------------------- reporting

def _anchor(res: Result) -> str:
    return slugify(f"{res.state}-{res.jurisdiction}-{res.title}")[:60]


def render_markdown(results: list[Result], args, elapsed: str) -> str:
    changed = [r for r in results if r.changed]
    new = [r for r in results if r.change_type == "new"]
    errs = [r for r in results if r.change_type == "error"]
    unchanged = [r for r in results if r.change_type == "unchanged"]
    today = date.today().isoformat()

    L: list[str] = []
    L.append(f"# RegBase update check — {today}")
    L.append("")
    filters = []
    if args.state:
        filters.append("state=" + ",".join(s.upper() for s in args.state))
    if args.cadence:
        filters.append(f"cadence={args.cadence}")
    if args.source_id:
        filters.append("source_id=" + ",".join(args.source_id))
    if args.limit:
        filters.append(f"limit={args.limit}")
    if getattr(args, "due", False):
        filters.append("due-only")
    L.append(f"*Generated {now_iso()} · {elapsed} · filters: "
             f"{'; '.join(filters) if filters else 'none (full sweep)'}*")
    L.append("")
    L.append("| | count |")
    L.append("|---|---:|")
    L.append(f"| **Changed** | {len(changed)} |")
    L.append(f"| New (baseline recorded) | {len(new)} |")
    L.append(f"| Unchanged | {len(unchanged)} |")
    L.append(f"| Errors | {len(errs)} |")
    L.append(f"| URLs checked | {len(results)} |")
    L.append("")

    if not changed:
        L.append("**No regulatory content changed on this run.**")
        L.append("")

    # ---- changed, grouped by state then jurisdiction -------------------
    if changed:
        L.append("## Changed")
        L.append("")
        for st in sorted({r.state for r in changed}):
            L.append(f"### {st}")
            L.append("")
            rows = [r for r in changed if r.state == st]
            for juris in sorted({r.jurisdiction for r in rows}):
                L.append(f"#### {juris}")
                L.append("")
                for r in sorted([x for x in rows if x.jurisdiction == juris],
                                key=lambda x: x.title):
                    L.append(f"- **{r.title}**")
                    L.append(f"  - URL: <{r.url}>")
                    L.append(f"  - Sources: `{'`, `'.join(r.source_ids)}`")
                    L.append(f"  - Signal: `{r.signal}` · HTTP {r.http_status} · "
                             f"normalizer `{r.normalizer}`")
                    L.append(f"  - sha256 `{r.previous_sha256[:12] or '—'}` → "
                             f"`{r.sha256[:12]}`")
                    L.append(f"  - Previously changed: {r.last_changed or 'unknown'} "
                             f"· previously checked: {r.previous_checked or 'never'}")
                    if r.noisy:
                        L.append("  - :warning: hashed over raw bytes (no extractable "
                                 "text) — this change may be a re-export, not a "
                                 "substantive edit. Verify by hand.")
                    if r.diff:
                        L.append(f"  - Diff baseline: `{r.diff_baseline}`")
                        L.append("")
                        L.append("<details><summary>Unified diff "
                                 f"({r.diff_lines} lines"
                                 + (f", {r.diff_elided} elided" if r.diff_elided else "")
                                 + ")</summary>")
                        L.append("")
                        L.append("```diff")
                        L.append(r.diff)
                        if r.diff_elided:
                            L.append(f"... {r.diff_elided} further diff lines elided "
                                     f"(limit {MAX_DIFF_LINES}) ...")
                        L.append("```")
                        L.append("")
                        L.append("</details>")
                    else:
                        L.append("  - _No previous extracted text under `corpus/text/` "
                                 "or `corpus/watch_text/` — content hash moved but no "
                                 "diff can be shown. Run `harvest.py` for this source, "
                                 "or re-run after this snapshot is stored._")
                    L.append("")
            L.append("")

    if new:
        L.append("## New (baseline recorded, nothing to compare yet)")
        L.append("")
        for r in sorted(new, key=lambda x: (x.state, x.jurisdiction, x.title)):
            L.append(f"- [{r.state}] {r.jurisdiction} — {r.title} — <{r.url}>")
        L.append("")

    if errs:
        L.append("## Errors")
        L.append("")
        L.append("| state | jurisdiction | document | HTTP | consecutive | url |")
        L.append("|---|---|---|---:|---:|---|")
        for r in sorted(errs, key=lambda x: (-x.consecutive_error_count, x.state)):
            flag = " :rotating_light:" if r.consecutive_error_count >= 3 else ""
            L.append(f"| {r.state} | {r.jurisdiction} | {r.title} | "
                     f"{r.error}{flag} | {r.consecutive_error_count} | <{r.url}> |")
        L.append("")
        L.append("_Three or more consecutive failures usually means the URL moved; "
                 "update the source record's `documents[].url` / "
                 "`update_watch.check_urls` rather than ignoring it._")
        L.append("")

    meta = [r for r in unchanged if r.metadata_only]
    if meta:
        L.append("## Suppressed noise (validator rotated, content identical)")
        L.append("")
        L.append(f"{len(meta)} URL(s) returned a new ETag/Last-Modified while the "
                 "normalized content hash was unchanged. These are NOT reported as "
                 "changes on purpose — see the normalization notes in "
                 "`check_updates.py`.")
        L.append("")
        for r in sorted(meta, key=lambda x: (x.state, x.title))[:40]:
            L.append(f"- [{r.state}] {r.title} — <{r.url}>")
        L.append("")

    L.append("---")
    L.append("")
    L.append("### What a reviewer should do with this")
    L.append("")
    L.append("1. Read each diff under **Changed**; decide whether the moved language "
             "affects midstream permitting (setbacks, flowline/gathering rules, SWD "
             "or injection permitting, 1041 / special-use triggers, ROW, fees).")
    L.append("2. For material changes, update the corresponding "
             "`regbase/sources/*.yaml` record: bump `last_reviewed`, adjust "
             "`confidence`, and fix any moved URL.")
    L.append("3. Re-run `harvest.py` for the affected sources so `corpus/text/` "
             "picks up the new language and the next diff is clean.")
    L.append("4. Chase every URL in **Errors** with 3+ consecutive failures.")
    L.append("")
    return "\n".join(L) + "\n"


def render_json(results: list[Result], args, elapsed: str) -> dict:
    return {
        "tool": "check_updates.py",
        "generated": now_iso(),
        "date": date.today().isoformat(),
        "elapsed": elapsed,
        "filters": {
            "state": [s.upper() for s in (args.state or [])],
            "cadence": args.cadence or None,
            "source_id": args.source_id or [],
            "limit": args.limit or None,
            "due_only": bool(getattr(args, "due", False)),
        },
        "counts": {
            "checked": len(results),
            "changed": sum(1 for r in results if r.changed),
            "new": sum(1 for r in results if r.change_type == "new"),
            "unchanged": sum(1 for r in results if r.change_type == "unchanged"),
            "errors": sum(1 for r in results if r.change_type == "error"),
            "metadata_only_suppressed": sum(1 for r in results if r.metadata_only),
        },
        "results": [r.to_json() for r in sorted(
            results, key=lambda r: (not r.changed, r.state, r.jurisdiction, r.title))],
    }


def render_dry_run(targets: list[Target], state: dict, args) -> dict:
    plan = []
    for t in targets:
        prev = state["urls"].get(t.url, {})
        plan.append({
            "url": t.url,
            "state": t.state,
            "jurisdiction": t.jurisdiction,
            "title": t.title,
            "source_ids": t.source_ids,
            "origin": t.origin,
            "cadence": t.cadence,
            "method": t.method,
            "doc_type": t.doc_type,
            "format": t.fmt,
            "known": bool(prev),
            "conditional_get": {
                "If-None-Match": prev.get("etag", "") or None,
                "If-Modified-Since": prev.get("last_modified", "") or None,
            },
            "previous_sha256": prev.get("sha256", "") or None,
            "last_checked": prev.get("last_checked", "") or None,
            "last_changed": prev.get("last_changed", "") or None,
            "consecutive_error_count": prev.get("consecutive_error_count", 0),
        })
    return {
        "tool": "check_updates.py",
        "mode": "dry-run",
        "generated": now_iso(),
        "filters": {
            "state": [s.upper() for s in (args.state or [])],
            "cadence": args.cadence or None,
            "source_id": args.source_id or [],
            "limit": args.limit or None,
            "due_only": bool(getattr(args, "due", False)),
        },
        "delay_seconds": args.delay,
        "would_fetch": len(plan),
        "already_known": sum(1 for p in plan if p["known"]),
        "first_time": sum(1 for p in plan if not p["known"]),
        "targets": plan,
    }


# --------------------------------------------------------------- cli

EGRESS_HELP = """\
Outbound HTTPS appears to be blocked in this environment, so check_updates.py
cannot fetch anything. Nothing was written.

To fix, one of:
  * Claude Code (web/remote): enable outbound network access for this
    environment in the session's environment settings (Settings ->
    Environment -> Network access / allowed domains), then re-run.
  * Locally:  git clone the repo and run
        python3 regbase/tools/check_updates.py --cadence weekly
    from a machine with normal internet access.
  * CI: the scheduled workflow at .github/workflows/regbase-update-check.yml
    runs this on GitHub-hosted runners, which have egress.

To see exactly what WOULD be fetched without any network at all:
  python3 regbase/tools/check_updates.py --dry-run [--state CO] [--limit 20]
"""


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="check_updates.py",
        description="Detect changed regulations across the RegBase source registry.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--state", action="append", default=[],
                   help="limit to a state (CO/WY/NM/UT/TX/US); repeatable")
    p.add_argument("--cadence", choices=["weekly", "monthly", "quarterly"],
                   help="only sources whose update_watch.cadence matches")
    p.add_argument("--source-id", action="append", default=[],
                   help="limit to a specific source id; repeatable")
    p.add_argument("--limit", type=int, default=0, help="max URLs to check")
    p.add_argument("--due", action="store_true",
                   help="only URLs whose cadence has elapsed since last_checked "
                        "(never-checked URLs always count as due)")
    p.add_argument("--dry-run", action="store_true",
                   help="list exactly what would be fetched; makes no network calls")
    p.add_argument("--delay", type=float, default=1.5,
                   help="per-host politeness delay in seconds (default 1.5)")
    p.add_argument("--json", action="store_true",
                   help="print machine-readable JSON to stdout")
    p.add_argument("--no-egress-check", action="store_true",
                   help="skip the outbound-connectivity probe")
    p.add_argument("--reports-dir", default=str(REPORTS_DIR),
                   help=f"where to write reports (default {REPORTS_DIR})")
    return p


def _tolerate_sigpipe() -> None:
    """Let `... | head` close the pipe without a BrokenPipeError traceback."""
    try:
        import signal
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    except (ImportError, AttributeError, ValueError):
        pass


def main(argv: Optional[list[str]] = None) -> int:
    _tolerate_sigpipe()
    args = build_parser().parse_args(argv)
    started = datetime.now(timezone.utc)

    sources = load_sources()
    state = load_state()
    all_targets = plan_targets(sources)
    targets = filter_targets(all_targets, args.state, args.cadence,
                             args.source_id, args.limit, args.due, state)

    if not targets:
        msg = ("No watch targets matched the given filters "
               f"({len(all_targets)} watch URLs in the registry).")
        if args.cadence:
            declared = sorted({t.cadence for t in all_targets})
            msg += (f" Cadences present in the registry: {', '.join(declared)}. "
                    "Sources with no `update_watch.cadence` fall back to "
                    "'quarterly'; declare `update_watch: {cadence: weekly}` on the "
                    "records you want swept more often, or use --due instead.")
        if args.json:
            print(json.dumps({"tool": "check_updates.py", "would_fetch": 0,
                              "targets": [], "note": msg}, indent=1))
        else:
            print(msg)
        return 0

    # ---------------- dry run: zero network -----------------------------
    if args.dry_run:
        plan = render_dry_run(targets, state, args)
        if args.json:
            print(json.dumps(plan, indent=1))
            return 0
        print(f"DRY RUN — would fetch {plan['would_fetch']} URL(s) "
              f"({plan['already_known']} with stored state, "
              f"{plan['first_time']} first-time), "
              f"{args.delay}s per-host delay. No network calls made.")
        print()
        hdr = f"{'STATE':<6} {'CADENCE':<10} {'ORIGIN':<12} {'KNOWN':<6} URL"
        print(hdr)
        print("-" * len(hdr))
        for t in targets:
            known = "yes" if state["urls"].get(t.url) else "new"
            print(f"{t.state:<6} {t.cadence:<10} {t.origin:<12} {known:<6} {t.url}")
        print()
        by_state: dict[str, int] = {}
        for t in targets:
            by_state[t.state] = by_state.get(t.state, 0) + 1
        print("by state: " + ", ".join(f"{k}={v}" for k, v in sorted(by_state.items())))
        print(f"reports would be written to: {args.reports_dir}/updates_"
              f"{date.today().isoformat()}.{{md,json}}")
        return 0

    # ---------------- live run ------------------------------------------
    if not args.no_egress_check and not egress_ok():
        print(EGRESS_HELP, file=sys.stderr)
        return 2

    fetcher = common.Fetcher(delay=args.delay)
    results: list[Result] = []
    for i, t in enumerate(targets, 1):
        if not args.json:
            print(f"[{i}/{len(targets)}] {t.url}", file=sys.stderr)
        res = check_target(t, fetcher, state)
        update_state(state, res, t)
        results.append(res)
    save_state(state)

    elapsed = f"{(datetime.now(timezone.utc) - started).total_seconds():.0f}s"
    reports = Path(args.reports_dir)
    reports.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    md_path = reports / f"updates_{today}.md"
    js_path = reports / f"updates_{today}.json"
    payload = render_json(results, args, elapsed)
    md_path.write_text(render_markdown(results, args, elapsed), encoding="utf-8")
    js_path.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")

    if args.json:
        print(json.dumps(payload, indent=1))
    else:
        c = payload["counts"]
        print(f"\nchecked {c['checked']} · changed {c['changed']} · new {c['new']} "
              f"· unchanged {c['unchanged']} · errors {c['errors']}")
        print(f"report: {md_path}")
        print(f"json:   {js_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
