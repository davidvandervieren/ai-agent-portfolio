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


class Municode:
    def __init__(self, delay: float = 1.0, timeout: int = 45):
        import requests

        self.s = requests.Session()
        self.s.headers.update(HEADERS)
        self.timeout = timeout
        self.delay = delay
        self._last = 0.0

    def _get(self, path: str, **params) -> Any:
        import time

        gap = time.monotonic() - self._last
        if gap < self.delay:
            time.sleep(self.delay - gap)
        self._last = time.monotonic()

        url = path if path.startswith("http") else BASE + path
        r = self.s.get(url, params=params or None, timeout=self.timeout)
        if r.status_code != 200:
            raise RuntimeError(f"{r.status_code} from {r.url}")
        try:
            return r.json()
        except ValueError:
            raise RuntimeError(f"non-JSON from {r.url}: {r.text[:120]}")

    # ---------------------------------------------------------------- resolve

    def resolve(self, state: str, client: str, product_hint: str = "") -> CodeRef:
        ref = CodeRef(state=state, client=client)

        org = self._get(f"/localapi/Organizations/GetByUrlEncodedNames/"
                        f"{quote(state)}/{quote(client)}")
        ref.client_id = _first_int(org, "clientId", "id", "organizationId")
        if not ref.client_id:
            raise RuntimeError(f"no clientId in organization payload for "
                               f"{state}/{client}: {json.dumps(org)[:200]}")

        content = self._get(f"/api/ClientContent/{ref.client_id}")

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

    def toc(self, ref: CodeRef) -> list[Node]:
        data = self._get("/api/codesToc", jobId=ref.job_id, productId=ref.product_id)
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
    ap.add_argument("--node", default="", help="fetch one node's content")
    ap.add_argument("--delay", type=float, default=1.0)
    args = ap.parse_args()

    state, client, product = parse_url(args.url)
    print(f"state={state!r} client={client!r} product={product!r}\n")

    m = Municode(delay=args.delay)
    try:
        ref = m.resolve(state, client, product)
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

    if args.toc or not args.node:
        try:
            nodes = m.toc(ref)
            print(f"\ntoc       : {len(nodes)} node(s)")
            for n in nodes[:25]:
                print(f"   {n.node_id[:44]:<46} {n.title[:60]}")
            if len(nodes) > 25:
                print(f"   ... and {len(nodes) - 25} more")
        except Exception as exc:
            print(f"\ntoc failed: {exc}")

    node = args.node
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
