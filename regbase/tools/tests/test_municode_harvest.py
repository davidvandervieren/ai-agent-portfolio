#!/usr/bin/env python3
"""Whole-code harvesting through Municode's API, end to end, against a local
stand-in that behaves like the live site did on Greeley:

  * the page's own script calls the API with an x-csrf header, and the API
    answers 401 to anything without it;
  * codesToc returns only top-level titles until asked for a node's children;
  * CodesContent needs a nodeId and carries a chapter's sections together.

Asserts that chapters land as documents with heading-path citations, that
sections are never probed for children, that non-Municode documents on the
same source still go through the normal fetch, and that the run summary
counts the chapters.
"""
from __future__ import annotations

import http.server
import json
import os
import socket
import sys
import tempfile
import threading
from pathlib import Path
from urllib.parse import parse_qs, urlparse

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

TREE = {
    "": [{"Id": "18000", "Heading": "Municipal Code"},
         {"Id": "PTIICOOR_TIT22BUCO", "Heading": "Title 22 - BUILDINGS AND CONSTRUCTION"},
         {"Id": "PTIICOOR_TIT24DECO", "Heading": "Title 24 - DEVELOPMENT CODE"}],
    "PTIICOOR_TIT22BUCO": [
        {"Id": "PTIICOOR_TIT22BUCO_CH16OIGAEXWEDR",
         "Heading": "CHAPTER 16. - OIL AND GAS EXPLORATION WELL DRILLING"}],
    "PTIICOOR_TIT22BUCO_CH16OIGAEXWEDR": [
        {"Id": "PTIICOOR_TIT22BUCO_CH16OIGAEXWEDR_S22-401PU", "Heading": "Sec. 22-401. - Purpose"},
        {"Id": "PTIICOOR_TIT22BUCO_CH16OIGAEXWEDR_S22-402SE", "Heading": "Sec. 22-402. - Setbacks"}],
    # Title 24 comes back the way the live site served Greeley: the chapter
    # holds an article AND direct sections, and one section is listed under
    # the title itself, as if flattened.
    "PTIICOOR_TIT24DECO": [
        {"Id": "PTIICOOR_TIT24DECO_CH11SUST", "Heading": "CHAPTER 11. - SUPPLEMENTAL STANDARDS"},
        {"Id": "PTIICOOR_TIT24DECO_CH11SUST_S24-1103NO", "Heading": "Sec. 24-1103. - Noise."},
        # a reserved chapter the API answers with nothing, and one the API
        # answers with an error: neither is a chapter, only one is a failure
        {"Id": "PTIICOOR_TIT24DECO_CH12RE", "Heading": "CHAPTER 12. - RESERVED"},
        {"Id": "PTIICOOR_TIT24DECO_CH13BR", "Heading": "CHAPTER 13. - BROKEN"}],
    "PTIICOOR_TIT24DECO_CH11SUST": [
        {"Id": "PTIICOOR_TIT24DECO_CH11SUST_ARTIGE", "Heading": "ARTICLE I. - GENERALLY"},
        {"Id": "PTIICOOR_TIT24DECO_CH11SUST_S24-1102OIGA", "Heading": "Sec. 24-1102. - Oil and gas."}],
    "PTIICOOR_TIT24DECO_CH11SUST_ARTIGE": [
        {"Id": "PTIICOOR_TIT24DECO_CH11SUST_ARTIGE_S24-1101PU", "Heading": "Sec. 24-1101. - Purpose."}],
}
CONTENT = {
    "PTIICOOR_TIT22BUCO_CH16OIGAEXWEDR":
        "<h2>Sec. 22-401. - Purpose</h2><p>This chapter governs oil and gas exploration "
        "well drilling within the city. " * 3 +
        "</p><h2>Sec. 22-402. - Setbacks</h2><p>No well or compressor shall be located "
        "within one thousand (1,000) feet of a platted residential subdivision.</p>",
    "PTIICOOR_TIT24DECO_CH11SUST":
        "<h2>Sec. 24-1102. - Oil and gas.</h2><p>Oil and gas facilities are subject to a "
        "use by special review in every zone district of the city. " * 3 + "</p>"
        "<h2>Sec. 24-1103. - Noise.</h2><p>Noise from any facility shall not exceed "
        "fifty-five dBA at the property line between 7 p.m. and 7 a.m. " * 2 + "</p>",
    "PTIICOOR_TIT24DECO_CH11SUST_ARTIGE":
        "<h2>Sec. 24-1101. - Purpose.</h2><p>This article states the purpose of the "
        "supplemental standards and how they are to be applied and construed. " * 3 + "</p>",
}
PAGE = (b"<html><body><h1>Code Library</h1><script>"
        b"fetch('/api/codesToc?jobId=493697&productId=18000',{headers:{'x-csrf':'tok'}});"
        b"</script></body></html>")
