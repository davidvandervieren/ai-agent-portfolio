#!/usr/bin/env python3
"""Generate a draft Form 1.9 Pre-Project Regulatory Review from a KML/KMZ.

    python3 regbase/tools/review.py project.kmz \
        --project-name "Vantom Silo Station" --reviewer "David Van der Vieren" \
        --asset midstream_pipeline --asset compressor_station \
        --state CO --county Arapahoe \
        --out reviews/

Produces, side by side:
    <name>.review.json   conforms to schemas/review.schema.json (interchange)
    <name>.md            readable draft for editing
    <name>.doc           opens in Word with the form's layout intact

The output is a DRAFT. Every permit, cost, and timeline is pulled from the
registry with its confidence attached, and anything the registry cannot answer
is emitted as an explicit blank with a note — never filled in from guesswork.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

import common
import kmlgeo

# Asset types whose presence pulls in a whole class of requirements regardless
# of what the registry record says explicitly.
ALWAYS_STATE_AUTHORITIES = {
    "midstream_pipeline": ["pipeline_safety", "oil_gas_conservation", "roads_row"],
    "produced_water_line": ["pipeline_safety", "oil_gas_conservation", "water_quality"],
    "swd_well": ["underground_injection", "oil_gas_conservation", "water_quality"],
    "compressor_station": ["air_quality", "oil_gas_conservation", "noise"],
    "gas_processing_plant": ["air_quality", "water_quality", "waste", "emergency_response"],
}


# ------------------------------------------------------------------ lookup

def resolve_jurisdictions(features, state_hint: str = "", counties: list[str] = (),
                          munis: list[str] = (), online: bool = True) -> tuple[list[dict], list[str]]:
    """Identify state/county/place containing the project.

    Uses the Census TIGERweb ArcGIS service when outbound HTTPS is available,
    sampling along the route so a corridor clipping a third county is caught.
    Falls back to whatever the caller passed on the command line.
    """
    notes: list[str] = []
    manual = []
    for c in counties or []:
        manual.append({"level": "county", "state": state_hint, "county": c,
                       "municipality": "", "basis": "specified on the command line"})
    for m in munis or []:
        manual.append({"level": "municipal", "state": state_hint, "county": "",
                       "municipality": m, "basis": "specified on the command line"})

    if not online or not common.egress_ok():
        notes.append(
            "Automatic jurisdiction lookup was skipped because outbound HTTPS is "
            "unavailable here. Jurisdictions below came from --state/--county/--muni. "
            "Re-run with network access, or use the HTML tool in a browser, to "
            "confirm every county and incorporated place the route actually crosses."
        )
        return manual, notes

    found = _tigerweb(kmlgeo.sample_points(features), notes)
    # Command-line entries win on ordering but never get dropped.
    seen = {(j["county"].lower(), j["municipality"].lower()) for j in found}
    for j in manual:
        if (j["county"].lower(), j["municipality"].lower()) not in seen:
            found.append(j)
    return found, notes


_TIGER = "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb"
_TIGER_LAYERS = [
    (f"{_TIGER}/State_County/MapServer/1", "state", "BASENAME"),
    (f"{_TIGER}/State_County/MapServer/3", "county", "BASENAME"),
    (f"{_TIGER}/Places_CouSub_ConCity_SubMCD/MapServer/0", "municipal", "BASENAME"),
]


def _tigerweb(points, notes: list[str]) -> list[dict]:
    """Point-in-polygon against Census boundaries. Best effort; never fatal."""
    import requests

    hits: dict[tuple, dict] = {}
    state_by_point: dict[tuple, str] = {}
    for lon, lat in points:
        for url, level, field in _TIGER_LAYERS:
            params = {
                "geometry": f"{lon},{lat}", "geometryType": "esriGeometryPoint",
                "inSR": "4326", "spatialRel": "esriSpatialRelIntersects",
                "outFields": "*", "returnGeometry": "false", "f": "json",
            }
            try:
                r = requests.get(f"{url}/query", params=params, timeout=30)
                data = r.json() if r.status_code == 200 else {}
            except Exception as exc:
                notes.append(f"TIGERweb {level} lookup failed: {exc}")
                continue
            for feat in data.get("features") or []:
                attrs = feat.get("attributes") or {}
                name = attrs.get(field) or attrs.get("NAME") or ""
                if not name:
                    continue
                stusab = attrs.get("STUSAB") or attrs.get("STATE") or ""
                if level == "state":
                    state_by_point[(lon, lat)] = str(stusab or name)[:2].upper()
                key = (level, name.lower())
                if key not in hits:
                    hits[key] = {
                        "level": level,
                        "state": state_by_point.get((lon, lat), ""),
                        "county": name if level == "county" else "",
                        "municipality": name if level == "municipal" else "",
                        "basis": "route intersects this boundary (US Census TIGERweb)",
                    }
    if not hits:
        notes.append("TIGERweb returned no boundaries — verify jurisdictions by hand.")
    return [v for k, v in hits.items() if k[0] != "state"]


def match_sources(sources: list[common.Source], juris: list[dict],
                  state: str, assets: list[str]) -> list[tuple[dict, list[common.Source]]]:
    """Group registry records under each jurisdiction the project touches."""
    st = (state or "").upper()
    groups: list[tuple[dict, list[common.Source]]] = []

    def wanted(s: common.Source) -> bool:
        if not assets or not s.applies_to:
            return True                      # unscoped records apply broadly
        return bool(set(assets) & set(s.applies_to))

    # Federal, then state, then each local jurisdiction — the review order.
    fed = [s for s in sources if s.jurisdiction_level == "federal" and wanted(s)]
    if fed:
        groups.append(({"level": "federal", "name": "Federal",
                        "basis": "applies nationwide"}, fed))

    state_recs = [s for s in sources
                  if s.state.upper() == st and s.jurisdiction_level in ("state", "tribal")
                  and wanted(s)]
    if state_recs:
        groups.append(({"level": "state", "name": f"State of {st}",
                        "basis": "project located in this state"}, state_recs))

    for j in juris:
        cty, muni = j.get("county", ""), j.get("municipality", "")
        if muni:
            recs = [s for s in sources if s.state.upper() == st
                    and s.municipality and s.municipality.lower() == muni.lower()]
            label = muni if muni.lower().startswith(("city", "town", "village")) else muni
        elif cty:
            recs = [s for s in sources if s.state.upper() == st
                    and s.county and s.county.lower() == cty.lower()
                    and not s.municipality]
            label = f"{cty} County" if not cty.lower().endswith("county") else cty
        else:
            continue
        groups.append(({**j, "name": label,
                        "matched": len(recs)}, [s for s in recs if wanted(s)]))
    return groups


def build_review(args, geo: dict, groups, juris_notes: list[str]) -> dict:
    unresolved: list[str] = list(juris_notes)
    needs_human: list[str] = []
    jurisdictions = []
    consulted: list[str] = []

    for meta, recs in groups:
        permits = []
        for s in recs:
            consulted.append(s.id)
            for p in s.permits or []:
                permits.append({
                    "name": p.get("name", ""),
                    "trigger": p.get("trigger", ""),
                    "cost": p.get("fee", ""),
                    "cost_basis": "" if p.get("fee") else "not in registry — confirm with jurisdiction",
                    "estimated_time": p.get("typical_timeline_days", ""),
                    "required_docs": p.get("required_docs", []) or [],
                    "citation": s.name,
                    "citation_url": p.get("form_url") or s.landing_url or "",
                    "decision_body": p.get("decision_body", ""),
                    "public_hearing": bool(p.get("public_hearing", False)),
                    "notes": f"form: {p['form_id']}" if p.get("form_id") else "",
                    "confidence": s.confidence,
                })
                if not p.get("fee"):
                    needs_human.append(f"{meta['name']}: fee for {p.get('name','permit')}")
                if not p.get("typical_timeline_days"):
                    needs_human.append(f"{meta['name']}: timeline for {p.get('name','permit')}")
        if not permits and recs:
            unresolved.append(
                f"{meta['name']}: {len(recs)} registry record(s) matched but none "
                f"carry structured permits yet — read their documents and add "
                f"permits[] entries."
            )
        if not recs:
            unresolved.append(
                f"{meta['name']}: NO registry coverage. This jurisdiction's "
                f"requirements are unknown and must be researched before the "
                f"review is usable."
            )
        jurisdictions.append({
            "name": meta["name"],
            "level": meta.get("level", "county"),
            "basis": meta.get("basis", ""),
            "source_id": ",".join(s.id for s in recs[:6]),
            "permits": permits,
        })

    if geo.get("over_one_acre"):
        needs_human.append(
            f"Estimated disturbance is {geo['est_disturbance_acres']} ac (>1 ac): "
            f"construction stormwater permit and SWPPP are triggered — confirm the "
            f"state permit number and the local erosion-control permit."
        )

    return {
        "form_version": "1.9",
        "review_date": args.review_date or date.today().strftime("%m/%d/%y"),
        "reviewer": args.reviewer,
        "clearance": args.clearance,
        "background": {
            "project_number": args.project_number,
            "project_name": args.project_name,
            "lat_long": geo.get("lat_long", ""),
            "new_line": "Y" if geo.get("lines") else "N",
            "linear_ft_of_line": f"{geo.get('total_length_ft', 0):,.0f}"
                                 f" ({geo.get('total_length_mi', 0)} mi)" if geo.get("lines") else "",
            "oil_and_or_gas": args.product,
            "new_equipment": {
                "compressors": "Yes" if "compressor_station" in args.asset else "",
                "meter_skids": "Yes" if "metering" in args.asset else "",
                "cathodic": "",
                "other": ", ".join(a for a in args.asset
                                   if a not in ("compressor_station", "metering")),
            },
        },
        "confidentiality": {
            "inside_wes": args.inside_wes, "outside_wes": args.outside_wes,
            "agreements": args.confidentiality_note,
        },
        "project_map": {
            "kml_source_file": Path(args.kml).name,
            "bbox": geo.get("bbox"),
            "centroid": geo.get("centroid"),
            "total_length_ft": geo.get("total_length_ft"),
            "disturbance_acres_est": geo.get("est_disturbance_acres"),
        },
        "regulatory": {
            "municipalities_involved": [j["name"] for j in jurisdictions
                                        if j["level"] in ("county", "municipal")],
            "jurisdictions": jurisdictions,
        },
        "non_muni_agencies": [],
        "stakeholder": {
            "stakeholders_within_1000ft": "", "mailer_required": "",
            "notice_radius_ft": None, "neighborhood_meeting_required": "",
            "notes": "Requires a parcel-owner query against the county assessor — "
                     "not derivable from the KML alone.",
        },
        "other": [
            f"Geometry: {geo.get('feature_count')} features — "
            f"{geo.get('lines')} line(s), {geo.get('polygons')} polygon(s), "
            f"{geo.get('points')} point(s).",
            f"Estimated disturbance {geo.get('est_disturbance_acres')} ac "
            f"({geo.get('est_disturbance_basis')}). Confirm against the final "
            f"construction workspace drawing.",
            "DRAFT — every requirement, cost, and timeline below must be confirmed "
            "with the jurisdiction before it drives a schedule or budget.",
        ],
        "provenance": {
            "generated_at": common.now_iso(),
            "generator": "regbase/tools/review.py",
            "registry_commit": _git_commit(),
            "sources_consulted": sorted(set(consulted)),
            "unresolved_questions": unresolved,
            "human_verification_required": sorted(set(needs_human)),
        },
    }


def _git_commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                              cwd=common.ROOT, capture_output=True, text=True,
                              timeout=10).stdout.strip()
    except Exception:
        return ""


# ----------------------------------------------------------------- render

def _blank(v, placeholder: str = "________") -> str:
    return str(v) if v not in (None, "", []) else placeholder


def to_markdown(r: dict) -> str:
    b, o = r["background"], []
    o.append("# Pre-Project Regulatory Review")
    o.append(f"\n**Review Date:** {r['review_date']}  |  **Reviewer:** {r['reviewer']}")
    o.append(f"\n## {r['clearance']}\n")
    o.append("## Background (To be Completed by Commercial/PM)\n")
    o.append(f"- **Project #:** {_blank(b.get('project_number'), 'N/A')}")
    o.append(f"- **Project Name:** {_blank(b.get('project_name'))}")
    o.append(f"- **Lat/Long:** {_blank(b.get('lat_long'))}")
    o.append(f"- **New Line (Y/N):** {_blank(b.get('new_line'))}")
    o.append(f"- **Linear Ft of Line:** {_blank(b.get('linear_ft_of_line'), 'TBD')}")
    o.append(f"- **Oil and/or Gas:** {_blank(b.get('oil_and_or_gas'))}")
    ne = b.get("new_equipment", {})
    o.append("- **New Equipment (Y/N)**")
    for k, lbl in (("compressors", "Compressors"), ("meter_skids", "Meter Skids"),
                   ("cathodic", "Cathodic"), ("other", "Other")):
        o.append(f"    - {lbl}: {_blank(ne.get(k))}")

    c = r.get("confidentiality", {})
    o.append("\n## Confidentiality\n")
    o.append(f"- Can this be discussed with parties inside WES (Y/N): {_blank(c.get('inside_wes'))}")
    o.append(f"- Can this be discussed with parties outside WES (Y/N): {_blank(c.get('outside_wes'))}")
    if c.get("agreements"):
        o.append(f"- {c['agreements']}")

    pm = r.get("project_map", {})
    o.append("\n## Project Map\n")
    o.append(f"- Source file: `{pm.get('kml_source_file','')}`")
    o.append(f"- Centroid: {pm.get('centroid')}  |  BBox: {pm.get('bbox')}")
    if pm.get("total_length_ft"):
        o.append(f"- Total centerline: {pm['total_length_ft']:,.0f} ft")
    o.append(f"- Estimated disturbance: {pm.get('disturbance_acres_est')} ac")
    o.append("- _[insert project map image here]_")

    reg = r["regulatory"]
    o.append("\n## Regulatory\n")
    o.append(f"**Municipality(s) Involved:** "
             f"{', '.join(reg['municipalities_involved']) or '________'}\n")
    for j in reg["jurisdictions"]:
        o.append(f"\n### {j['name']}  _({j['level']})_")
        if j.get("basis"):
            o.append(f"_{j['basis']}_")
        if not j["permits"]:
            o.append("\n> **No permits on file for this jurisdiction.** "
                     "Requirements unknown — research required before use.\n")
            continue
        for p in j["permits"]:
            aka = f" ({p['aka']})" if p.get("aka") else ""
            o.append(f"\n**{p['name']}**{aka}"
                     f"{'  `' + p['confidence'] + '`' if p.get('confidence') else ''}")
            if p.get("trigger"):
                o.append(f"- _Trigger:_ {p['trigger']}")
            o.append(f"- **Cost:** {_blank(p.get('cost'))}"
                     f"{'  — ' + p['cost_basis'] if p.get('cost_basis') else ''}")
            o.append(f"- **Estimated Time:** {_blank(p.get('estimated_time'))}")
            docs = p.get("required_docs") or []
            o.append("- **Required Docs:**" + ("" if docs else " ________"))
            for d in docs:
                o.append(f"    - {d}")
            if p.get("decision_body"):
                o.append(f"- Decision body: {p['decision_body']}"
                         f"{' (public hearing)' if p.get('public_hearing') else ''}")
            if p.get("citation_url"):
                o.append(f"- Source: [{p.get('citation','link')}]({p['citation_url']})")
        for t in j.get("timing_narrative") or []:
            o.append(f"\n**Timing — {t.get('phase','')}** ({t.get('duration','')})")
            for step in t.get("steps") or []:
                o.append(f"- {step}")

    o.append("\n## Non-Muni Agencies\n")
    if r.get("non_muni_agencies"):
        for a in r["non_muni_agencies"]:
            o.append(f"- **{a.get('agency','')}** — {a.get('requirement','')} "
                     f"(cost {_blank(a.get('cost'))}, {_blank(a.get('estimated_time'))})")
    else:
        o.append("- ________  _(fire district, USACE, SHPO, USFWS, tribal — confirm)_")

    s = r.get("stakeholder", {})
    o.append("\n## Stakeholder\n")
    o.append(f"- Stakeholders within 1,000 ft (Y/N): {_blank(s.get('stakeholders_within_1000ft'))}")
    o.append(f"- Mailer Required (Y/N): {_blank(s.get('mailer_required'))}")
    if s.get("notes"):
        o.append(f"- _{s['notes']}_")

    o.append("\n## Other\n")
    for line in r.get("other") or []:
        o.append(f"- {line}")

    prov = r.get("provenance", {})
    if prov.get("unresolved_questions") or prov.get("human_verification_required"):
        o.append("\n---\n\n## Open Items (not part of the form — resolve before issuing)\n")
        for q in prov.get("unresolved_questions") or []:
            o.append(f"- [ ] {q}")
        for q in prov.get("human_verification_required") or []:
            o.append(f"- [ ] {q}")
    return "\n".join(o) + "\n"


def to_word(markdown_text: str, title: str) -> str:
    """Minimal markdown -> Word-openable HTML. Only the constructs we emit."""
    body: list[str] = []
    in_list = False

    def close_list():
        nonlocal in_list
        if in_list:
            body.append("</ul>")
            in_list = False

    for raw in markdown_text.splitlines():
        line = raw.rstrip()
        if not line.strip():
            close_list()
            body.append("<p></p>")
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            close_list()
            lvl = len(m.group(1))
            body.append(f"<h{lvl}>{_inline(m.group(2))}</h{lvl}>")
            continue
        m = re.match(r"^(\s*)-\s+(.*)$", line)
        if m:
            indent = len(m.group(1)) // 4
            if not in_list:
                body.append("<ul>")
                in_list = True
            body.append(f'<li style="margin-left:{indent * 18}pt">{_inline(m.group(2))}</li>')
            continue
        if line.startswith(">"):
            close_list()
            body.append(f'<p style="border-left:3pt solid #c00;padding-left:8pt">'
                        f'{_inline(line.lstrip("> "))}</p>')
            continue
        if line.strip() == "---":
            close_list()
            body.append("<hr/>")
            continue
        close_list()
        body.append(f"<p>{_inline(line)}</p>")
    close_list()

    return f"""<html xmlns:o="urn:schemas-microsoft-com:office:office"
      xmlns:w="urn:schemas-microsoft-com:office:word"
      xmlns="http://www.w3.org/TR/REC-html40">
