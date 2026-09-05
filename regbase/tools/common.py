"""Shared plumbing for RegBase: paths, config, HTTP, manifest."""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
import unicodedata
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator, Optional

import yaml

# ---------------------------------------------------------------- paths

ROOT = Path(__file__).resolve().parents[1]          # .../regbase
SOURCES_DIR = ROOT / "sources"
CORPUS_DIR = Path(os.environ.get("REGBASE_CORPUS", ROOT / "corpus"))
TEXT_DIR = CORPUS_DIR / "text"                       # committed extracted text

# Raw bytes can live outside the project tree. That matters when the project
# sits in a synced folder (OneDrive, Dropbox): the extracted text is small and
# worth syncing, but tens of GB of source PDFs are not. Set REGBASE_RAW to a
# local, unsynced directory to split them.
RAW_DIR = Path(os.environ.get("REGBASE_RAW", CORPUS_DIR / "raw"))
MANIFEST = CORPUS_DIR / "manifest.jsonl"
INDEX_DB = CORPUS_DIR / "regbase.sqlite"
PEOPLE_DIR = ROOT / "people"
SCHEMA_DIR = ROOT / "schemas"

for _d in (CORPUS_DIR, RAW_DIR, TEXT_DIR):
    _d.mkdir(parents=True, exist_ok=True)