PLAIN = b"<html><body><h1>Oil & Gas | Erie</h1><p>" + b"The Town of Erie regulates oil and gas facilities through its Unified Development Code. " * 6 + b"</p></body></html>"

probed: list[str] = []


fetched: list[str] = []


def chapter_of(node: str) -> str:
    """Municode answers with the enclosing chapter for any node asked."""
    while node and node not in CONTENT:
        node = node.rsplit("_", 1)[0] if "_" in node else ""
    return node


class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        u = urlparse(self.path); q = parse_qs(u.query)
        if u.path.startswith("/api/"):
            if self.headers.get("x-csrf") != "tok":
                self.send_response(401); self.end_headers(); self.wfile.write(b"unauthorized"); return
            node = q.get("nodeId", [""])[0]
            if node.startswith("PTIICOOR_TIT24DECO_CH13BR") and "CodesContent" in u.path:
                self.send_response(500); self.end_headers(); self.wfile.write(b"boom"); return
            if "codesToc" in u.path:
                probed.append(node)
                body = json.dumps({"Children": TREE.get(node, [])}).encode()
            else:
                fetched.append(node)
                body = json.dumps({"Docs": [{"Html": CONTENT.get(chapter_of(node), "")}]}).encode()
            ctype = "application/json"
        elif u.path.startswith("/plain"):
            body, ctype = PLAIN, "text/html"
        else:
            body, ctype = PAGE, "text/html"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers(); self.wfile.write(body)

    def log_message(self, *a): pass


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0)); return s.getsockname()[1]


