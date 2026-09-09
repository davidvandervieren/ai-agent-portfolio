#!/usr/bin/env python3
"""Build corpus/regbase.sqlite — the queryable spine of RegBase.

Inputs
------
  regbase/sources/*.yaml        registry records (via common.load_sources)
  regbase/corpus/manifest.jsonl harvest manifest (via common.manifest_read)
  regbase/corpus/text/**        extracted text emitted by extract.py
  regbase/people/people.seed.yaml   people layer (optional)

Outputs
-------
  regbase/corpus/regbase.sqlite with tables:
    sources     one row per registry record (arrays stored as JSON columns)
    documents   one row per registry document + harvest state
    permits     flattened permits, denormalized with jurisdiction columns so
                "what permits does Weld County require for a compressor
                station" is a single WHERE clause
    chunks      chunked extracted text, citable on its own
    chunks_fts  FTS5 index over chunks (see FTS NOTES below)
    people      people-layer records
    meta        build provenance + counts

FTS NOTES
---------
`chunks_fts` is an **external-content** FTS5 table (`content='chunks'`,
`content_rowid='id'`) kept in sync by AFTER INSERT/UPDATE/DELETE triggers on
`chunks`. External content was chosen over contentless so that:
  * the chunk text lives exactly once (no duplication of the corpus),
  * `snippet()` / `highlight()` work (they need the column text, which a
    contentless table cannot supply), and
  * ordinary SQL over `chunks` still works without touching the FTS table.
Tokenizer is `porter unicode61`; ranking is `bm25(chunks_fts, ...)` with the
text column weighted highest. If you ever hand-edit `chunks`, run
`INSERT INTO chunks_fts(chunks_fts) VALUES('rebuild')`.

Empty corpus
------------
This script is designed to run and produce a valid, useful DB when
`corpus/text/` is empty (the current state — egress is blocked, nothing has
been harvested). Registry, documents, permits and people all still index; only
`chunks` is empty.

Idempotency
-----------
Default run is incremental: sources/permits/people are re-upserted (cheap),
document text is re-chunked only when its sha256 changed. `--rebuild` drops
every table and starts clean.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Iterable, Iterator, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

import common  # noqa: E402  (shared plumbing: ROOT, paths, load_sources, ...)

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None


# ------------------------------------------------------------------ schema

SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS sources (
    id                  TEXT PRIMARY KEY,
    jurisdiction_level  TEXT NOT NULL,
    state               TEXT NOT NULL,
    county              TEXT NOT NULL DEFAULT '',
    municipality        TEXT NOT NULL DEFAULT '',
    name                TEXT NOT NULL,
    agency              TEXT NOT NULL DEFAULT '',
    jurisdiction_label  TEXT NOT NULL DEFAULT '',
    code_platform       TEXT NOT NULL DEFAULT 'unknown',
    landing_url         TEXT NOT NULL DEFAULT '',
    confidence          TEXT NOT NULL DEFAULT 'unverified',
    last_reviewed       TEXT NOT NULL DEFAULT '',
    source_file         TEXT NOT NULL DEFAULT '',
    authority_type      TEXT NOT NULL DEFAULT '[]',   -- JSON array
    applies_to          TEXT NOT NULL DEFAULT '[]',   -- JSON array
    gis                 TEXT NOT NULL DEFAULT '[]',   -- JSON array of objects
    contacts            TEXT NOT NULL DEFAULT '[]',   -- JSON array of objects
    update_watch        TEXT NOT NULL DEFAULT '{}',   -- JSON object
    n_documents         INTEGER NOT NULL DEFAULT 0,
    n_permits           INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_sources_state   ON sources(state);
CREATE INDEX IF NOT EXISTS idx_sources_county  ON sources(state, county);
CREATE INDEX IF NOT EXISTS idx_sources_muni    ON sources(state, municipality);
CREATE INDEX IF NOT EXISTS idx_sources_level   ON sources(jurisdiction_level);

CREATE TABLE IF NOT EXISTS documents (
    id               INTEGER PRIMARY KEY,
    source_id        TEXT NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    title            TEXT NOT NULL DEFAULT '',
    url              TEXT NOT NULL DEFAULT '',
    doc_type         TEXT NOT NULL DEFAULT 'regulation',
    format           TEXT NOT NULL DEFAULT 'unknown',
    citation_root    TEXT NOT NULL DEFAULT '',
    notes            TEXT NOT NULL DEFAULT '',
    local_raw_path   TEXT NOT NULL DEFAULT '',
    local_text_path  TEXT NOT NULL DEFAULT '',
    sha256           TEXT NOT NULL DEFAULT '',
    text_sha256      TEXT NOT NULL DEFAULT '',
    fetched_at       TEXT NOT NULL DEFAULT '',
    http_status      INTEGER,
    n_chunks         INTEGER NOT NULL DEFAULT 0,
    UNIQUE(source_id, url)
);
CREATE INDEX IF NOT EXISTS idx_documents_source ON documents(source_id);
CREATE INDEX IF NOT EXISTS idx_documents_type   ON documents(doc_type);

CREATE TABLE IF NOT EXISTS permits (
    id                    INTEGER PRIMARY KEY,
    source_id             TEXT NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    permit_index          INTEGER NOT NULL DEFAULT 0,
    name                  TEXT NOT NULL DEFAULT '',
    trigger               TEXT NOT NULL DEFAULT '',
    form_id               TEXT NOT NULL DEFAULT '',
    form_url              TEXT NOT NULL DEFAULT '',
    typical_timeline_days TEXT NOT NULL DEFAULT '',
    decision_body         TEXT NOT NULL DEFAULT '',
    public_hearing        INTEGER,                      -- 1/0/NULL(unknown)
    fee                   TEXT NOT NULL DEFAULT '',
    -- denormalized jurisdiction columns (one-query filtering)
    jurisdiction_level    TEXT NOT NULL DEFAULT '',
    state                 TEXT NOT NULL DEFAULT '',
    county                TEXT NOT NULL DEFAULT '',
    municipality          TEXT NOT NULL DEFAULT '',
    jurisdiction_label    TEXT NOT NULL DEFAULT '',
    agency                TEXT NOT NULL DEFAULT '',
    landing_url           TEXT NOT NULL DEFAULT '',
    confidence            TEXT NOT NULL DEFAULT 'unverified',
    applies_to            TEXT NOT NULL DEFAULT '[]',
    authority_type        TEXT NOT NULL DEFAULT '[]',
    UNIQUE(source_id, permit_index)
);
CREATE INDEX IF NOT EXISTS idx_permits_state  ON permits(state);
CREATE INDEX IF NOT EXISTS idx_permits_county ON permits(state, county);
CREATE INDEX IF NOT EXISTS idx_permits_muni   ON permits(state, municipality);
CREATE INDEX IF NOT EXISTS idx_permits_level  ON permits(jurisdiction_level);

CREATE TABLE IF NOT EXISTS chunks (
    id                 INTEGER PRIMARY KEY,
    document_id        INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    source_id          TEXT NOT NULL,
    jurisdiction_label TEXT NOT NULL DEFAULT '',
    state              TEXT NOT NULL DEFAULT '',
    county             TEXT NOT NULL DEFAULT '',
    municipality       TEXT NOT NULL DEFAULT '',
    citation_root      TEXT NOT NULL DEFAULT '',
    heading_path       TEXT NOT NULL DEFAULT '',
    chunk_index        INTEGER NOT NULL DEFAULT 0,
    char_start         INTEGER NOT NULL DEFAULT 0,
    char_end           INTEGER NOT NULL DEFAULT 0,
    text               TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_chunks_document ON chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_chunks_source   ON chunks(source_id);
CREATE INDEX IF NOT EXISTS idx_chunks_state    ON chunks(state, county, municipality);

CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
    text,
    heading_path,
    citation_root,
    jurisdiction_label,
    content='chunks',
    content_rowid='id',
    tokenize='porter unicode61'
);

CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN
    INSERT INTO chunks_fts(rowid, text, heading_path, citation_root, jurisdiction_label)
    VALUES (new.id, new.text, new.heading_path, new.citation_root, new.jurisdiction_label);
END;
CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN
    INSERT INTO chunks_fts(chunks_fts, rowid, text, heading_path, citation_root, jurisdiction_label)
    VALUES ('delete', old.id, old.text, old.heading_path, old.citation_root, old.jurisdiction_label);
END;
CREATE TRIGGER IF NOT EXISTS chunks_au AFTER UPDATE ON chunks BEGIN
    INSERT INTO chunks_fts(chunks_fts, rowid, text, heading_path, citation_root, jurisdiction_label)
    VALUES ('delete', old.id, old.text, old.heading_path, old.citation_root, old.jurisdiction_label);
    INSERT INTO chunks_fts(rowid, text, heading_path, citation_root, jurisdiction_label)
    VALUES (new.id, new.text, new.heading_path, new.citation_root, new.jurisdiction_label);
END;

CREATE TABLE IF NOT EXISTS people (
    id                      TEXT PRIMARY KEY,
    jurisdiction_id         TEXT NOT NULL DEFAULT '',
    state                   TEXT NOT NULL DEFAULT '',
    level                   TEXT NOT NULL DEFAULT '',
    body                    TEXT NOT NULL DEFAULT '',
    role_type               TEXT NOT NULL DEFAULT '',
    title                   TEXT NOT NULL DEFAULT '',
    full_name               TEXT NOT NULL DEFAULT '',
    department              TEXT NOT NULL DEFAULT '',
    appointed_by            TEXT NOT NULL DEFAULT '',
    staff_or_decision_maker TEXT NOT NULL DEFAULT '',
    portfolio               TEXT NOT NULL DEFAULT '[]',
    official_contact        TEXT NOT NULL DEFAULT '{}',
    confidence              TEXT NOT NULL DEFAULT 'unverified',
    last_reviewed           TEXT NOT NULL DEFAULT '',
    record                  TEXT NOT NULL DEFAULT '{}'   -- full JSON record
);
CREATE INDEX IF NOT EXISTS idx_people_state ON people(state);
CREATE INDEX IF NOT EXISTS idx_people_juris ON people(jurisdiction_id);

CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL DEFAULT ''
);
"""