<head><meta charset="utf-8"/><title>{html.escape(title)}</title>
<!--[if gte mso 9]><xml><w:WordDocument><w:View>Print</w:View>
<w:Zoom>100</w:Zoom></w:WordDocument></xml><![endif]-->
<style>
 @page {{ size: 8.5in 11in; margin: 0.8in; }}
 body {{ font-family: Calibri, Arial, sans-serif; font-size: 11pt; color: #111; }}
 h1 {{ font-size: 18pt; margin: 0 0 6pt; }}
 h2 {{ font-size: 14pt; margin: 14pt 0 4pt; border-bottom: 1pt solid #999; }}
 h3 {{ font-size: 12pt; margin: 10pt 0 3pt; color: #1a3d6d; }}
 ul {{ margin: 2pt 0 6pt 0; }}
 li {{ margin: 1pt 0; }}
 hr {{ border: none; border-top: 1pt solid #bbb; }}
</style></head><body>
{chr(10).join(body)}
</body></html>"""


def _inline(text: str) -> str:
    text = html.escape(text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<i>\1</i>", text)
    text = re.sub(r"_([^_]+)_", r"<i>\1</i>", text)
    text = re.sub(r"`([^`]+)`", r'<span style="font-family:Consolas">\1</span>', text)
    return text


_CLEARANCE_SUFFIX = {
    "NOT CLEARED TO CONSTRUCT": "NTCLRD",
    "CLEARED TO CONSTRUCT": "CLRD",
    "CLEARED WITH CONDITIONS": "CLRDCOND",
    "PENDING REVIEW": "PEND",
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("kml", help="project .kml or .kmz")
    ap.add_argument("--project-name", required=True)
    ap.add_argument("--project-number", default="N/A")
    ap.add_argument("--reviewer", default="")
    ap.add_argument("--review-date", default="", help="MM/DD/YY (default: today)")
    ap.add_argument("--clearance", default="NOT CLEARED TO CONSTRUCT",
                    choices=list(_CLEARANCE_SUFFIX))
    ap.add_argument("--asset", action="append", default=[],
                    help="repeatable: midstream_pipeline compressor_station swd_well "
                         "produced_water_line gas_processing_plant metering ...")
    ap.add_argument("--product", default="", help="e.g. 'Gas and Condensate'")
    ap.add_argument("--state", default="", help="two-letter; required for state/local matching")
    ap.add_argument("--county", action="append", default=[])
    ap.add_argument("--muni", action="append", default=[])
    ap.add_argument("--inside-wes", default="")
    ap.add_argument("--outside-wes", default="")
    ap.add_argument("--confidentiality-note", default="")
    ap.add_argument("--offline", action="store_true",
                    help="skip the Census jurisdiction lookup")
    ap.add_argument("--out", default="reviews", help="output directory")
    args = ap.parse_args()

    feats = kmlgeo.parse(Path(args.kml))
    geo = kmlgeo.summarize(feats)

    juris, notes = resolve_jurisdictions(
        feats, args.state, args.county, args.muni, online=not args.offline)
    if not args.state and juris:
        args.state = next((j["state"] for j in juris if j.get("state")), "")

    groups = match_sources(common.load_sources(), juris, args.state, args.asset)
    review = build_review(args, geo, groups, notes)

    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)
    stem = (f"Form_1.9__Pre_Project_Review__"
            f"{review['review_date'].replace('/', '')[-2:]}"
            f"{review['review_date'][:2]}{review['review_date'][3:5]}__"
            f"{common.slugify(args.project_name).replace('-', '_')}_"
            f"{_CLEARANCE_SUFFIX[args.clearance]}")

    md = to_markdown(review)
    (outdir / f"{stem}.review.json").write_text(json.dumps(review, indent=2))
    (outdir / f"{stem}.md").write_text(md)
    (outdir / f"{stem}.doc").write_text(
        to_word(md, f"Pre-Project Regulatory Review — {args.project_name}"))

    prov = review["provenance"]
    print(f"wrote {outdir}/{stem}.{{review.json,md,doc}}")
    print(f"  jurisdictions: {len(review['regulatory']['jurisdictions'])}  "
          f"permits: {sum(len(j['permits']) for j in review['regulatory']['jurisdictions'])}  "
          f"sources consulted: {len(prov['sources_consulted'])}")
    if prov["unresolved_questions"]:
        print(f"\n  {len(prov['unresolved_questions'])} unresolved question(s):")
        for q in prov["unresolved_questions"][:8]:
            print(f"    - {q}")
    if prov["human_verification_required"]:
        print(f"\n  {len(prov['human_verification_required'])} item(s) need human "
              f"verification (listed in the JSON and at the bottom of the .md)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