def main() -> int:
    tmp = tempfile.mkdtemp(prefix="regbase-mc-")
    os.environ["REGBASE_CORPUS"] = str(Path(tmp) / "corpus")
    os.environ["REGBASE_RAW"] = str(Path(tmp) / "raw")
    os.environ["NO_PROXY"] = "127.0.0.1"; os.environ["no_proxy"] = "127.0.0.1"

    import common, harvest, municode
    try:
        import playwright  # noqa: F401
    except ImportError:
        print("SKIP  playwright not installed"); return 0

    port = free_port()
    srv = http.server.HTTPServer(("127.0.0.1", port), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{port}"
    harvest.MUNICODE_HOST = f"127.0.0.1:{port}"

    src = common.Source(
        id="co-greeley-municode", jurisdiction_level="municipal", state="CO",
        municipality="Greeley", name="Greeley Municipal Code", code_platform="municode",
        landing_url=f"{base}/co/greeley/codes/code_of_ordinances",
        documents=[
            # the registry's first URL carries a job id in its path, as Greeley's does
            {"title": "Chapter 16 - Oil and Gas", "url": f"{base}/co/greeley/codes/code_of_ordinances/493697?nodeId=PTIICOOR_TIT22BUCO_CH16OIGAEXWEDR", "doc_type": "code", "format": "html"},
            # the registry sometimes carries the same page in a different case
            {"title": "Chapter 18 - Oil and Gas Operations", "url": f"{base}/CO/Greeley/codes/Code_of_Ordinances?nodeId=PTIICOOR_TIT24DECO_CH11SUST", "doc_type": "code", "format": "html"},
            {"title": "Oil & Gas | Erie-style page", "url": f"{base}/plain", "doc_type": "guidance", "format": "html"},
        ])

    failed = 0
    def check(label, ok):
        nonlocal failed
        print(f"{'PASS' if ok else 'FAIL'}  {label}"); failed += not ok

    stale_dir = common.TEXT_DIR / "CO" / "co-greeley-municode"
    stale_dir.mkdir(parents=True, exist_ok=True)
    stale = stale_dir / "chapter-18-oil-and-gas-operations-deadbeef.md"
    stale.write_text("---\ntitle: stale shell\n---\n\nMunicode Library\n", encoding="utf-8")
    common.manifest_append({"key": "co-greeley-municode::stale", "source_id": "co-greeley-municode",
                            "url": "stale", "http_status": 200, "text_path": "CO/co-greeley-municode/chapter-18-oil-and-gas-operations-deadbeef.md"})

    fetcher = common.Fetcher(delay=0)
    fetcher.s.trust_env = False
    try:
        stats = harvest.harvest_documents([src], fetcher, {}, force=True, dry_run=False,
                                          limit=0, render_mode="never",
                                          municode_api=True, delay_s=0)
    finally:
        srv.shutdown()

    text_dir = common.TEXT_DIR / "CO" / "co-greeley-municode"
    files = sorted(text_dir.glob("*.md")) if text_dir.exists() else []
    bodies = {f.name: f.read_text(encoding="utf-8") for f in files}

    check("three units harvested via API (2 chapters + 1 article)", stats.get("api_chapters") == 3)
    check("no section was ever fetched for content",
          not any(municode.is_section(n) for n in fetched))
    check("stale shell from an earlier fetch was removed", not stale.exists())
    check("stale manifest record was dropped",
          "co-greeley-municode::stale" not in common.manifest_read())
    import hashlib
    distinct = {hashlib.sha256(b.split("---", 2)[-1].encode()).hexdigest() for b in bodies.values()}
    check("no two files carry the same body", len(distinct) == len(bodies))
    check("the broken chapter is the one API failure", stats.get("api_failed") == 1)
    check("the reserved chapter counts as empty, not failed", stats.get("api_empty") == 1)
    check("failure is named for the report",
          any("CHAPTER 13" in h and "500" in e for _, h, _, e in harvest.MUNICODE_FAILURES))
    check("sections were never probed for children",
          not any(municode.is_section(n) for n in probed))
    check("chapter text files written", len(files) == 4)   # 2 chapters + article + plain page
    ch16 = next((b for b in bodies.values() if "22-402" in b), "")
    check("chapter 16 content includes its sections", "1,000" in ch16 and "22-401" in ch16)
    check("citation carries the heading path",
          "Title 22 - BUILDINGS AND CONSTRUCTION > CHAPTER 16." in ch16)
    check("document url is the browser's ?nodeId form, without a job id",
          "/co/greeley/codes/code_of_ordinances?nodeId=PTIICOOR_TIT22BUCO_CH16OIGAEXWEDR" in ch16
          and "493697?nodeId" not in ch16)
    check("non-Municode document still fetched normally",
          any("Town of Erie regulates" in b for b in bodies.values()))
    check("Municode-hosted documents not fetched twice, whatever their case",
          stats["fetched"] == 1)

    # The harvested chapters must reach the index, not just the disk.
    import build_index
    con = build_index.connect(Path(tmp) / "index.sqlite", rebuild=True)
    build_index.upsert_sources(con, [src])
    istats = build_index.index_documents(con, [src], common.manifest_read())
    hits = con.execute("SELECT COUNT(*) FROM chunks WHERE text LIKE '%22-402%'").fetchone()[0]
    con.close()
    check("harvested chapters are indexed beside the registry's documents",
          istats.get("harvested") == 2 and istats["chunked"] == 4 and istats["missing_text"] == 0)
    check("a chapter the registry never listed is searchable", hits >= 1)

    print("\n" + ("whole-code Municode harvest works end to end"
                  if not failed else f"{failed} check(s) failed"))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