DROP_ORDER = [
    "DROP TRIGGER IF EXISTS chunks_ai",
    "DROP TRIGGER IF EXISTS chunks_ad",
    "DROP TRIGGER IF EXISTS chunks_au",
    "DROP TABLE IF EXISTS chunks_fts",
    "DROP TABLE IF EXISTS chunks",
    "DROP TABLE IF EXISTS permits",
    "DROP TABLE IF EXISTS documents",
    "DROP TABLE IF EXISTS people",
    "DROP TABLE IF EXISTS sources",
    "DROP TABLE IF EXISTS meta",
]


# ------------------------------------------------------------------ chunking

TARGET_CHARS = 1200
OVERLAP_CHARS = 150
MIN_CHARS = 120           # below this a trailing fragment is folded backwards
MIN_INDEXABLE_CHARS = 200 # a document body below this is a shell, not content

HEADING_PATH_RE = re.compile(r"<!--\s*heading[-_]path\s*:\s*(.*?)\s*-->", re.I)
MD_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
SENTENCE_END_RE = re.compile(r"[.!?;:][\)\"'”]?\s")


def _join_path(parts: Iterable[str]) -> str:
    return " > ".join(p.strip() for p in parts if p and p.strip())


def segment_by_headings(text: str) -> list[tuple[str, int, int]]:
    """Split *text* into (heading_path, start, end) sections.

    Understands both markdown ATX headings (`## Foo`) and the extractor's
    explicit `<!-- heading-path: A > B > C -->` markers. A document with
    neither yields a single section spanning the whole text.
    """
    sections: list[tuple[str, int, int]] = []
    stack: list[tuple[int, str]] = []          # (level, title)
    explicit: Optional[str] = None
    cur_path = ""
    cur_start = 0
    pos = 0

    for line in text.splitlines(keepends=True):
        line_start = pos
        pos += len(line)
        stripped = line.strip()

        m = HEADING_PATH_RE.search(stripped)
        if m:
            if line_start > cur_start:
                sections.append((cur_path, cur_start, line_start))
            explicit = m.group(1).strip()
            cur_path = explicit
            cur_start = pos                      # marker line itself is dropped
            continue

        hm = MD_HEADING_RE.match(stripped)
        if hm:
            level = len(hm.group(1))
            title = hm.group(2).strip()
            if line_start > cur_start:
                sections.append((cur_path, cur_start, line_start))
            while stack and stack[-1][0] >= level:
                stack.pop()
            stack.append((level, title))
            # an explicit heading-path marker stays a prefix for everything under it
            parts = ([explicit] if explicit else []) + [t for _, t in stack]
            # Dedupe globally, not just against the previous segment. The
            # extractor emits a full heading-path marker AND the heading itself,
            # so a two-level section arrives as A > B from the marker plus A, B
            # from the stack. Adjacent-only dedup left "A > B > A > B", which
            # rendered in every citation.
            deduped: list[str] = []
            seen: set[str] = set()
            for part in parts:
                for seg in part.split(" > "):
                    seg = seg.strip()
                    if seg and seg not in seen:
                        seen.add(seg)
                        deduped.append(seg)
            cur_path = _join_path(deduped)
            cur_start = line_start               # keep heading line inside section
            continue

    if cur_start < len(text):
        sections.append((cur_path, cur_start, len(text)))
    if not sections:
        sections = [("", 0, len(text))]
    return [(p, s, e) for (p, s, e) in sections if text[s:e].strip()]


