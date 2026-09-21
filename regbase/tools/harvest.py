#!/usr/bin/env python3
"""Download every document in the RegBase source registry and extract its text.

Two modes:

  documents  (default)  Fetch each explicit `documents[].url` in the registry.
                        Precise, polite, and immediately useful — these are the
                        rule PDFs, form packets, and code landing pages that
                        were curated by hand.

  crawl      (--crawl)  Walk a jurisdiction's online code from `landing_url`,
                        staying on-host, following only links that look like
                        code content for that publishing platform. This is how
                        a whole municipal code gets pulled down.

Raw bytes land in corpus/raw/ (gitignored). Extracted text lands in
corpus/text/ (committed) so diffs of actual regulatory language are reviewable
and so the index can be rebuilt without re-downloading.

Every fetch is recorded in corpus/manifest.jsonl with a sha256, so re-runs are
incremental and change detection is exact.
"""
from __future__ import annotations

import argparse
import re
import time
import sys
from collections import deque
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit

import common
import extract
import render as render_mod

# --------------------------------------------------------------- platforms
#
# Per-publishing-platform crawl hints. `include` links are followed; `exclude`
# links never are. These patterns are written from the public URL shapes of
# each platform, but they are UNVALIDATED against live sites in this
# environment (outbound HTTPS is blocked here) — expect to tune them on the
# first real run and check the per-platform counts in the run summary.

PLATFORMS: dict[str, dict] = {
    "municode": {
        "include": [r"/codes/", r"/regulations/", r"nodeId=", r"CodesContent"],
        "exclude": [r"/print", r"\.pdf$", r"login", r"/help"],
        "notes": "library.municode.com renders via XHR; the JSON behind it is "
                 "api.municode.com/codesContent?jobId=&nodeId=&productId=. If "
                 "the HTML crawl comes back thin, switch to that API.",
    },
    "american_legal": {
        "include": [r"codelibrary\.amlegal\.com/codes/", r"/latest/"],
        "exclude": [r"/print", r"/search", r"\.pdf$"],
        "notes": "American Legal Publishing. Whole-code downloads are sometimes "
                 "offered at /codes/<client>/latest/<code>/0-0-0-1.",
    },
    "ecode360": {
        "include": [r"ecode360\.com/\w+", r"#\d"],
        "exclude": [r"/print", r"/pdf", r"/search"],
        "notes": "General Code eCode360. Section anchors are stable ids; the "
                 "'Download' menu exposes per-chapter PDFs.",
    },
    "code_publishing": {
        "include": [r"codepublishing\.com", r"/html/", r"\.html$"],
        "exclude": [r"/search", r"/print"],
        "notes": "Code Publishing Co. Codes are static HTML trees — the "
                 "friendliest platform to crawl.",
    },
    "franklin_legal": {
        "include": [r"z2\.franklinlegal", r"/codes?/"],
        "exclude": [r"/search"],
        "notes": "Franklin Legal Publishing (common for small Texas cities). "
                 "Often a Z2 viewer that needs session cookies.",
    },
    "sterling": {"include": [r"sterlingcodifiers\.com"], "exclude": [r"/search"], "notes": ""},
    "quality_code": {"include": [r"qcode\.us"], "exclude": [r"/search"], "notes": ""},
    "ecfr": {
        "include": [r"ecfr\.gov/current/title-\d+"],
        "exclude": [],
        "notes": "Prefer the eCFR bulk API: ecfr.gov/api/versioner/v1/full/"
                 "<date>/title-<n>.xml — one request per title instead of a crawl.",
    },
    "self_hosted": {"include": [], "exclude": [r"/search", r"\?print", r"mailto:"], "notes": ""},
    "state_register": {"include": [], "exclude": [r"/search"], "notes": ""},
    "unknown": {"include": [], "exclude": [r"/search"], "notes": ""},
    "none": {"include": [], "exclude": [], "notes": ""},
}

THIN_REPORT: list[tuple[str, str, str, str]] = []
MUNICODE_FAILURES: list[tuple[str, str, str, str]] = []   # source, heading, url, error

_BINARY_EXT = re.compile(r"\.(pdf|docx?|xlsx?|zip|jpg|jpeg|png|gif|mp4|mp3)$", re.I)
_SKIP_SCHEMES = ("mailto:", "tel:", "javascript:", "data:", "#")


def canonical(url: str) -> str:
    """Drop fragments and normalize, so the same page is not fetched twice."""
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, parts.query, ""))


