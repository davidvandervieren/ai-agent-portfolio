---
name: regbase
description: Answer oil & gas midstream permitting and regulatory questions for CO/WY/NM/UT/TX by querying the local RegBase corpus (regbase/tools/query.py) instead of model memory. Use for questions like "what permits do I need for a compressor station in Weld County", "what does Aurora require for a pipeline", "who decides SWD permits in Lea County NM", "pull the citation for ECMC flowline rules", "what's the full permit stack for this project", "which agency reviews a water crossing in Uintah County", or any request for a jurisdiction's code sections, forms, fees, decision bodies, timelines, GIS layers, or pre-project regulatory review.
---

# RegBase — regulatory retrieval for midstream permitting

RegBase is a local corpus of regulatory sources for oil & gas midstream permitting in
Colorado, Wyoming, New Mexico, Utah and Texas: federal, state, county, municipal,
special-district and tribal authorities, with their documents, permits, forms, decision
bodies, GIS endpoints and contacts.

## The one rule

**If you do not know something, do not guess; tell the user you are unsure and ask
clarifying questions.** In this skill that means: if the query returns nothing, say the
registry has no record, name exactly what would have to be checked to find out, and stop.
Never fill a gap from model memory — a plausible-sounding wrong permit, fee, or code
section is the single worst failure mode for this tool.

## Always query, never recall

Every answer starts with a command, run from the repository root:

```bash
python3 regbase/tools/query.py stack   --state CO --county Weld --muni Erie \
                                       --asset compressor_station --asset midstream_pipeline
python3 regbase/tools/query.py permits --state NM --county Lea --asset swd_well
python3 regbase/tools/query.py jurisdiction CO Weld            # or: jurisdiction CO "" Aurora
python3 regbase/tools/query.py search  "flowline setback" --state CO -n 8
python3 regbase/tools/query.py people  --state CO --jurisdiction co-weld-county-landuse
python3 regbase/tools/query.py gaps    --state TX
```

Add `--json` to any subcommand when you need structured output to reason over.
If the DB is missing, build it: `python3 regbase/tools/build_index.py --rebuild`.

## Review order — always work top down

1. **Federal** — BLM ROW/NEPA, USACE 404, FERC, PHMSA, EPA (air/NPDES/SPCC/RMP), USFWS/ESA,
   Section 106.
2. **State** — oil & gas conservation agency (ECMC / WOGCC / NM OCD / UT DOGM / TX RRC),
   state air, state water quality, state lands, DOT ROW, SHPO, wildlife.
3. **County** — land use / zoning / 1041 or special-use, roads & ROW, floodplain,
   stormwater, building & fire.
4. **Municipal** — only where the site is inside city limits or an extraterritorial /
   referral area; check the municipal code platform.
5. **Special districts and tribal** — drainage, navigation, groundwater conservation,
   irrigation, fire districts; tribal land triggers BIA/tribal jurisdiction.

`query.py stack` assembles levels 1–5 in that order and dedupes. Use it as the backbone of
any "what do I need?" answer.

## How to cite

Every regulatory statement you make must carry: **jurisdiction → code section / form →
URL → confidence**. `search` returns a ready-made citation string, e.g.

> Weld County Code Ch. 23-3-40 — Chapter 23 - Zoning (https://library.municode.com/…)
> — Weld County, CO, confidence: verified

Surface the `confidence` value verbatim (`verified` / `probable` / `unverified`) in the
answer. `probable` and `unverified` mean the user must confirm with the agency before
relying on it. Never present an `unverified` record as settled.

## KML / project scope → permit stack

1. Get the project's state, county(ies), municipalities and asset types. If a KML or scope
   document is supplied, use `regbase/tools/kmlgeo.py` to resolve the geometry to
   jurisdictions; if it is not available, ask the user which counties and cities the route
   or site touches — do not infer them from coordinates by memory.
2. Run `query.py stack` with one `--asset` per asset type
   (`midstream_pipeline`, `produced_water_line`, `swd_well`, `compressor_station`,
   `gas_processing_plant`, `well_pad`, `tank_battery`, `metering`, `access_road`,
   `electrical_line`, `water_crossing`, `temporary_workspace`).
3. Report the stack grouped by level, then report the `coverage_warnings` and
   `authorities_without_recorded_permits` blocks as **open items**, not as "nothing
   required".
4. Add `query.py people --jurisdiction <source_id>` when the user asks who decides.

## Worked example

User: *"What permits do I need for a compressor station in Weld County, CO?"*

```bash
python3 regbase/tools/query.py stack --state CO --county Weld --asset compressor_station
```

Answer shape:

- **Federal** — EPA Title V / PSD / minor NSR (delegated to CDPHE), NSPS OOOOb, GHGRP
  Subpart W, SPCC, EPCRA 302/311/312/313, FAA 7460-1 if a stack exceeds Part 77 heights.
- **State (CO)** — CDPHE APCD APEN + Reg. 3 construction/operating permit (or GP01/GP02);
  CDPHE WQCD COR400000 construction stormwater; ECMC Form 2A OGDP (Director/Commission,
  public hearing) and Form 4 sundry; CPW consultation via the 1200 Series.
- **County (Weld)** — Oil and Gas Location Assessment / 1041 permit, Board of County
  Commissioners, public hearing (confidence: verified; fee, form ID and timeline are **not
  recorded** — confirm with Weld County Planning Services).
- **Open items** — Colorado PUC Gas Pipeline Safety is in the registry with no permit
  recorded; if the site is inside a municipality (Greeley, Evans, Erie, Kersey…) rerun with
  `--muni`.

Then state plainly what is missing rather than filling it in.

## Known coverage gaps

Run `python3 regbase/tools/query.py gaps [--state XX]` before answering anything that
sounds comprehensive. Persistent, known holes:

- **Texas is barely covered** — a handful of statewide RRC records, **zero county or
  municipal records**. Any TX county/city answer must be given as "not in the registry;
  here is what to check" (RRC statewide rules, county road/floodplain office, the city's
  code platform, groundwater conservation district, drainage/navigation district).
- **No document text has been harvested yet** (outbound HTTPS was blocked when the corpus
  was built), so `search` returns 0 results until `harvest.py` + `extract.py` run and
  `build_index.py` is re-run. Registry-backed commands (`permits`, `stack`, `jurisdiction`,
  `gaps`, `people`) work regardless — say which one you used.
- **People records are seat placeholders**: `confidence: unverified`, no names. Never name
  an incumbent from them; report the office/body and that the holder is unverified.
- Many permits lack `fee`, `form_id` and `typical_timeline_days` — `query.py` prints those
  as `MISSING in registry`. Repeat that to the user rather than estimating.

## Boundaries

RegBase is a research aid, not legal advice, and not a substitute for a pre-application
meeting with the agency. Say so when a user is about to rely on an answer for a filing.
