#!/usr/bin/env python3
"""Discover how to fetch a Municode code as data instead of a JavaScript shell.

library.municode.com returns a ~6 KB bootstrap page and loads the ordinance
over XHR, so an HTML crawl harvests nothing. The content is reachable, but the
exact API shape has to be confirmed against the live service rather than
assumed - a wrong endpoint baked into the harvester would silently produce
empty codes, which is the failure this whole exercise exists to prevent.

Run this where the network works:

    py regbase\\tools\\municode_probe.py
    py regbase\\tools\\municode_probe.py --url https://library.municode.com/co/greeley/codes/code_of_ordinances

It tries a set of candidate endpoints, reports exactly which respond with
JSON and what shape they return, and prints the recipe that worked. Paste the
output back and the harvester gets a verified Municode handler.

Nothing is written and nothing is changed - this only reads.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from urllib.parse import urlsplit

DEFAULT_URL = "https://library.municode.com/co/greeley/codes/code_of_ordinances"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

HEADERS = {
    "User-Agent": UA,
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://library.municode.com/",
    "Origin": "https://library.municode.com",
}


def parse_target(url: str) -> tuple[str, str]:
    """library.municode.com/<state>/<client>/codes/<product> -> (state, client)."""
    parts = [p for p in urlsplit(url).path.split("/") if p]
    if len(parts) >= 2:
        return parts[0], parts[1]
    return "", ""


def show(label: str, resp) -> dict | list | None:
    ct = resp.headers.get("Content-Type", "")
    ok = resp.status_code == 200
    print(f"  {'OK ' if ok else '   '} {resp.status_code}  {label}")
    print(f"        {resp.url}")
    print(f"        content-type: {ct.split(';')[0]}  bytes: {len(resp.content):,}")
    if not ok or "json" not in ct.lower():
        body = resp.text[:160].replace("\n", " ")
        if body.strip():
            print(f"        body starts: {body}")
        return None
    try:
        data = resp.json()
    except Exception as exc:
        print(f"        ! declared JSON but did not parse: {exc}")
        return None
    if isinstance(data, dict):
        print(f"        keys: {sorted(data.keys())[:12]}")
    elif isinstance(data, list):
        print(f"        list of {len(data)}")
        if data and isinstance(data[0], dict):
            print(f"        first item keys: {sorted(data[0].keys())[:12]}")
    return data


def main() -> int:
    try:
        import requests
    except ImportError:
        print("requests is not installed:  py -m pip install requests")
        return 1

    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", default=DEFAULT_URL,
                    help="a library.municode.com code URL to probe")
    args = ap.parse_args()

    state, client = parse_target(args.url)
    print(f"target: {args.url}")
    print(f"  state={state!r}  client={client!r}\n")

    s = requests.Session()
    s.headers.update(HEADERS)

    def get(url, **kw):
        try:
            return s.get(url, timeout=30, **kw)
        except Exception as exc:
            print(f"  ERR      {url}\n        {type(exc).__name__}: {exc}")
            return None

    print("1. The HTML page itself (confirm it really is a shell)")
    r = get(args.url)
    if r is not None:
        text_len = len(re.sub(r"<[^>]+>", " ", r.text).split())
        print(f"     {r.status_code}  {len(r.content):,} bytes, ~{text_len} words of visible text")
        print(f"     {'CONFIRMED shell - content is not in the HTML' if text_len < 200 else 'has real text - an HTML crawl may work after all'}")
        for pat in (r'clientId["\s:=]+(\d+)', r'productId["\s:=]+(\d+)', r'jobId["\s:=]+([\w-]+)'):
            for m in re.finditer(pat, r.text):
                print(f"     found in page source: {m.group(0)[:60]}")

    print("\n2. Candidate API endpoints")
    candidates = [
        ("client lookup by name",
         f"https://api.municode.com/Clients/name?clientName={client}&stateAbbr={state}"),
        ("client content list",
         f"https://api.municode.com/ClientContent/{client}"),
        ("products for client",
         f"https://api.municode.com/Products/{client}"),
        ("codes content (needs ids)",
         "https://api.municode.com/CodesContent"),
        ("jobs latest",
         "https://api.municode.com/Jobs/latest"),
    ]
    found = {}
    for label, url in candidates:
        r = get(url)
        if r is not None:
            data = show(label, r)
            if data:
                found[label] = (url, data)
        print()

    print("3. What to do next")
    if found:
        print("   These endpoints returned JSON:")
        for label, (url, _) in found.items():
            print(f"     - {label}: {url}")
        print("\n   Paste this whole output back and I will write the verified handler.")
    else:
        print("   None of the candidates returned JSON, so the shape has changed or")
        print("   the service requires headers this probe did not send.")
        print("\n   Authoritative fallback - takes about a minute in your browser:")
        print("     1. Open the code page in Chrome")
        print("     2. F12 -> Network tab -> filter XHR -> reload the page")
        print("     3. Click a request that returns the ordinance text (look for a")
        print("        large JSON response)")
        print("     4. Right-click it -> Copy -> Copy as cURL")
        print("     5. Paste that here")
        print("\n   That gives the exact URL, headers and parameters the site itself")
        print("   uses, which beats any guess.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