def same_host(a: str, b: str) -> bool:
    ha, hb = urlsplit(a).netloc.lower(), urlsplit(b).netloc.lower()
    ha, hb = ha.removeprefix("www."), hb.removeprefix("www.")
    return ha == hb


def local_paths(source: common.Source, url: str, title: str, ext: str) -> tuple[Path, Path]:
    stem = common.slugify(title or Path(urlsplit(url).path).stem or "document")
    digest = common.sha256_bytes(url.encode())[:8]        # disambiguates same-titled docs
    sub = Path(source.state) / common.slugify(source.id)
    raw = common.RAW_DIR / sub / f"{stem}-{digest}{ext}"
    txt = common.TEXT_DIR / sub / f"{stem}-{digest}.md"
    return raw, txt


def manifest_path(path: Path, base: Path) -> str:
    """Path as recorded in the manifest.

    Relative to `base` when it lives there, absolute otherwise. REGBASE_RAW
    can point the raw corpus outside the project entirely - which is the
    recommended setup when the project sits in a synced folder - so raw files
    are frequently NOT under CORPUS_DIR. build_index._resolve() accepts both
    forms. POSIX separators keep a manifest written on Windows readable on
    Linux.
    """
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return str(path)


# A JavaScript-shell page: plenty of HTML delivered, almost no readable text
# once it is stripped. Municode's library.municode.com serves exactly this -
# roughly 6 KB of bootstrap returning 16 characters of text - because the code
# itself arrives later over XHR. Recording those as harvested documents is
# worse than failing: an empty file titled "Chapter 18 - Oil and Gas
# Operations" indexes as a citable chunk with nothing behind it.
THIN_TEXT_CHARS = 200        # below this, treat the extraction as suspect
THIN_RATIO_BYTES = 2000      # ...but only when the response was substantial


def is_thin_extraction(raw_bytes: int, text_chars: int) -> bool:
    return text_chars < THIN_TEXT_CHARS and raw_bytes > THIN_RATIO_BYTES