def _use_utf8_console() -> None:
    """Force UTF-8 on stdout/stderr.

    On Windows, Python writes to the console using the locale code page
    (cp1252 for a US install), so any character outside it - a section symbol,
    an em dash, a curly quote lifted from ordinance text - renders as mojibake
    or raises UnicodeEncodeError mid-report. Regulatory text is full of them.

    errors="replace" is deliberate: a console that still cannot represent a
    character should print a placeholder, never abort a harvest run.
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            if stream and getattr(stream, "encoding", "").lower() not in ("utf-8", "utf8"):
                stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass          # non-reconfigurable stream (pipe, IDE capture): carry on


_use_utf8_console()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def slugify(value: str, maxlen: int = 90) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    value = re.sub(r"[^\w\s-]", "", value).strip().lower()
    value = re.sub(r"[-\s]+", "-", value)
    return value[:maxlen].strip("-") or "untitled"


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


# ---------------------------------------------------------------- registry

@dataclass
class Document:
    title: str
    url: str
    doc_type: str = "regulation"
    format: str = "unknown"
    citation_root: str = ""
    notes: str = ""


@dataclass
class Source:
    id: str
    jurisdiction_level: str
    state: str
    name: str
    documents: list[dict] = field(default_factory=list)
    agency: str = ""
    county: str = ""
    municipality: str = ""
    authority_type: list[str] = field(default_factory=list)
    applies_to: list[str] = field(default_factory=list)
    code_platform: str = "unknown"
    landing_url: str = ""
    permits: list[dict] = field(default_factory=list)
    gis: list[dict] = field(default_factory=list)
    contacts: list[dict] = field(default_factory=list)
    update_watch: dict = field(default_factory=dict)
    confidence: str = "unverified"
    last_reviewed: str = ""
    _file: str = ""

    @property
    def jurisdiction_label(self) -> str:
        if self.municipality:
            return f"{self.municipality}, {self.state}"
        if self.county:
            return f"{self.county} County, {self.state}"
        return f"{self.state} — {self.agency or self.name}"

    def docs(self) -> Iterator[Document]:
        for d in self.documents or []:
            yield Document(
                title=d.get("title", "untitled"),
                url=d.get("url", ""),
                doc_type=d.get("doc_type", "regulation"),
                format=d.get("format", "unknown"),
                citation_root=d.get("citation_root", ""),
                notes=d.get("notes", ""),
            )


_KNOWN_FIELDS = {f for f in Source.__dataclass_fields__ if not f.startswith("_")}


def load_sources(paths: Optional[Iterable[Path]] = None) -> list[Source]:
    """Load every regbase/sources/*.yaml into Source objects."""
    paths = list(paths) if paths else sorted(SOURCES_DIR.glob("*.yaml"))
    out: list[Source] = []
    seen: dict[str, str] = {}
    for p in paths:
        try:
            data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as exc:
            raise SystemExit(f"{p}: invalid YAML: {exc}") from exc
        records = data.get("sources") or []
        for rec in records:
            if not isinstance(rec, dict) or "id" in rec is None:
                continue
            sid = rec.get("id")
            if not sid:
                continue
            if sid in seen:
                raise SystemExit(f"duplicate source id {sid!r} in {p} (also in {seen[sid]})")
            seen[sid] = str(p)
            kwargs = {k: v for k, v in rec.items() if k in _KNOWN_FIELDS}
            kwargs.setdefault("jurisdiction_level", "state")
            kwargs.setdefault("state", "US")
            kwargs.setdefault("name", sid)
            s = Source(**kwargs)
            # POSIX separators: this string is published in web/registry.json,
            # so a build on Windows must not produce a different file than a
            # build on Linux.
            s._file = p.relative_to(ROOT).as_posix()
            out.append(s)
    return out


def validate_sources() -> list[str]:
    """Validate every source file against schemas/source.schema.json."""
    import jsonschema

    schema = json.loads((SCHEMA_DIR / "source.schema.json").read_text(encoding="utf-8"))
    errors: list[str] = []
    for p in sorted(SOURCES_DIR.glob("*.yaml")):
        data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        for rec in data.get("sources") or []:
            try:
                jsonschema.validate(rec, schema)
            except jsonschema.ValidationError as exc:
                loc = "/".join(str(x) for x in exc.absolute_path)
                errors.append(f"{p.name}:{rec.get('id','?')}:{loc}: {exc.message}")
    return errors


# ---------------------------------------------------------------- manifest

def manifest_read() -> dict[str, dict]:
    """key -> record. key is source_id::url."""
    out: dict[str, dict] = {}
    if MANIFEST.exists():
        for line in MANIFEST.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            out[rec["key"]] = rec          # later lines win
    return out


def manifest_append(rec: dict) -> None:
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    with MANIFEST.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, sort_keys=True) + "\n")


def manifest_compact() -> int:
    """Rewrite manifest keeping only the newest record per key."""
    recs = manifest_read()
    lines = [json.dumps(r, sort_keys=True) for _, r in sorted(recs.items())]
    MANIFEST.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return len(lines)


# ---------------------------------------------------------------- http

# The `Mozilla/5.0 (compatible; ...)` prefix is load-bearing, not cargo cult.
# The WAF in front of colorado.gov -- ECMC, CDPHE, PUC and most of the county
# sites -- 403s any User-Agent that does not start with it: 56 of 65 failures
# in a full Colorado harvest were that single check. The `compatible;` form
# still identifies RegBase honestly, so there is no need to pose as a browser.
USER_AGENT = os.environ.get(
    "REGBASE_UA",
    "Mozilla/5.0 (compatible; RegBase/1.0; oil-and-gas regulatory research; "
    "contact: set REGBASE_UA env var)",
)


class Fetcher:
    """Polite HTTP with per-host rate limiting, retries, and conditional GET."""

    def __init__(self, delay: float = 1.0, timeout: int = 60, retries: int = 4):
        import requests

        self.delay = delay
        self.timeout = timeout
        self.retries = retries
        self._last: dict[str, float] = {}
        self.s = requests.Session()
        self.s.headers.update({
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/pdf,*/*",
            "Accept-Language": "en-US,en;q=0.9",
        })

    def _wait(self, host: str) -> None:
        last = self._last.get(host, 0.0)
        gap = time.monotonic() - last
        if gap < self.delay:
            time.sleep(self.delay - gap)
        self._last[host] = time.monotonic()

    def get(self, url: str, etag: str = "", last_modified: str = "", stream: bool = False,
            extra_headers: Optional[dict] = None):
        """Returns a requests.Response, or None on permanent failure.

        Raises nothing; caller inspects .status_code. 304 means unchanged.

        `extra_headers` is for per-request headers a specific API demands —
        Municode's JSON API, for one, 401s without `X-CSRF: 1`.
        """
        import requests
        from urllib.parse import urlsplit

        host = urlsplit(url).netloc
        headers = dict(extra_headers or {})
        if etag:
            headers["If-None-Match"] = etag
        if last_modified:
            headers["If-Modified-Since"] = last_modified

        backoff = 2.0
        for attempt in range(self.retries + 1):
            self._wait(host)
            try:
                r = self.s.get(url, headers=headers, timeout=self.timeout,
                               stream=stream, allow_redirects=True)
            except requests.RequestException as exc:
                if attempt == self.retries:
                    return _FakeResponse(0, str(exc), url)
                time.sleep(backoff)
                backoff *= 2
                continue
            if r.status_code in (429, 500, 502, 503, 504) and attempt < self.retries:
                retry_after = r.headers.get("Retry-After")
                time.sleep(float(retry_after) if (retry_after or "").isdigit() else backoff)
                backoff *= 2
                continue
            return r
        return _FakeResponse(0, "exhausted retries", url)


@dataclass
class _FakeResponse:
    status_code: int
    reason: str
    url: str
    content: bytes = b""
    text: str = ""
    headers: dict = field(default_factory=dict)

    def iter_content(self, chunk_size: int = 8192):
        return iter(())


def egress_ok(probe: str = "https://www.google.com") -> bool:
    """Cheap check for whether general outbound HTTPS is permitted."""
    try:
        import requests

        r = requests.get(probe, timeout=15)
        return r.status_code < 500
    except Exception:
        return False