def _split_point(body: str, target: int) -> int:
    """Pick an end offset inside *body* near *target*, preferring a sentence
    or paragraph boundary so a chunk is never cut mid-sentence when avoidable."""
    n = len(body)
    if n <= target:
        return n
    lo = max(int(target * 0.55), 1)
    window = body[lo:target]

    para = window.rfind("\n\n")
    if para != -1:
        return lo + para + 2

    best = -1
    for m in SENTENCE_END_RE.finditer(window):
        best = m.end()
    if best != -1:
        return lo + best

    nl = window.rfind("\n")
    if nl != -1:
        return lo + nl + 1
    sp = window.rfind(" ")
    if sp != -1:
        return lo + sp + 1
    return target


def window_chunks(body: str, target: int = TARGET_CHARS,
                  overlap: int = OVERLAP_CHARS) -> Iterator[tuple[int, int]]:
    """Yield (start, end) offsets relative to *body*, ~target chars with overlap."""
    n = len(body)
    if n == 0:
        return
    if n <= int(target * 1.3):
        yield 0, n
        return
    cursor = 0
    while cursor < n:
        rel_end = _split_point(body[cursor:], target)
        end = cursor + rel_end
        if n - end < MIN_CHARS:                  # fold a tiny tail into this chunk
            end = n
        yield cursor, end
        if end >= n:
            break
        step = max(end - overlap, cursor + 1)
        # nudge the overlap start to a whitespace boundary
        probe = body.rfind(" ", max(cursor, step - 40), step)
        cursor = probe + 1 if probe > cursor else step