def write_resilient(path: Path, data: bytes, *, attempts: int = 3) -> str:
    """Write bytes, retrying briefly. Returns "" on success, else the error.

    On Windows, antivirus real-time scanning and Controlled Folder Access can
    hold a newly created file open or refuse the write outright - PDFs
    especially. A short retry clears the transient case. A genuine denial must
    never end a harvest run: one unwritable file killed a run that had already
    fetched 531 documents successfully.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    delay = 0.4
    for attempt in range(attempts):
        try:
            path.write_bytes(data)
            return ""
        except OSError as exc:
            if attempt == attempts - 1:
                return f"{type(exc).__name__}: {exc}"
            time.sleep(delay)
            delay *= 2
    return "unreachable"


def needs_render(source: common.Source, mode: str) -> bool:
    """Should this source be fetched with a browser?

    "auto" renders only the platforms known to build their pages client-side,
    which keeps the slow path off the ~90% of sources that are plain HTML.
    """
    if mode == "never":
        return False
    if mode == "always":
        return True
    return source.code_platform in render_mod.JS_RENDERED_PLATFORMS


def fetch_document(fetcher: common.Fetcher, url: str, prev: dict, use_render: bool):
    """One fetch, browser-rendered or plain. Returns a response-like object."""
    if not use_render:
        return fetcher.get(url, etag=prev.get("etag", ""),
                           last_modified=prev.get("last_modified", ""))
    # A rendered fetch cannot use conditional GET - there is no validator for
    # a DOM built after load - so it always re-renders. That is the cost of
    # reaching content a plain fetch cannot see at all.
    result = render_mod.render(url)
    if result.error:
        print(f"    ! render failed ({result.error}); falling back to plain fetch",
              file=sys.stderr)
        return fetcher.get(url)
    return render_mod.RenderedResponse(result)


def store(source: common.Source, doc_title: str, doc_type: str, citation_root: str,
          url: str, resp, *, write_text: bool = True) -> dict:
    """Persist one fetched response and return its manifest record."""
    data = resp.content or b""
    ext = extract.guess_ext(resp.headers.get("Content-Type", ""), url)
    raw_path, txt_path = local_paths(source, url, doc_title, ext)
    digest = common.sha256_bytes(data)

    raw_error = write_resilient(raw_path, data)
    if raw_error:
        print(f"    ! could not write raw file ({raw_error}); continuing on the "
              f"in-memory copy so text is still extracted", file=sys.stderr)

    text = ""
    thin = False
    if write_text:
        try:
            text = extract.extract(data, ext, url)
        except Exception as exc:                      # extraction must never abort a run
            text = ""
            doc_type = doc_type or "regulation"
            print(f"    ! extract failed for {url}: {exc}", file=sys.stderr)
        if text and is_thin_extraction(len(data), len(text)):
            print(f"    ! THIN: {len(data):,}B returned only {len(text)} chars of "
                  f"text - almost certainly JavaScript-rendered, not harvested. "
                  f"Not writing a text file.", file=sys.stderr)
            thin = True
            text = ""
        if text:
            txt_path.parent.mkdir(parents=True, exist_ok=True)
            header = extract.front_matter(
                source_id=source.id,
                jurisdiction=source.jurisdiction_label,
                state=source.state,
                county=source.county,
                municipality=source.municipality,
                agency=source.agency,
                title=doc_title,
                doc_type=doc_type,
                citation_root=citation_root,
                url=url,
                sha256=digest,
                fetched_at=common.now_iso(),
            )
            txt_path.write_text(f"{header}\n\n{text}\n", encoding="utf-8")

    return {
        "key": f"{source.id}::{url}",
        "source_id": source.id,
        "state": source.state,
        "jurisdiction": source.jurisdiction_label,
        "title": doc_title,
        "doc_type": doc_type,
        "citation_root": citation_root,
        "url": url,
        "final_url": getattr(resp, "url", url),
        "http_status": resp.status_code,
        "content_type": resp.headers.get("Content-Type", ""),
        "bytes": len(data),
        "sha256": digest,
        "etag": resp.headers.get("ETag", ""),
        "last_modified": resp.headers.get("Last-Modified", ""),
        "raw_path": "" if raw_error else manifest_path(raw_path, common.RAW_DIR),
        "raw_write_error": raw_error,
        "text_path": manifest_path(txt_path, common.TEXT_DIR) if text else "",
        "text_chars": len(text),
        "thin_extraction": thin,
        "fetched_at": common.now_iso(),
    }



# ------------------------------------------------------------- municode api

MUNICODE_HOST = "library.municode.com"     # overridable for tests


class _ApiResponse:
    """A response-like wrapper so store() can persist API-fetched HTML."""

    def __init__(self, url: str, html: str):
        self.status_code = 200
        self.content = html.encode("utf-8", errors="replace")
        self.text = html
        self.url = url
        self.headers = {"Content-Type": "text/html; charset=utf-8"}
        self.reason = ""

    def iter_content(self, chunk_size: int = 8192):
        return iter(())


def _municode_page(source: common.Source) -> str:
    """The library.municode.com page to open a session on, if any."""
    for d in source.docs():
        if MUNICODE_HOST in (d.url or ""):
            return d.url.split("?")[0]
    if MUNICODE_HOST in (source.landing_url or ""):
        return source.landing_url.split("?")[0]
    return ""


def _municode_root(page: str) -> str:
    """The code's canonical page: host/state/client/codes/product, lower-cased,
    without a job id or query. Registry URLs vary in case and some carry a
    job id in the path; both name the same code."""
    import municode
    from urllib.parse import urlsplit
    u = urlsplit(page)
    state, client, product = municode.parse_url(page)
    return f"{u.scheme}://{u.netloc}/{state}/{client}/codes/{product}".lower()


def harvest_municode_source(source: common.Source, *, delay: float,
                            match: str = "", dry_run: bool = False) -> dict:
    """Pull a jurisdiction's entire code through Municode's own API.

    One browser session per jurisdiction, then chapter-by-chapter fetches
    through it. Each chapter becomes a document whose URL is the same
    ?nodeId= form a person would see in the browser, so citations resolve.
    """
    import municode

    page = _municode_page(source)
    stats = {"chapters": 0, "chars": 0, "failed": 0, "skipped": 0, "empty": 0}
    if not page:
        return stats
    if dry_run:
        print(f"    would harvest the whole code via API from {page}")
        return stats

    try:
        client = municode.Municode(delay=delay, browser_page=page)
    except Exception as exc:
        print(f"    ! could not open Municode session ({exc}); falling back to "
              f"document fetch", file=sys.stderr)
        stats["failed"] += 1
        return stats
    try:
        state, city, product = municode.parse_url(page)
        ref = client.resolve(state, city, product, page_url=page)
        t = client.transport

        # A whole-code harvest replaces this source's corpus outright. Stale
        # shells from earlier per-document fetches and per-section duplicates
        # from an earlier version of this path would otherwise sit beside the
        # fresh chapters and be indexed alongside them.
        import shutil
        sub = Path(source.state) / common.slugify(source.id)
        for d in (common.TEXT_DIR / sub, common.RAW_DIR / sub):
            if d.exists():
                shutil.rmtree(d, ignore_errors=True)
        dropped = common.manifest_drop(source.id)
        if dropped:
            print(f"    cleared {dropped} earlier record(s) for a fresh whole-code harvest")
        print(f"    api session: job {ref.job_id} product {ref.product_id} "
              f"(headers reused: {', '.join(sorted(t.api_headers)) or 'none'})")

        def progress(node, new, reqs, total):
            if reqs % 50 == 0:
                print(f"    ... {total} nodes, {reqs} requests", flush=True)

        for unit, heading, html, err in client.fetch_code(ref, match=match,
                                                          on_progress=progress):
            url = f"{_municode_root(page)}?nodeId={unit.fetch_id or unit.node_id}"
            if err:
                stats["failed"] += 1
                MUNICODE_FAILURES.append((source.id, heading or unit.title, url, err))
                print(f"  ! failed  {(heading or unit.title)[-60:]}: {err[:90]}")
                continue
            if not html:
                stats["empty"] += 1
                continue
            rec = store(source, unit.title or unit.node_id, "code",
                        heading or source.name, url, _ApiResponse(url, html))
            common.manifest_append(rec)
            if rec.get("thin_extraction"):
                stats["skipped"] += 1
                continue
            stats["chapters"] += 1
            stats["chars"] += rec["text_chars"]
            print(f"  + {rec['text_chars']:>8,} chars  {(heading or unit.title)[-70:]}")
    except Exception as exc:
        print(f"    ! municode api failed: {exc}", file=sys.stderr)
        stats["failed"] += 1
    finally:
        client.close()
    return stats


def harvest_documents(sources: list[common.Source], fetcher: common.Fetcher,
                      manifest: dict, *, force: bool, dry_run: bool,
                      limit: int, render_mode: str = "auto",
                      municode_api: bool = True, municode_match: str = "",
                      delay_s: float = 1.0) -> dict[str, int]:
    stats = {"fetched": 0, "unchanged": 0, "failed": 0, "skipped": 0, "text": 0,
             "thin": 0}
    for src in sources:
        docs = list(src.docs())
        if not docs:
            continue
        use_render = needs_render(src, render_mode)
        api_page = _municode_page(src) if (municode_api and
                                           src.code_platform == "municode") else ""
        tag = "  [municode api]" if api_page else ("  [rendered]" if use_render else "")
        print(f"\n[{src.state}] {src.jurisdiction_label} — {src.id} "
              f"({len(docs)} docs){tag}")
        if api_page:
            mstats = harvest_municode_source(src, delay=delay_s, match=municode_match,
                                             dry_run=dry_run)
            stats["api_chapters"] = stats.get("api_chapters", 0) + mstats["chapters"]
            stats["api_failed"] = stats.get("api_failed", 0) + mstats["failed"]
            stats["api_empty"] = stats.get("api_empty", 0) + mstats["empty"]
            if mstats["chapters"]:
                extra = []
                if mstats["empty"]:
                    extra.append(f"{mstats['empty']} empty")
                if mstats["failed"]:
                    extra.append(f"{mstats['failed']} failed")
                print(f"    = {mstats['chapters']} chapter(s), "
                      f"{mstats['chars']:,} chars via API"
                      + (f"  ({', '.join(extra)})" if extra else ""))
            # The API covered the code page and everything under it; anything
            # else on this source - a city's own oil & gas page, say - still
            # goes through the normal fetch.
            root = _municode_root(api_page)
            docs = [d for d in docs
                    if not (d.url or "").lower().startswith(root)]
            if not docs:
                continue
        for doc in docs:
            if limit and stats["fetched"] >= limit:
                return stats
            if not doc.url or doc.url.startswith(_SKIP_SCHEMES):
                stats["skipped"] += 1
                continue
            key = f"{src.id}::{doc.url}"
            prev = manifest.get(key, {})
            if prev and not force and prev.get("http_status") == 200:
                pass  # still re-check with a conditional GET below

            if dry_run:
                print(f"  would GET {doc.url}")
                stats["skipped"] += 1
                continue

            resp = fetch_document(fetcher, doc.url, prev, use_render)
            if resp.status_code == 304:
                print(f"  = 304 {doc.title[:60]}")
                stats["unchanged"] += 1
                continue
            if resp.status_code != 200:
                print(f"  ! {resp.status_code} {doc.url}")
                common.manifest_append({
                    "key": key, "source_id": src.id, "url": doc.url,
                    "http_status": resp.status_code, "title": doc.title,
                    "error": getattr(resp, "reason", ""), "fetched_at": common.now_iso(),
                })
                stats["failed"] += 1
                continue

            rec = store(src, doc.title, doc.doc_type, doc.citation_root, doc.url, resp)
            common.manifest_append(rec)
            stats["fetched"] += 1
            if rec["text_chars"]:
                stats["text"] += 1
            if rec.get("thin_extraction"):
                stats["thin"] = stats.get("thin", 0) + 1
                THIN_REPORT.append((src.id, src.code_platform, doc.title, doc.url))
            changed = "" if prev.get("sha256") == rec["sha256"] else "  *CHANGED*" if prev else ""
            print(f"  + {rec['bytes']:>9,}B  {rec['text_chars']:>7,} chars  "
                  f"{doc.title[:55]}{changed}")
    return stats


def harvest_crawl(sources: list[common.Source], fetcher: common.Fetcher,
                  manifest: dict, *, max_pages: int, max_depth: int,
                  dry_run: bool) -> dict[str, int]:
    stats = {"pages": 0, "failed": 0, "sources": 0}
    for src in sources:
        start = src.landing_url
        if not start:
            continue
        rules = PLATFORMS.get(src.code_platform, PLATFORMS["unknown"])
        include = [re.compile(p, re.I) for p in rules["include"]]
        exclude = [re.compile(p, re.I) for p in rules["exclude"]]

        print(f"\n[crawl {src.code_platform}] {src.jurisdiction_label} <- {start}")
        if rules.get("notes"):
            print(f"    note: {rules['notes']}")
        if dry_run:
            print(f"    would crawl up to {max_pages} pages, depth {max_depth}")
            continue

        seen: set[str] = set()
        queue: deque[tuple[str, int]] = deque([(canonical(start), 0)])
        pages = 0
        while queue and pages < max_pages:
            url, depth = queue.popleft()
            if url in seen:
                continue
            seen.add(url)

            prev = manifest.get(f"{src.id}::{url}", {})
            resp = fetcher.get(url, etag=prev.get("etag", ""),
                               last_modified=prev.get("last_modified", ""))
            if resp.status_code == 304:
                continue
            if resp.status_code != 200:
                stats["failed"] += 1
                continue

            title = f"{src.name} — {Path(urlsplit(url).path).name or 'index'}"
            rec = store(src, title, "code", src.name, url, resp)
            common.manifest_append(rec)
            pages += 1
            stats["pages"] += 1

            if depth >= max_depth or _BINARY_EXT.search(url):
                continue
            ctype = resp.headers.get("Content-Type", "")
            if "html" not in ctype.lower():
                continue
            for href in _links(resp.content, url):
                if href in seen or not same_host(href, start):
                    continue
                if any(rx.search(href) for rx in exclude):
                    continue
                if include and not any(rx.search(href) for rx in include):
                    continue
                queue.append((href, depth + 1))

        print(f"    crawled {pages} pages")
        stats["sources"] += 1
    return stats


def _links(content: bytes, base: str) -> list[str]:
    from bs4 import BeautifulSoup

    try:
        soup = BeautifulSoup(content.decode("utf-8", errors="replace"), "lxml")
    except Exception:
        return []
    out = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith(_SKIP_SCHEMES):
            continue
        out.append(canonical(urljoin(base, href)))
    return out


def select(sources: list[common.Source], args) -> list[common.Source]:
    out = sources
    if args.state:
        want = {s.upper() for s in args.state}
        out = [s for s in out if s.state.upper() in want]
    if args.level:
        out = [s for s in out if s.jurisdiction_level in set(args.level)]
    if args.source_id:
        out = [s for s in out if s.id in set(args.source_id)]
    if args.county:
        want = {c.lower() for c in args.county}
        out = [s for s in out if s.county.lower() in want]
    if args.platform:
        out = [s for s in out if s.code_platform in set(args.platform)]
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--state", action="append", help="CO WY NM UT TX US (repeatable)")
    ap.add_argument("--county", action="append")
    ap.add_argument("--level", action="append",
                    choices=["federal", "state", "county", "municipal",
                             "special_district", "tribal"])
    ap.add_argument("--source-id", action="append")
    ap.add_argument("--platform", action="append")
    ap.add_argument("--crawl", action="store_true",
                    help="crawl each jurisdiction's code from landing_url "
                         "instead of only fetching listed documents")
    ap.add_argument("--max-pages", type=int, default=400, help="per source, crawl mode")
    ap.add_argument("--max-depth", type=int, default=4, help="crawl mode")
    ap.add_argument("--delay", type=float, default=1.0, help="seconds between hits per host")
    ap.add_argument("--limit", type=int, default=0, help="stop after N documents (0=all)")
    ap.add_argument("--force", action="store_true", help="ignore ETag/Last-Modified")
    ap.add_argument("--render", choices=["auto", "always", "never"], default="auto",
                    help="use a real browser for JavaScript-rendered platforms. "
                         "auto (default) renders only Municode, eCode360, "
                         "Franklin Legal and Sterling; always renders everything "
                         "(slow); never disables it")
    ap.add_argument("--no-municode-api", action="store_true",
                    help="do not pull whole codes through Municode's API "
                         "(falls back to per-document fetch / render)")
    ap.add_argument("--municode-match", default="",
                    help="regex on chapter headings; only matching chapters are "
                         "fetched from Municode, e.g. 'oil|gas|pipeline|zoning|land use'")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--compact", action="store_true", help="compact the manifest and exit")
    args = ap.parse_args()

    if args.compact:
        print(f"manifest compacted to {common.manifest_compact()} records")
        return 0

    if not args.dry_run and not common.egress_ok():
        print(
            "\nOutbound HTTPS is blocked in this environment, so nothing can be "
            "downloaded.\n\n"
            "  * In Claude Code on the web: open the environment's settings and "
            "set network\n"
            "    access to allow outbound traffic, then re-run.\n"
            "  * Or run this script on a machine with normal internet access:\n"
            "      pip install -r regbase/tools/requirements.txt\n"
            "      python3 regbase/tools/harvest.py --state CO\n\n"
            "Use --dry-run to see exactly what would be fetched.\n",
            file=sys.stderr,
        )
        return 2

    sources = select(common.load_sources(), args)
    if not sources:
        print("no sources matched those filters", file=sys.stderr)
        return 1

    fetcher = common.Fetcher(delay=args.delay)
    manifest = common.manifest_read()
    print(f"{len(sources)} sources selected; {len(manifest)} manifest records on disk")

    if args.crawl:
        stats = harvest_crawl(sources, fetcher, manifest, max_pages=args.max_pages,
                              max_depth=args.max_depth, dry_run=args.dry_run)
    else:
        stats = harvest_documents(sources, fetcher, manifest, force=args.force,
                                  dry_run=args.dry_run, limit=args.limit,
                                  render_mode=args.render,
                                  municode_api=not args.no_municode_api,
                                  municode_match=args.municode_match,
                                  delay_s=args.delay)

    print("\n" + "  ".join(f"{k}={v}" for k, v in stats.items()))

    if THIN_REPORT:
        from collections import Counter
        by_platform = Counter(p for _, p, _, _ in THIN_REPORT)
        print(f"\n{len(THIN_REPORT)} document(s) returned almost no text despite a "
              f"substantial response.")
        print("These are NOT harvested - the page renders its content with "
              "JavaScript, so nothing was indexed.")
        print("  by platform: " + ", ".join(f"{k}={v}" for k, v in by_platform.most_common()))
        if by_platform.get("municode"):
            print("\n  Municode pages render their text with JavaScript, so a plain "
                  "\n  fetch sees only the shell. These are harvested whole through "
                  "\n  the API instead (default); a thin Municode entry here means a "
                  "\n  registry document URL that did not match the source's code page.")
        report = common.CORPUS_DIR / "reports" / "thin_extractions.txt"
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(
            "\n".join(f"{sid}\t{plat}\t{title}\t{url}"
                      for sid, plat, title, url in THIN_REPORT) + "\n",
            encoding="utf-8")
        print(f"\n  full list: {report}")
    if MUNICODE_FAILURES:
        report = common.CORPUS_DIR / "reports" / "municode_failures.txt"
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(
            "\n".join(f"{sid}\t{heading}\t{url}\t{err}"
                      for sid, heading, url, err in MUNICODE_FAILURES) + "\n",
            encoding="utf-8")
        print(f"\n{len(MUNICODE_FAILURES)} Municode chapter(s) failed to fetch; "
              f"re-run the source to retry.\n  full list: {report}")
    if not args.dry_run:
        print(f"manifest compacted to {common.manifest_compact()} records")
        print("next: python3 regbase/tools/build_index.py --rebuild")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
