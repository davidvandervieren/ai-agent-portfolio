#!/usr/bin/env python3
"""Fetch pages that build themselves with JavaScript.

Municode, eCode360 and the Franklin Legal Z2 viewer all serve a small
bootstrap page and load the ordinance over XHR. A plain HTTP fetch gets ~6 KB
of chrome and 16 characters of text, which is why roughly forty Colorado
municipalities harvested empty. Rendering the page in a real browser solves
all of those platforms at once, rather than reverse-engineering each one's
private API.

The browser is found rather than downloaded. On Windows that usually means
using the Chrome or Edge already installed, so no `playwright install` step is
needed:

    py -m pip install playwright
    py regbase\\tools\\render.py --url https://library.municode.com/co/greeley/codes/code_of_ordinances

Used by harvest.py via --render.
"""
from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass, field
from typing import Optional

# Platforms known to render their content client-side.
JS_RENDERED_PLATFORMS = {"municode", "ecode360", "franklin_legal", "sterling"}

# A rendered page should carry real text. Below this we are still looking at a
# shell, so waiting longer is worth a try before giving up.
MIN_RENDERED_CHARS = 400
DEFAULT_TIMEOUT_MS = 45_000


@dataclass
class RenderResult:
    url: str
    status_code: int
    html: str = ""
    text_chars: int = 0
    error: str = ""
    browser_used: str = ""
    xhr_json: list = field(default_factory=list)   # captured API responses

    @property
    def ok(self) -> bool:
        return self.status_code == 200 and not self.error


def _launch(p, headless: bool = True):
    """Find a usable Chromium. Prefers a bundled build, falls back to the
    browsers the user already has - Chrome and Edge are on virtually every
    Windows machine, which avoids a 150 MB download."""
    attempts: list[tuple[str, dict]] = []

    root = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
    if root and os.path.isdir(root):
        for entry in sorted(os.listdir(root), reverse=True):
            for rel in ("chrome-linux/chrome", "chrome-win/chrome.exe",
                        "chrome-mac/Chromium.app/Contents/MacOS/Chromium"):
                cand = os.path.join(root, entry, rel)
                if os.path.exists(cand):
                    attempts.append((f"bundled:{entry}", {"executable_path": cand}))
                    break

    attempts += [
        ("playwright default", {}),
        ("system chrome", {"channel": "chrome"}),
        ("system edge", {"channel": "msedge"}),
    ]

    errors = []
    for label, kwargs in attempts:
        try:
            args = [
                "--no-sandbox",
                "--disable-dev-shm-usage",
                # Silence the browser's own phone-home traffic: it is unrelated
                # to fetching an ordinance and fails noisily on restricted
                # networks.
                "--disable-background-networking",
                "--disable-component-update",
                "--disable-sync",
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-domain-reliability",
                "--metrics-recording-only",
            ]
            return p.chromium.launch(headless=headless, args=args, **kwargs), label
        except Exception as exc:
            errors.append(f"{label}: {str(exc).splitlines()[0][:90]}")
    raise RuntimeError("no usable browser found:\n  " + "\n  ".join(errors))


def render(url: str, *, timeout_ms: int = DEFAULT_TIMEOUT_MS, headless: bool = True,
           capture_xhr: bool = False, wait_selector: str = "") -> RenderResult:
    """Load *url* in a browser and return the DOM after scripts have run."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return RenderResult(url, 0, error="playwright not installed "
                                          "(py -m pip install playwright)")

    captured: list = []
    try:
        with sync_playwright() as p:
            browser, label = _launch(p, headless=headless)
            try:
                ctx = browser.new_context(
                    user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                "AppleWebKit/537.36 (KHTML, like Gecko) "
                                "Chrome/124.0 Safari/537.36"),
                    viewport={"width": 1400, "height": 2000},
                )
                page = ctx.new_page()

                if capture_xhr:
                    def on_response(resp):
                        ct = (resp.headers or {}).get("content-type", "")
                        if "json" in ct.lower() and resp.request.resource_type in ("xhr", "fetch"):
                            try:
                                captured.append({"url": resp.url,
                                                 "status": resp.status,
                                                 "bytes": len(resp.body() or b"")})
                            except Exception:
                                pass
                    page.on("response", on_response)

                resp = page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")
                status = resp.status if resp else 0

                # Let the XHR content arrive, then confirm real text landed.
                try:
                    page.wait_for_load_state("networkidle", timeout=timeout_ms // 2)
                except Exception:
                    pass
                if wait_selector:
                    try:
                        page.wait_for_selector(wait_selector, timeout=timeout_ms // 2)
                    except Exception:
                        pass
                try:
                    page.wait_for_function(
                        f"document.body && document.body.innerText.length > {MIN_RENDERED_CHARS}",
                        timeout=timeout_ms // 3)
                except Exception:
                    pass    # report what we got rather than failing outright

                html = page.content()
                text_chars = len(page.inner_text("body") or "")
                return RenderResult(url, status, html=html, text_chars=text_chars,
                                    browser_used=label, xhr_json=captured)
            finally:
                browser.close()
    except Exception as exc:
        return RenderResult(url, 0, error=f"{type(exc).__name__}: {exc}".splitlines()[0][:200])


class RenderedResponse:
    """Quacks like requests.Response so harvest.store() needs no changes."""

    def __init__(self, r: RenderResult):
        self.status_code = r.status_code if r.ok else (r.status_code or 0)
        self.content = r.html.encode("utf-8", errors="replace")
        self.text = r.html
        self.url = r.url
        self.headers = {"Content-Type": "text/html; charset=utf-8"}
        self.reason = r.error
        self.render = r

    def iter_content(self, chunk_size: int = 8192):
        return iter(())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", required=True)
    ap.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_MS)
    ap.add_argument("--show-xhr", action="store_true",
                    help="list the JSON API calls the page makes")
    ap.add_argument("--headed", action="store_true", help="show the browser window")
    ap.add_argument("--out", help="write the rendered HTML here")
    args = ap.parse_args()

    r = render(args.url, timeout_ms=args.timeout, headless=not args.headed,
               capture_xhr=args.show_xhr)

    print(f"url     : {r.url}")
    print(f"browser : {r.browser_used or '(none)'}")
    print(f"status  : {r.status_code}")
    print(f"text    : {r.text_chars:,} chars")
    if r.error:
        print(f"error   : {r.error}")
        return 1
    verdict = ("looks like real content" if r.text_chars >= MIN_RENDERED_CHARS
               else "STILL A SHELL - content did not arrive")
    print(f"verdict : {verdict}")

    if args.show_xhr:
        print(f"\nJSON API calls made by the page ({len(r.xhr_json)}):")
        for x in sorted(r.xhr_json, key=lambda d: -d["bytes"])[:15]:
            print(f"  {x['status']}  {x['bytes']:>9,}B  {x['url'][:130]}")

    if args.out:
        from pathlib import Path
        Path(args.out).write_text(r.html, encoding="utf-8")
        print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
