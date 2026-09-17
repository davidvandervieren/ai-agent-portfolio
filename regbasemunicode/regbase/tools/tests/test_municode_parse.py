#!/usr/bin/env python3
"""The Municode payload parsing must survive shapes we have not seen.

The endpoints were discovered by watching a real page's network traffic, but
the JSON field names inside them are undocumented and vary between clients -
some use "Id", some "NodeId", some nest a level deeper. So the client searches
for plausible keys anywhere in the structure rather than assuming one layout.

This exercises that against several shapes, including ones deliberately
different from Greeley's, plus the failure cases: no identifier present, and
a payload carrying no HTML at all.

It does NOT test the live service - no network here. It tests that whatever
comes back is parsed sanely.
"""
from __future__ import annotations

import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

import municode  # noqa: E402


def main() -> int:
    failed = 0

    def check(label, ok):
        nonlocal failed
        print(f"{'PASS' if ok else 'FAIL'}  {label}")
        failed += not ok

    # --- URL parsing -------------------------------------------------------
    s, c, p = municode.parse_url(
        "https://library.municode.com/co/greeley/codes/code_of_ordinances")
    check("url -> state/client/product", (s, c, p) == ("co", "greeley", "code_of_ordinances"))

    s2, c2, _ = municode.parse_url("https://library.municode.com/tx/midland")
    check("url without a product still yields client", (s2, c2) == ("tx", "midland"))

    # --- identifier extraction across differing shapes ---------------------
    shapes = [
        ({"ClientId": 2436}, "flat ClientId"),
        ({"data": {"organization": {"clientId": 2436}}}, "nested clientId"),
        ({"results": [{"Id": 2436, "Name": "Greeley"}]}, "list with Id"),
        ({"Organization": {"id": "2436"}}, "numeric string"),
    ]
    for payload, label in shapes:
        got = municode._first_int(payload, "clientId", "id", "organizationId")
        check(f"clientId found in {label}", got == 2436)

    check("missing identifier returns None",
          municode._first_int({"nothing": "here"}, "clientId") is None)

    # --- table of contents -------------------------------------------------
    toc_payload = {
        "Children": [
            {"Id": "CH18OIGAOP", "Heading": "Chapter 18 - Oil and Gas Operations",
             "Children": [
                 {"Id": "CH18OIGAOP_S18-1PERE", "Heading": "18-1 Permit required"},
                 {"NodeId": "CH18OIGAOP_S18-2SE", "Title": "18-2 Setbacks"},
             ]},
            {"Id": "CH23ZO", "Heading": "Chapter 23 - Zoning"},
        ]
    }

    class FakeClient(municode.Municode):
        def __init__(self, payload):
            self._payload = payload
            self.delay = 0

        def _get(self, path, **params):
            return self._payload

    m = FakeClient(toc_payload)
    ref = municode.CodeRef(state="co", client="greeley", client_id=2436,
                           product_id=18000, job_id=493697)
    nodes = m.toc(ref)
    ids = {n.node_id for n in nodes}
    check("toc finds top-level chapters",
          {"CH18OIGAOP", "CH23ZO"} <= ids)
    check("toc finds nested sections under both key spellings",
          {"CH18OIGAOP_S18-1PERE", "CH18OIGAOP_S18-2SE"} <= ids)
    check("toc carries headings",
          any(n.title.startswith("Chapter 18") for n in nodes))
    check("toc does not duplicate ids", len(ids) == len(nodes))

    # --- content extraction ------------------------------------------------
    setback = ("<h2>18-2 Setbacks</h2><p>No compressor station shall be located "
               "within one thousand (1,000) feet of a platted residential "
               "subdivision.</p>")
    for payload, label in [
        ({"Content": setback}, "Content key"),
        ({"Docs": [{"Html": setback}]}, "nested Docs/Html"),
        ({"a": {"b": {"text": setback}}}, "deeply nested text"),
    ]:
        html = municode.Municode._html_from(payload)
        check(f"html recovered from {label}", "1,000" in html)

    dup = municode.Municode._html_from({"one": setback, "two": setback})
    check("duplicate fragments collapse", dup.count("1,000") == 1)

    check("payload with no html yields empty string",
          municode.Municode._html_from({"count": 3, "ok": True, "msg": "fine"}) == "")

    # Short strings must not be mistaken for content.
    check("short strings are not treated as html",
          municode.Municode._html_from({"x": "<b>hi</b>"}) == "")

    print("\n" + ("payload parsing is shape-tolerant"
                  if not failed else f"{failed} check(s) failed"))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
