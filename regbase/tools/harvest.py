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
import sys
from collections import deque
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit

import common
import extract

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


def store(source: common.Source, doc_title: str, doc_type: str, citation_root: str,
          url: str, resp, *, write_text: bool = True) -> dict:
    """Persist one fetched response and return its manifest record."""
    data = resp.content or b""
    ext = extract.guess_ext(resp.headers.get("Content-Type", ""), url)
    raw_path, txt_path = local_paths(source, url, doc_title, ext)
    digest = common.sha256_bytes(data)

    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes(data)

    text = ""
    if write_text:
        try:
            text = extract.extract(data, ext, url)
        except Exception as exc:                      # extraction must never abort a run
            text = ""
            doc_type = doc_type or "regulation"
            print(f"    ! extract failed for {url}: {exc}", file=sys.stderr)
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
        "raw_path": str(raw_path.relative_to(common.CORPUS_DIR)),
        "text_path": str(txt_path.relative_to(common.CORPUS_DIR)) if text else "",
        "text_chars": len(text),
        "fetched_at": common.now_iso(),
    }


def harvest_documents(sources: list[common.Source], fetcher: common.Fetcher,
                      manifest: dict, *, force: bool, dry_run: bool,
                      limit: int) -> dict[str, int]:
    stats = {"fetched": 0, "unchanged": 0, "failed": 0, "skipped": 0, "text": 0}
    for src in sources:
        docs = list(src.docs())
        if not docs:
            continue
        print(f"\n[{src.state}] {src.jurisdiction_label} — {src.id} ({len(docs)} docs)")
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

            resp = fetcher.get(doc.url, etag=prev.get("etag", ""),
                               last_modified=prev.get("last_modified", ""))
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
                                  dry_run=args.dry_run, limit=args.limit)

    print("\n" + "  ".join(f"{k}={v}" for k, v in stats.items()))
    if not args.dry_run:
        print(f"manifest compacted to {common.manifest_compact()} records")
        print("next: python3 regbase/tools/build_index.py --rebuild")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
