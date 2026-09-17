#!/usr/bin/env python3
"""Fetch Municode ordinances through the API the site itself uses.

Discovered by rendering a page and watching its network calls, not guessed -
an earlier assumption that the host was api.municode.com was wrong. The real
chain, observed on Greeley:

    /localapi/Organizations/GetByUrlEncodedNames/<state>/<client>  -> clientId
    /api/ClientContent/<clientId>                                  -> products
    /api/Products/name?clientId=&productName=                      -> productId
    /api/Jobs/latest/<productId>                                   -> jobId
    /api/codesToc?jobId=&productId=                                -> chapter tree
    /api/CodesContent?jobId=&productId=&nodeId=                    -> text

Two things this buys over browser rendering: it is far faster across the ~50
affected jurisdictions, and codesToc enumerates every chapter, so a whole code
can be harvested instead of a single landing page.

Field names inside those JSON payloads are not documented and may differ
between clients, so the parsing here searches for plausible keys rather than
assuming one shape. Run with --dump to see what a payload actually contains.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from typing import Any, Iterator, Optional
from urllib.parse import quote, urlsplit

BASE = "https://library.municode.com"

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
    "Accept": "application/json, text/plain, */*",
    "Referer": BASE + "/",
}


@dataclass
class CodeRef:
    state: str
    client: str
    client_id: Optional[int] = None
    product_id: Optional[int] = None
    job_id: Optional[int] = None
    product_name: str = ""

    @property
    def resolved(self) -> bool:
        return bool(self.product_id and self.job_id)


@dataclass
class Node:
    node_id: str
    title: str
    depth: int = 0
    children: list = field(default_factory=list)


def parse_url(url: str) -> tuple[str, str, str]:
    """library.municode.com/<state>/<client>/codes/<product> -> parts."""
    parts = [p for p in urlsplit(url).path.split("/") if p]
    state = parts[0] if parts else ""
    client = parts[1] if len(parts) > 1 else ""
    product = parts[3] if len(parts) > 3 else ""
    return state, client, product


def _walk(obj: Any) -> Iterator[dict]:
    """Every dict anywhere in a nested JSON structure."""
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from _walk(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk(v)


def _first_int(obj: Any, *names: str) -> Optional[int]:
    """First integer-ish value under any of *names*, case-insensitively."""
    wanted = {n.lower() for n in names}
    for d in _walk(obj):
        for k, v in d.items():
            if k.lower() in wanted:
                if isinstance(v, int):
                    return v
                if isinstance(v, str) and v.isdigit():
                    return int(v)
    return None


# Municode node ids are hierarchical and self-describing:
#   PTIICOOR_TIT22BUCO                 a title
#   PTIICOOR_TIT22BUCO_CH16OIGAEXWEDR  a chapter under it
#   ..._CH16OIGAEXWEDR_S22-401PU       a section under that
_SECTION_RE = re.compile(r"_S\d", re.I)
_CHAPTER_RE = re.compile(r"_(CH|ART|DIV)[\dA-Z]", re.I)


def is_section(node_id: str) -> bool:
    return bool(_SECTION_RE.search(node_id))


def content_units(nodes: list) -> list:
    """Nodes worth fetching content for, at chapter granularity.

    A chapter's CodesContent carries all of its sections, so fetching per
    chapter needs roughly a tenth of the requests of fetching per section.
    A node qualifies when its children are all sections, or when it is a
    leaf that is not itself a section (a chapter with no sections yet).
    Sections whose parent is not in the set - orphans - are included so
    nothing is dropped.
    """
    by_id = {n.node_id: n for n in nodes}
    units = []
    covered: set = set()
    for n in nodes:
        if is_section(n.node_id):
            continue
        kids = n.children
        if kids and all(is_section(k.node_id) for k in kids):
            units.append(n)
            covered.update(k.node_id for k in kids)
        elif not kids and n.node_id != n.node_id.split("_")[0]:
            units.append(n)
    for n in nodes:
        if is_section(n.node_id) and n.node_id not in covered:
            parent = n.node_id.rsplit("_", 1)[0]
            if parent not in by_id or by_id[parent] not in units:
                units.append(n)
    return units


class BrowserTransport:
    """Issue API calls from inside a rendered Municode page.

    A cold request gets 401 even with the page's cookies, so the site relies
    on something the page establishes at runtime - a token in a header, a
    value set by script. Rather than reverse-engineer it, run fetch() inside
    the page: the request is then the site's own, carrying whatever it needs.

    One page load opens the session; every API call after that is a plain
    fetch through it, so this stays fast across a whole code.
    """

    # Headers the browser sets itself and a fetch() may not override.
    _SKIP = {"host", "content-length", "connection", "accept-encoding",
             "cookie", "origin", "referer", "user-agent"}

    def __init__(self, page_url: str, timeout_ms: int = 45_000):
        import render as render_mod
        from playwright.sync_api import sync_playwright

        self.api_headers: dict[str, str] = {}
        self.observed_ids: dict[str, int] = {}
        self.observed_urls: list[str] = []

        self._pw = sync_playwright().start()
        self._browser, self.browser_used = render_mod._launch(self._pw)
        ctx = self._browser.new_context(user_agent=HEADERS["User-Agent"])
        self.page = ctx.new_page()

        # Watch the page's own API traffic. Its requests succeed where ours
        # 401, so whatever they carry is what we need - and their URLs hold
        # the job/product ids outright.
        self.page.on("request", self._observe)

        self.page.goto(page_url, timeout=timeout_ms, wait_until="domcontentloaded")
        try:
            self.page.wait_for_load_state("networkidle", timeout=timeout_ms // 2)
        except Exception:
            pass
        self.page_html = self.page.content()

    def _observe(self, request) -> None:
        url = request.url
        if "/api/" not in url and "/localapi/" not in url:
            return
        self.observed_urls.append(url)
        if "/api/" in url and not self.api_headers:
            self.api_headers = {k: v for k, v in (request.headers or {}).items()
                                if k.lower() not in self._SKIP}
        for key in ("jobId", "productId", "clientId"):
            m = re.search(rf"[?&]{key}=(\d+)", url, re.I)
            if m and key not in self.observed_ids:
                self.observed_ids[key] = int(m.group(1))

    def get_json(self, url: str) -> Any:
        return self.page.evaluate(
            """async ([u, h]) => {
                 const r = await fetch(u, {credentials: 'include', headers: h});
                 const t = await r.text();
                 if (!r.ok) throw new Error(r.status + ' from ' + u + ': ' + t.slice(0, 120));
                 try { return JSON.parse(t); } catch (e) { throw new Error('non-JSON from ' + u + ': ' + t.slice(0, 120)); }
               }""",
            [url, self.api_headers],
        )

    def close(self) -> None:
        try:
            self._browser.close()
        finally:
            self._pw.stop()


class Municode:
    def __init__(self, delay: float = 1.0, timeout: int = 45,
                 browser_page: str = ""):
        import requests

        self.s = requests.Session()
        self.s.headers.update(HEADERS)
        self.timeout = timeout
        self.delay = delay
        self._last = 0.0
        self._warmed = False
        self.transport: Optional[BrowserTransport] = None
        self.base = BASE
        if browser_page:
            self.transport = BrowserTransport(browser_page, timeout_ms=timeout * 1000)
            self._warmed = True
            parts = urlsplit(browser_page)
            self.base = f"{parts.scheme}://{parts.netloc}"

    def close(self) -> None:
        if self.transport:
            self.transport.close()
            self.transport = None

    def warm(self, page_url: str) -> str:
        """Load the human page first and keep its cookies.

        The API answers 401 to a cold request. A browser reaches it only after
        the page has run, by which point it holds a session cookie and sends
        the page as Referer. Doing the same makes the API answer normally.
        Returns the page HTML, which usually carries the ids as well.
        """
        import time

        self.s.headers["Referer"] = page_url
        try:
            r = self.s.get(page_url, timeout=self.timeout)
            self._last = time.monotonic()
            self._warmed = True
            return r.text if r.status_code == 200 else ""
        except Exception:
            return ""

    @staticmethod
    def ids_from_page(html: str) -> dict:
        """Pull jobId / productId / clientId out of the page source.

        The page has to know them to make its own calls, so they are usually
        embedded. When they are, the whole discovery chain can be skipped -
        fewer requests, and nothing to go wrong.
        """
        out: dict[str, int] = {}
        for key in ("jobId", "productId", "clientId"):
            m = re.search(rf'{key}["\\\s:=]+(\d+)', html, re.I)
            if m:
                out[key] = int(m.group(1))
        return out

    def _get(self, path: str, **params) -> Any:
        import time

        gap = time.monotonic() - self._last
        if gap < self.delay:
            time.sleep(self.delay - gap)
        self._last = time.monotonic()

        url = path if path.startswith("http") else self.base + path
        if self.transport is not None:
            import time
            gap = time.monotonic() - self._last
            if gap < self.delay:
                time.sleep(self.delay - gap)
            self._last = time.monotonic()
            from urllib.parse import urlencode
            full = url + ("?" + urlencode(params) if params else "")
            try:
                return self.transport.get_json(full)
            except Exception as exc:
                raise RuntimeError(str(exc).splitlines()[0][:200])
        r = self.s.get(url, params=params or None, timeout=self.timeout)
        if r.status_code != 200:
            raise RuntimeError(f"{r.status_code} from {r.url}")
        try:
            return r.json()
        except ValueError:
            raise RuntimeError(f"non-JSON from {r.url}: {r.text[:120]}")

    # ---------------------------------------------------------------- resolve

    def resolve(self, state: str, client: str, product_hint: str = "",
                page_url: str = "") -> CodeRef:
        ref = CodeRef(state=state, client=client)

        # Warm the session before touching the API, or it answers 401.
        html = self.transport.page_html if self.transport else ""
        if not self._warmed:
            url = page_url or f"{BASE}/{state}/{client}"
            if product_hint:
                url = f"{BASE}/{state}/{client}/codes/{product_hint}"
            html = self.warm(url)

        # Ids seen in the page's own API calls beat everything: they are the
        # values the site is actually using right now.
        scraped: dict = {}
        if self.transport and self.transport.observed_ids:
            scraped = dict(self.transport.observed_ids)
        elif html:
            scraped = self.ids_from_page(html)
        if scraped.get("jobId") and scraped.get("productId"):
            ref.client_id = scraped.get("clientId")
            ref.product_id = scraped["productId"]
            ref.job_id = scraped["jobId"]
            ref.product_name = product_hint or "(from page)"
            return ref

        org = self._get(f"/localapi/Organizations/GetByUrlEncodedNames/"
                        f"{quote(state)}/{quote(client)}")
        ref.client_id = _first_int(org, "clientId", "id", "organizationId")
        if not ref.client_id:
            raise RuntimeError(f"no clientId in organization payload for "
                               f"{state}/{client}: {json.dumps(org)[:200]}")

        try:
            content = self._get(f"/api/ClientContent/{ref.client_id}")
        except RuntimeError as exc:
            if "401" not in str(exc) and "403" not in str(exc):
                raise
            # The browser also reaches products by name; try that instead.
            name = (product_hint or "code of ordinances").replace("_", " ")
            content = self._get("/api/Products/name", clientId=ref.client_id,
                                productName=name)

        # Prefer a product whose name matches the hint, else the first with an id.
        hint = (product_hint or "").replace("_", " ").lower()
        best = None
        for d in _walk(content):
            name = ""
            for k, v in d.items():
                if k.lower() in ("productname", "name", "title") and isinstance(v, str):
                    name = v
                    break
            pid = _first_int(d, "productId", "id")
            if not pid:
                continue
            if hint and hint in name.lower():
                best = (pid, name)
                break
            if best is None:
                best = (pid, name)
        if not best:
            raise RuntimeError(f"no product found for clientId {ref.client_id}")
        ref.product_id, ref.product_name = best

        job = self._get(f"/api/Jobs/latest/{ref.product_id}")
        ref.job_id = _first_int(job, "jobId", "id")
        if not ref.job_id:
            raise RuntimeError(f"no jobId for productId {ref.product_id}")
        return ref

    # -------------------------------------------------------------------- toc

    def toc(self, ref: CodeRef, node_id: str = "") -> list[Node]:
        """Table of contents; with node_id, the children of that node."""
        params = {"jobId": ref.job_id, "productId": ref.product_id}
        if node_id:
            params["nodeId"] = node_id
        data = self._get("/api/codesToc", **params)
        nodes: list[Node] = []
        seen: set[str] = set()
        for d in _walk(data):
            nid = None
            for k, v in d.items():
                if k.lower() in ("id", "nodeid") and isinstance(v, str) and v:
                    nid = v
                    break
            if not nid or nid in seen:
                continue
            title = ""
            for k, v in d.items():
                if k.lower() in ("heading", "title", "name") and isinstance(v, str):
                    title = v
                    break
            seen.add(nid)
            nodes.append(Node(node_id=nid, title=title or nid))
        return nodes

    def expand(self, ref: CodeRef, *, max_requests: int = 3000,
               on_progress=None) -> list[Node]:
        """Every node in the code, walking the tree breadth-first.

        The root call returns only top-level titles; chapters and sections
        are fetched per node. Node ids are hierarchical (TIT18 under
        PTIICOOR), so a child that comes back identical to its parent, or a
        request that returns nothing new, ends that branch.
        """
        root = self.toc(ref)
        seen = {n.node_id: n for n in root}
        queue = [n for n in root if n.node_id != str(ref.product_id)]
        requests = 1
        for n in root:
            n.depth = 0
        while queue and requests < max_requests:
            node = queue.pop(0)
            if is_section(node.node_id):
                continue            # a section has no children; skip the probe
            try:
                kids = self.toc(ref, node.node_id)
            except RuntimeError:
                continue
            requests += 1
            new = [k for k in kids if k.node_id not in seen]
            for k in new:
                k.depth = node.depth + 1
                seen[k.node_id] = k
                node.children.append(k)
                queue.append(k)
            if on_progress:
                on_progress(node, len(new), requests, len(seen))
        return list(seen.values())

    def fetch_code(self, ref: CodeRef, *, match: str = "", on_progress=None):
        """Yield (node, heading_path, html) for every content unit in the code.

        `match` is a regex applied to the heading path; with it, only
        matching chapters are fetched - useful for pulling just the oil and
        gas, zoning and land use material out of a large code.
        """
        nodes = self.expand(ref, on_progress=on_progress)
        by_id = {n.node_id: n for n in nodes}

        def path_of(n) -> str:
            parts, cur = [], n.node_id
            while cur:
                node = by_id.get(cur)
                if node and node.title and node.title != cur:
                    parts.append(node.title)
                cur = cur.rsplit("_", 1)[0] if "_" in cur else ""
            return " > ".join(reversed(parts))

        rx = re.compile(match, re.I) if match else None
        for unit in content_units(nodes):
            heading = path_of(unit)
            if rx and not rx.search(heading):
                continue
            try:
                html = self.content(ref, unit.node_id)
            except RuntimeError as exc:
                yield unit, heading, ""
                continue
            yield unit, heading, html

    # ---------------------------------------------------------------- content

    def content(self, ref: CodeRef, node_id: str = "") -> str:
        params = {"jobId": ref.job_id, "productId": ref.product_id}
        if node_id:
            params["nodeId"] = node_id
        data = self._get("/api/CodesContent", **params)
        return self._html_from(data)

    @staticmethod
    def _html_from(data: Any) -> str:
        """Concatenate every HTML-looking string in the payload, in order."""
        chunks: list[str] = []
        for d in _walk(data):
            for k, v in d.items():
                if not isinstance(v, str) or len(v) < 40:
                    continue
                if k.lower() in ("content", "html", "text", "docs", "body") or "<" in v:
                    if re.search(r"<[a-zA-Z/]", v):
                        chunks.append(v)
        # De-duplicate while preserving order.
        out, seen = [], set()
        for c in chunks:
            if c not in seen:
                seen.add(c)
                out.append(c)
        return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", required=True,
                    help="a library.municode.com code URL")
    ap.add_argument("--dump", action="store_true",
                    help="print raw JSON payloads (to learn the shapes)")
    ap.add_argument("--toc", action="store_true", help="list the chapter tree")
    ap.add_argument("--expand", action="store_true",
                    help="walk the whole tree to its sections (many requests)")
    ap.add_argument("--node", default="", help="fetch one node's content")
    ap.add_argument("--delay", type=float, default=1.0)
    ap.add_argument("--plain", action="store_true",
                    help="use plain HTTP instead of calling through a rendered "
                         "page (known to get 401 from this API)")
    args = ap.parse_args()

    state, client, product = parse_url(args.url)
    print(f"state={state!r} client={client!r} product={product!r}\n")

    try:
        m = Municode(delay=args.delay,
                     browser_page="" if args.plain else args.url)
    except Exception as exc:
        print(f"could not open a browser session: {exc}")
        print("install playwright (py -m pip install playwright) or pass --plain")
        return 1
    print(f"transport : {'browser (' + m.transport.browser_used + ')' if m.transport else 'plain http'}")
    if m.transport:
        t = m.transport
        print(f"observed  : {len(t.observed_urls)} API call(s) by the page; "
              f"ids {t.observed_ids or 'none'}; "
              f"headers reused: {sorted(t.api_headers) or 'none'}")
    try:
        return _run(m, args, state, client, product)
    finally:
        m.close()


def _run(m: "Municode", args, state: str, client: str, product: str) -> int:
    try:
        ref = m.resolve(state, client, product, page_url=args.url)
    except Exception as exc:
        print(f"resolve failed: {exc}")
        if args.dump:
            try:
                print(json.dumps(m._get(
                    f"/localapi/Organizations/GetByUrlEncodedNames/{state}/{client}"),
                    indent=1)[:2000])
            except Exception as e2:
                print(f"  (dump also failed: {e2})")
        return 1

    print(f"clientId  : {ref.client_id}")
    print(f"productId : {ref.product_id}  ({ref.product_name})")
    print(f"jobId     : {ref.job_id}")

    nodes: list[Node] = []
    if args.toc or args.expand or not args.node:
        try:
            nodes = m.toc(ref)
            print(f"\ntoc       : {len(nodes)} top-level node(s)")
            for n in nodes[:25]:
                print(f"   {n.node_id[:44]:<46} {n.title[:60]}")
            if len(nodes) > 25:
                print(f"   ... and {len(nodes) - 25} more")
        except Exception as exc:
            print(f"\ntoc failed: {exc}")

    if args.expand:
        def progress(node, new, reqs, total):
            if new:
                print(f"   +{new:<3} under {node.title[:50]:<52} ({total} nodes, {reqs} req)")
        try:
            allnodes = m.expand(ref, on_progress=progress)
            leaves = [n for n in allnodes if not n.children]
            deepest = max((n.depth for n in allnodes), default=0)
            print(f"\nexpanded  : {len(allnodes)} node(s), {len(leaves)} leaves, "
                  f"depth {deepest}")
            hits = [n for n in allnodes if re.search(r"oil|gas|pipeline", n.title, re.I)]
            if hits:
                print("   oil & gas related:")
                for n in hits[:15]:
                    print(f"     {n.node_id[:44]:<46} {n.title[:60]}")
        except Exception as exc:
            print(f"\nexpand failed: {exc}")

    node = args.node
    if not node and nodes:
        # The root returns nothing; pick the first title that is not the
        # product itself, so the content path is actually exercised.
        for n in nodes:
            if n.node_id != str(ref.product_id) and re.search(r"TIT|CH|ART", n.node_id):
                node = n.node_id
                break
        if node:
            print(f"\nnode      : {node}  (first title; pass --node to choose)")
    try:
        html = m.content(ref, node)
        import extract as _extract
        text = _extract.html_to_text(html) if html else ""
        print(f"\ncontent   : {len(html):,} bytes html -> {len(text):,} chars text")
        if text:
            print(f"\n{text[:600]}")
    except Exception as exc:
        print(f"\ncontent failed: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
