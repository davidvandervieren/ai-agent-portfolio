#!/usr/bin/env python3
"""Fixture tests for check_updates.py's body normalization.

These run with no network. The load-bearing assertion is the first one: two
renders of the SAME page that differ only in a <script> nonce and a rendered
"last updated" timestamp must hash IDENTICALLY, or every weekly run reports
every government CMS page as changed and the whole tool becomes noise.

Run:  python3 regbase/tools/tests/test_normalize.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from check_updates import (  # noqa: E402
    normalize_body,
    normalize_html,
    scrub_text_volatiles,
)

FAILURES: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail and not ok else ""))
    if not ok:
        FAILURES.append(name)


# --------------------------------------------------------------------------
# 1. THE ONE THAT MATTERS: nonce + rendered timestamp must not move the hash
# --------------------------------------------------------------------------

PAGE = """<!DOCTYPE html>
<html><head>
  <meta charset="utf-8">
  <meta name="csrf-token" content="{csrf}">
  <script nonce="{nonce}">window.__BUILD__="{nonce}";dataLayer.push({{t:{epoch}}});</script>
  <style>.a{{color:#fff}}</style>
</head>
<body>
  <!-- rendered by cms node {node} at {stamp} -->
  <h1>Chapter 23 — Oil and Gas Facility Regulations</h1>
  <p>Section 23-4-30. A gathering pipeline shall maintain a setback of 500 feet
     from any occupied structure, effective January 15, 2021.</p>
  <input type="hidden" name="__VIEWSTATE" value="{viewstate}">
  <input type="hidden" name="__RequestVerificationToken" value="{csrf}">
  <link rel="stylesheet" href="/css/site.css?v={epoch}">
  <footer>Last updated: {stamp} | Visitors: {hits}</footer>
</body></html>
"""

a = PAGE.format(csrf="9f13ab7c22d4", nonce="abc123XYZ", epoch="1757000000",
                node="web07", stamp="September 4, 2026 3:04 PM",
                viewstate="/wEPDwUKLTE2NDA5NTIzNw9kFgICAw9kFgI=", hits="12,345")
b = PAGE.format(csrf="0011ffee5522", nonce="zzz987QQQ", epoch="1757600111",
                node="web02", stamp="September 11, 2026 9:12 AM",
                viewstate="/wEPDwUJODc2NTQzMjEwZBYCAgMPZBYC", hits="12,911")

na = normalize_body(a.encode(), "text/html; charset=utf-8", "https://x.gov/code")
nb = normalize_body(b.encode(), "text/html; charset=utf-8", "https://x.gov/code")

check("identical content with rotating nonce/timestamp hashes identically",
      na.sha256 == nb.sha256,
      f"\n  A={na.sha256}\n  B={nb.sha256}\n  A_text={na.hash_text!r}\n  B_text={nb.hash_text!r}")
check("raw bytes DO differ (so the test is actually testing something)",
      a.encode() != b.encode())
check("normalizer selected html", na.normalizer == "html", na.normalizer)
check("substantive text survives normalization",
      "500 feet" in na.hash_text and "23-4-30" in na.hash_text, na.hash_text[:200])

# --------------------------------------------------------------------------
# 2. A real regulatory edit MUST still register
# --------------------------------------------------------------------------

c = a.replace("500 feet", "2,000 feet")
nc = normalize_body(c.encode(), "text/html; charset=utf-8", "https://x.gov/code")
check("a substantive setback change DOES move the hash", nc.sha256 != na.sha256)

# --------------------------------------------------------------------------
# 3. Bare effective dates are preserved on purpose (false positive > false negative)
# --------------------------------------------------------------------------

d = a.replace("effective January 15, 2021", "effective March 1, 2027")
nd = normalize_body(d.encode(), "text/html; charset=utf-8", "https://x.gov/code")
check("a changed EFFECTIVE date still moves the hash", nd.sha256 != na.sha256)

# --------------------------------------------------------------------------
# 4. Individual scrubber behaviours
# --------------------------------------------------------------------------

check("script contents removed", "dataLayer" not in na.hash_text)
check("style contents removed", "color:#fff" not in na.hash_text)
check("html comment removed", "web07" not in na.hash_text and "cms node" not in na.hash_text)
check("viewstate removed", "wEPDwUKLTE2NDA5NTIzNw" not in na.hash_text)
check("csrf meta removed", "9f13ab7c22d4" not in na.hash_text)
check("visitor counter removed", "12,345" not in na.hash_text)
check("cache-busting query string removed", "1757000000" not in na.hash_text)

check("whitespace re-wrap alone does not move the hash",
      normalize_body(a.replace("\n", "\n   ").encode(), "text/html", "u").sha256 == na.sha256)

check("bare clock time scrubbed",
      scrub_text_volatiles("Meeting at 3:04 PM") == scrub_text_volatiles("Meeting at 9:12 AM"))
check("iso datetime scrubbed",
      scrub_text_volatiles("x 2026-09-04T03:04:05Z y")
      == scrub_text_volatiles("x 2026-09-11T09:12:00Z y"))
check("render timer scrubbed",
      scrub_text_volatiles("Page generated in 0.013 seconds")
      == scrub_text_volatiles("Page generated in 1.902 seconds"))
check("epoch-length digit run masked", "<NUM>" in scrub_text_volatiles("id 1757000000123"))
check("long hex / uuid masked",
      "<HEX>" in scrub_text_volatiles("req 3f2a9c8e1b7d4a5f6e0c2b1a9d8e7f60"))

# sitemap lastmod churn must not register
sm_a = "<urlset><url><loc>https://x.gov/a</loc><lastmod>2026-09-04</lastmod></url></urlset>"
sm_b = "<urlset><url><loc>https://x.gov/a</loc><lastmod>2026-09-11</lastmod></url></urlset>"
check("sitemap <lastmod> churn suppressed", normalize_html(sm_a) == normalize_html(sm_b))
check("sitemap new <loc> still detected",
      normalize_html(sm_a) != normalize_html(sm_a.replace("/a<", "/b<")))

# json endpoint volatile keys
j1 = b'{"currentVersion":11.2,"timestamp":1757000000,"layers":[{"id":0,"name":"Flowlines"}]}'
j2 = b'{"currentVersion":11.3,"timestamp":1757600111,"layers":[{"id":0,"name":"Flowlines"}]}'
j3 = b'{"currentVersion":11.2,"timestamp":1757000000,"layers":[{"id":0,"name":"Gathering"}]}'
check("json volatile keys ignored",
      normalize_body(j1, "application/json", "u.json").sha256
      == normalize_body(j2, "application/json", "u.json").sha256)
check("json substantive change detected",
      normalize_body(j1, "application/json", "u.json").sha256
      != normalize_body(j3, "application/json", "u.json").sha256)

# --------------------------------------------------------------------------
# 5. PDF: hash the extracted TEXT, not the bytes — producers rewrite
#    /CreationDate, /ModDate and /ID on every regeneration
# --------------------------------------------------------------------------

def _mkpdf(text: str, stamp: str) -> bytes:
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
    ]
    stream = b"BT /F1 12 Tf 72 720 Td (" + text.encode() + b") Tj ET"
    objs.append(b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream")
    objs.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    objs.append(("<< /CreationDate (D:%s) /ModDate (D:%s) >>" % (stamp, stamp)).encode())
    out, offs = b"%PDF-1.4\n", []
    for i, o in enumerate(objs, 1):
        offs.append(len(out))
        out += b"%d 0 obj\n" % i + o + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    for off in offs:
        out += b"%010d 00000 n \n" % off
    out += (b"trailer\n<< /Size %d /Root 1 0 R /Info 6 0 R /ID [<AB12> <%s>] >>\n"
            b"startxref\n%d\n%%%%EOF" % (len(objs) + 1, stamp.encode()[:4], xref))
    return out


pdf_a = _mkpdf("Setback of 500 feet required for gathering lines.", "20260904030405")
pdf_b = _mkpdf("Setback of 500 feet required for gathering lines.", "20260911091200")
pdf_c = _mkpdf("Setback of 2000 feet required for gathering lines.", "20260904030405")
pa, pb, pc = (normalize_body(x, "application/pdf", "https://x.gov/rule.pdf")
              for x in (pdf_a, pdf_b, pdf_c))
check("pdf bytes differ after re-export (test is meaningful)", pdf_a != pdf_b)
check("pdf normalizer extracts text", pa.normalizer == "pdf_text", pa.normalizer)
check("re-exported identical PDF hashes identically", pa.sha256 == pb.sha256)
check("substantive PDF edit moves the hash", pc.sha256 != pa.sha256)

print()
if FAILURES:
    print(f"{len(FAILURES)} FAILURE(S): " + ", ".join(FAILURES))
    raise SystemExit(1)
print("all normalization fixtures passed")