def chunk_document(text: str) -> list[dict]:
    """Return chunk dicts (heading_path, chunk_index, char_start, char_end, text)."""
    out: list[dict] = []
    idx = 0
    for heading_path, sec_start, sec_end in segment_by_headings(text):
        body = text[sec_start:sec_end]
        lead = len(body) - len(body.lstrip())
        body = body.strip()
        if not body:
            continue
        base = sec_start + lead
        for rel_s, rel_e in window_chunks(body):
            piece = body[rel_s:rel_e].strip()
            if len(piece) < 25:
                continue
            out.append({
                "heading_path": heading_path,
                "chunk_index": idx,
                "char_start": base + rel_s,
                "char_end": base + rel_e,
                "text": piece,
            })
            idx += 1
    return out


# ------------------------------------------------------------------ harvest state

_TEXT_KEYS = ("local_text_path", "text_path", "text", "path_text", "textfile")
_RAW_KEYS = ("local_raw_path", "raw_path", "raw", "path_raw", "file", "path")
_SHA_KEYS = ("sha256", "hash", "content_sha256", "sha")
_FETCHED_KEYS = ("fetched_at", "fetched", "timestamp", "ts", "retrieved_at")
_STATUS_KEYS = ("http_status", "status", "status_code")


def _first(rec: dict, keys: Iterable[str], default=""):
    for k in keys:
        v = rec.get(k)
        if v not in (None, ""):
            return v
    return default


