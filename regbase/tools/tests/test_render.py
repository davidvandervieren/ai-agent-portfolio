#!/usr/bin/env python3
"""Browser rendering must recover content a plain fetch cannot see.

Municode, eCode360 and Franklin Legal serve a bootstrap page and load the
ordinance over XHR. A plain fetch returns ~6 KB of chrome and 16 characters of
text, which is how roughly forty Colorado municipalities harvested empty while
appearing to succeed.

This serves a fixture that behaves the same way - the ordinance arrives only
after a script runs - and asserts that the plain path misses the operative
language while the rendered path captures it and survives extraction.

Skips cleanly when playwright or a browser is unavailable, since the harvester
falls back to a plain fetch in that case.
"""
from __future__ import annotations

import http.server
import json
import socket
import sys
import threading
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

SETBACK = ("No compressor station shall be located within one thousand (1,000) "
           "feet of a platted residential subdivision.")

PAGE = """<html><head><title>Municipal Code Library</title></head><body>
<div id="app">Loading</div>
<script>
setTimeout(function () {
  fetch('code.json').then(r => r.json()).then(d => {
    document.getElementById('app').innerHTML =
      '<h1>' + d.title + '</h1>' +
      d.sections.map(s => '<h2>' + s.heading + '</h2><p>' + s.body + '</p>').join('');
  });
}, 100);
</script></body></html>"""

CODE = {"title": "Chapter 18 - Oil and Gas Operations",
        "sections": [
            {"heading": "18-1 Permit required",
             "body": "No person shall construct or operate a compressor station "
                     "within the city without first obtaining an oil and gas "
                     "operations permit issued under this chapter."},
            {"heading": "18-2 Setbacks", "body": SETBACK},
            {"heading": "18-3 Noise",
             "body": "Sound levels attributable to the facility shall not exceed "
                     "fifty-five (55) dBA at the nearest residential property "
                     "line between 7:00 p.m. and 7:00 a.m."},
        ]}


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/code.json"):
            body, ctype = json.dumps(CODE).encode(), "application/json"
        else:
            body, ctype = PAGE.encode(), "text/html"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def main() -> int:
    import extract, render as render_mod

    port = free_port()
    srv = http.server.HTTPServer(("127.0.0.1", port), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{port}/index.html"

    failed = 0
    try:
        # The plain path must miss it - that is the bug being guarded against.
        import requests
        raw = requests.get(url, proxies={"http": None, "https": None}).text
        plain = extract.html_to_text(raw)
        ok = "1,000" not in plain
        print(f"{'PASS' if ok else 'FAIL'}  plain fetch misses the setback rule "
              f"({len(plain)} chars extracted)")
        failed += not ok

        result = render_mod.render(url, timeout_ms=30_000)
        if result.error:
            print(f"SKIP  no browser available: {result.error}")
            print("      harvester falls back to a plain fetch in this case")
            return 0

        checks = [
            ("render reports success", result.ok),
            ("rendered text is substantial", result.text_chars >= 300),
        ]
        resp = render_mod.RenderedResponse(result)
        text = extract.extract(resp.content, ".html", url)
        checks += [
            ("extraction recovers the setback rule", "1,000" in text),
            ("extraction keeps the chapter heading",
             "Oil and Gas Operations" in text),
            ("all three sections survive",
             all(h in text for h in ("18-1", "18-2", "18-3"))),
            ("rendered text far exceeds plain", len(text) > len(plain)),
            ("response looks like requests.Response",
             resp.status_code == 200 and bool(resp.content)),
        ]
        for label, ok in checks:
            print(f"{'PASS' if ok else 'FAIL'}  {label}")
            failed += not ok

        print(f"\n  plain: {len(plain)} chars   rendered: {len(text)} chars"
              f"   browser: {result.browser_used}")
    finally:
        srv.shutdown()

    print("\n" + ("rendering recovers JavaScript-delivered ordinances"
                  if not failed else f"{failed} check(s) failed"))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