def _resolve(path_value: str) -> Optional[Path]:
    """Resolve a manifest path (absolute, repo-relative, or corpus-relative)."""
    if not path_value:
        return None
    p = Path(str(path_value))
    candidates = [p] if p.is_absolute() else [
        common.ROOT / p,
        common.ROOT.parent / p,
        common.CORPUS_DIR / p,
        common.TEXT_DIR / p,
        common.RAW_DIR / p,      # REGBASE_RAW may point outside the project
    ]
    for c in candidates:
        if c.exists() and c.is_file():
            return c
    return None


def guess_text_path(src: "common.Source", title: str, url: str) -> Optional[Path]:
    """Fallback discovery for extractor output when the manifest is silent.

    Mirrors harvest.local_paths(): corpus/text/<STATE>/<source-id>/<title-slug>-<8hex>.md
    and degrades to a few looser layouts so a hand-placed text file is still found.
    """
    from urllib.parse import urlsplit

    stem = common.slugify(title or Path(urlsplit(url).path).stem or "document")
    digest = common.sha256_bytes(url.encode())[:8]
    dirs = [common.TEXT_DIR / src.state / common.slugify(src.id),
            common.TEXT_DIR / src.id,
            common.TEXT_DIR]
    names = [f"{stem}-{digest}.md", f"{stem}-{digest}.txt", f"{stem}.md", f"{stem}.txt"]
    for d in dirs:
        if not d.is_dir():
            continue
        for n in names:
            p = d / n
            if p.is_file():
                return p
        for p in sorted(d.glob(f"{stem}-*.md")) + sorted(d.glob(f"{stem}-*.txt")):
            return p
    return None


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def git_commit() -> str:
    try:
        out = subprocess.run(
            ["git", "-C", str(common.ROOT), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=10,
        )
        if out.returncode == 0:
            return out.stdout.strip()
    except Exception:
        pass
    return ""


# ------------------------------------------------------------------ build

def connect(db_path: Path, rebuild: bool) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    if rebuild:
        for stmt in DROP_ORDER:
            con.execute(stmt)
        con.commit()
    con.executescript(SCHEMA)
    con.commit()
    return con


def load_people() -> list[dict]:
    path = common.PEOPLE_DIR / "people.seed.yaml"
    if not path.exists() or yaml is None:
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    if isinstance(data, dict):
        data = data.get("people") or data.get("records") or []
    return [r for r in data if isinstance(r, dict) and r.get("id")]


def upsert_sources(con: sqlite3.Connection, sources: list[common.Source]) -> None:
    keep = {s.id for s in sources}
    existing = {r["id"] for r in con.execute("SELECT id FROM sources")}
    for dead in existing - keep:
        con.execute("DELETE FROM sources WHERE id=?", (dead,))
    for s in sources:
        con.execute(
            """INSERT INTO sources (id, jurisdiction_level, state, county, municipality, name,
                    agency, jurisdiction_label, code_platform, landing_url, confidence,
                    last_reviewed, source_file, authority_type, applies_to, gis, contacts,
                    update_watch, n_documents, n_permits)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(id) DO UPDATE SET
                    jurisdiction_level=excluded.jurisdiction_level, state=excluded.state,
                    county=excluded.county, municipality=excluded.municipality,
                    name=excluded.name, agency=excluded.agency,
                    jurisdiction_label=excluded.jurisdiction_label,
                    code_platform=excluded.code_platform, landing_url=excluded.landing_url,
                    confidence=excluded.confidence, last_reviewed=excluded.last_reviewed,
                    source_file=excluded.source_file, authority_type=excluded.authority_type,
                    applies_to=excluded.applies_to, gis=excluded.gis, contacts=excluded.contacts,
                    update_watch=excluded.update_watch, n_documents=excluded.n_documents,
                    n_permits=excluded.n_permits""",
            (
                s.id, s.jurisdiction_level, s.state, s.county or "", s.municipality or "",
                s.name, s.agency or "", s.jurisdiction_label, s.code_platform or "unknown",
                s.landing_url or "", s.confidence or "unverified", str(s.last_reviewed or ""),
                s._file, json.dumps(s.authority_type or []), json.dumps(s.applies_to or []),
                json.dumps(s.gis or []), json.dumps(s.contacts or []),
                json.dumps(s.update_watch or {}), len(s.documents or []), len(s.permits or []),
            ),
        )


def upsert_permits(con: sqlite3.Connection, sources: list[common.Source]) -> int:
    con.execute("DELETE FROM permits")           # cheap; permits come only from YAML
    n = 0
    for s in sources:
        for i, p in enumerate(s.permits or []):
            if not isinstance(p, dict):
                continue
            hearing = p.get("public_hearing")
            con.execute(
                """INSERT INTO permits (source_id, permit_index, name, trigger, form_id, form_url,
                        typical_timeline_days, decision_body, public_hearing, fee,
                        jurisdiction_level, state, county, municipality, jurisdiction_label,
                        agency, landing_url, confidence, applies_to, authority_type)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    s.id, i, str(p.get("name") or ""), str(p.get("trigger") or ""),
                    str(p.get("form_id") or ""), str(p.get("form_url") or ""),
                    str(p.get("typical_timeline_days") or ""), str(p.get("decision_body") or ""),
                    None if hearing is None else int(bool(hearing)), str(p.get("fee") or ""),
                    s.jurisdiction_level, s.state, s.county or "", s.municipality or "",
                    s.jurisdiction_label, s.agency or "", s.landing_url or "",
                    s.confidence or "unverified",
                    json.dumps(s.applies_to or []), json.dumps(s.authority_type or []),
                ),
            )
            n += 1
    return n


def upsert_people(con: sqlite3.Connection, records: list[dict]) -> int:
    keep = {r["id"] for r in records}
    for dead in {r["id"] for r in con.execute("SELECT id FROM people")} - keep:
        con.execute("DELETE FROM people WHERE id=?", (dead,))
    for r in records:
        con.execute(
            """INSERT INTO people (id, jurisdiction_id, state, level, body, role_type, title,
                    full_name, department, appointed_by, staff_or_decision_maker, portfolio,
                    official_contact, confidence, last_reviewed, record)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(id) DO UPDATE SET
                    jurisdiction_id=excluded.jurisdiction_id, state=excluded.state,
                    level=excluded.level, body=excluded.body, role_type=excluded.role_type,
                    title=excluded.title, full_name=excluded.full_name,
                    department=excluded.department, appointed_by=excluded.appointed_by,
                    staff_or_decision_maker=excluded.staff_or_decision_maker,
                    portfolio=excluded.portfolio, official_contact=excluded.official_contact,
                    confidence=excluded.confidence, last_reviewed=excluded.last_reviewed,
                    record=excluded.record""",
            (
                r["id"], str(r.get("jurisdiction_id") or ""), str(r.get("state") or ""),
                str(r.get("level") or ""), str(r.get("body") or ""), str(r.get("role_type") or ""),
                str(r.get("title") or ""), str(r.get("full_name") or ""),
                str(r.get("department") or ""), str(r.get("appointed_by") or ""),
                str(r.get("staff_or_decision_maker") or ""),
                json.dumps(r.get("portfolio") or []), json.dumps(r.get("official_contact") or {}),
                str(r.get("confidence") or "unverified"), str(r.get("last_reviewed") or ""),
                json.dumps(r, default=str, sort_keys=True),
            ),
        )
    return len(records)


def index_documents(con: sqlite3.Connection, sources: list[common.Source],
                    manifest: dict[str, dict], verbose: bool = False) -> dict:
    """Upsert documents, then (re)chunk any whose extracted text changed."""
    stats = {"documents": 0, "with_text": 0, "chunked": 0, "skipped_unchanged": 0,
             "chunks": 0, "missing_text": 0}
    seen_keys: set[tuple[str, str]] = set()

    for s in sources:
        for d in s.docs():
            url = d.url or ""
            key = (s.id, url)
            if key in seen_keys:
                continue
            seen_keys.add(key)

            mrec = manifest.get(f"{s.id}::{url}", {}) or {}
            raw_p = _resolve(str(_first(mrec, _RAW_KEYS)))
            text_p = _resolve(str(_first(mrec, _TEXT_KEYS))) or guess_text_path(s, d.title, url)
            sha = str(_first(mrec, _SHA_KEYS))
            fetched = str(_first(mrec, _FETCHED_KEYS))
            status_raw = _first(mrec, _STATUS_KEYS, None)
            try:
                status = int(status_raw) if status_raw not in (None, "") else None
            except (TypeError, ValueError):
                status = None

            def rel(p: Optional[Path]) -> str:
                if p is None:
                    return ""
                try:
                    return str(p.relative_to(common.ROOT))
                except ValueError:
                    return str(p)

            con.execute(
                """INSERT INTO documents (source_id, title, url, doc_type, format, citation_root,
                        notes, local_raw_path, local_text_path, sha256, fetched_at, http_status)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(source_id, url) DO UPDATE SET
                        title=excluded.title, doc_type=excluded.doc_type, format=excluded.format,
                        citation_root=excluded.citation_root, notes=excluded.notes,
                        local_raw_path=excluded.local_raw_path,
                        local_text_path=excluded.local_text_path, sha256=excluded.sha256,
                        fetched_at=excluded.fetched_at, http_status=excluded.http_status""",
                (s.id, d.title, url, d.doc_type, d.format, d.citation_root, d.notes,
                 rel(raw_p), rel(text_p), sha, fetched, status),
            )
            row = con.execute("SELECT id, text_sha256, n_chunks FROM documents "
                              "WHERE source_id=? AND url=?", (s.id, url)).fetchone()
            doc_id = row["id"]
            stats["documents"] += 1

            if text_p is None:
                stats["missing_text"] += 1
                if row["n_chunks"]:
                    con.execute("DELETE FROM chunks WHERE document_id=?", (doc_id,))
                    con.execute("UPDATE documents SET n_chunks=0, text_sha256='' WHERE id=?", (doc_id,))
                continue

            stats["with_text"] += 1
            tsha = sha256_file(text_p)
            if tsha == row["text_sha256"] and row["n_chunks"]:
                stats["skipped_unchanged"] += 1
                stats["chunks"] += row["n_chunks"]
                continue

            try:
                text = text_p.read_text(encoding="utf-8", errors="replace")
            except OSError as exc:                       # unreadable file
                if verbose:
                    print(f"  ! cannot read {text_p}: {exc}", file=sys.stderr)
                continue

            # Refuse to index a JavaScript shell as if it were an ordinance.
            # A harvest before the thin-extraction guard existed wrote ~40 such
            # files - 16 characters each, titled things like "Chapter 18 - Oil
            # and Gas Operations". Chunked, they become citable results with no
            # regulation behind them, which is worse than a missing document
            # because it looks answered. Front matter alone runs ~400 chars, so
            # the floor is measured on the body.
            body_only = text.split("---", 2)[-1].strip()
            if len(body_only) < MIN_INDEXABLE_CHARS:
                stats["too_thin"] = stats.get("too_thin", 0) + 1
                con.execute("DELETE FROM chunks WHERE document_id=?", (doc_id,))
                if verbose:
                    print(f"  ! skipping {text_p.name}: only {len(body_only)} chars "
                          f"of body - not indexable content", file=sys.stderr)
                continue

            pieces = chunk_document(text)
            con.execute("DELETE FROM chunks WHERE document_id=?", (doc_id,))
            con.executemany(
                """INSERT INTO chunks (document_id, source_id, jurisdiction_label, state, county,
                        municipality, citation_root, heading_path, chunk_index, char_start,
                        char_end, text)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                [(doc_id, s.id, s.jurisdiction_label, s.state, s.county or "",
                  s.municipality or "", d.citation_root, c["heading_path"], c["chunk_index"],
                  c["char_start"], c["char_end"], c["text"]) for c in pieces],
            )
            con.execute("UPDATE documents SET n_chunks=?, text_sha256=? WHERE id=?",
                        (len(pieces), tsha, doc_id))
            stats["chunked"] += 1
            stats["chunks"] += len(pieces)
            if verbose:
                print(f"  + {s.id} :: {d.title[:60]} -> {len(pieces)} chunks")

    # drop documents that vanished from the registry
    live = con.execute("SELECT id, source_id, url FROM documents").fetchall()
    for r in live:
        if (r["source_id"], r["url"]) not in seen_keys:
            con.execute("DELETE FROM documents WHERE id=?", (r["id"],))
    return stats


def write_meta(con: sqlite3.Connection, extra: dict) -> None:
    counts = {}
    for t in ("sources", "documents", "permits", "chunks", "people"):
        counts[t] = con.execute(f"SELECT COUNT(*) AS n FROM {t}").fetchone()["n"]
    payload = {
        "built_at": common.now_iso(),
        "git_commit": git_commit(),
        "schema_version": "1",
        "corpus_dir": str(common.CORPUS_DIR),
        "registry_sources": counts["sources"],
        "registry_documents": counts["documents"],
        "registry_permits": counts["permits"],
        "registry_people": counts["people"],
        "chunks": counts["chunks"],
        "python": sys.version.split()[0],
        "sqlite": sqlite3.sqlite_version,
    }
    payload.update({k: str(v) for k, v in extra.items()})
    for k, v in payload.items():
        con.execute("INSERT INTO meta(key, value) VALUES(?,?) "
                    "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (k, str(v)))


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rebuild", action="store_true",
                    help="drop and recreate every table (default: incremental by sha256)")
    ap.add_argument("--db", default=str(common.INDEX_DB), help="output sqlite path")
    ap.add_argument("--verbose", "-v", action="store_true")
    args = ap.parse_args(argv)

    db_path = Path(args.db)
    sources = common.load_sources()
    manifest = common.manifest_read()
    people = load_people()

    con = connect(db_path, rebuild=args.rebuild)
    try:
        upsert_sources(con, sources)
        n_permits = upsert_permits(con, sources)
        stats = index_documents(con, sources, manifest, verbose=args.verbose)
        n_people = upsert_people(con, people)
        write_meta(con, {
            "manifest_records": len(manifest),
            "text_files_present": stats["with_text"],
            "documents_missing_text": stats["missing_text"],
            "mode": "rebuild" if args.rebuild else "incremental",
        })
        con.commit()
        con.execute("PRAGMA optimize")
        con.commit()
    finally:
        con.close()

    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    q = lambda sql: con.execute(sql).fetchone()[0]  # noqa: E731
    by_state = con.execute("SELECT state, COUNT(*) n FROM sources GROUP BY state "
                           "ORDER BY n DESC").fetchall()
    by_level = con.execute("SELECT jurisdiction_level lv, COUNT(*) n FROM sources "
                           "GROUP BY lv ORDER BY n DESC").fetchall()
    conf = con.execute("SELECT confidence c, COUNT(*) n FROM sources GROUP BY c "
                       "ORDER BY n DESC").fetchall()
    states = ", ".join("%s=%s" % (r["state"], r["n"]) for r in by_state)
    levels = ", ".join("%s=%s" % (r["lv"], r["n"]) for r in by_level)
    confs = ", ".join("%s=%s" % (r["c"], r["n"]) for r in conf)
    print(f"RegBase index written: {db_path}")
    print(f"  mode              : {'rebuild' if args.rebuild else 'incremental'}")
    print(f"  sources           : {q('SELECT COUNT(*) FROM sources')}  ({states})")
    print(f"  by level          : {levels}")
    print(f"  confidence        : {confs}")
    print(f"  documents         : {q('SELECT COUNT(*) FROM documents')}"
          f"  (manifest records: {len(manifest)})")
    print(f"  permits           : {n_permits}")
    print(f"  people            : {n_people}")
    print(f"  text files found  : {stats['with_text']}  "
          f"(re-chunked {stats['chunked']}, unchanged {stats['skipped_unchanged']}"
          + (f", SKIPPED AS TOO THIN {stats['too_thin']}" if stats.get("too_thin") else "")
          + ")")
    print(f"  chunks            : {q('SELECT COUNT(*) FROM chunks')}"
          f"  (fts rows: {q('SELECT COUNT(*) FROM chunks_fts')})")
    if stats["with_text"] == 0:
        print("  NOTE: corpus/text/ is empty — no full-text chunks indexed. Registry,")
        print("        permits and people are still queryable. Run harvest.py + extract.py")
        print("        once outbound HTTPS is available, then re-run this script.")
    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
