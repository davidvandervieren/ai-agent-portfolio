---
name: pre-project-review
description: Produce a Form 1.9 Pre-Project Regulatory Review for an oil & gas midstream project (pipeline, produced water line, SWD well, compressor station, gas processing plant) in CO, WY, NM, UT, or TX. Use when the user supplies a KML/KMZ and a scope, asks "what permits do we need for <project>", asks to scope or pre-screen a project, asks which jurisdictions a route crosses, or asks for a project scoping document for a PM. Also use when asked to update or re-issue an existing Form 1.9.
---

# Pre-Project Regulatory Review (Form 1.9)

You are producing the document that tells a project manager what it will take to
permit a midstream project. It goes into schedules and budgets. Getting a
requirement wrong is worse than saying you don't know.

## The one rule

**Never invent a permit, a cost, a timeline, a form number, or a citation.**
Everything comes from `regbase/sources/*.yaml` (via the tools below) or from a
source you actually read this session. When the registry has no answer, the
field stays blank and the gap goes on the Open Items list. The user's standing
instruction: *if you do not know something, do not guess — say you are unsure
and ask.*

## Workflow

### 1. Get the geometry

```bash
python3 regbase/tools/kmlgeo.py <project.kmz> --samples
```

Gives you centroid, bbox, centerline length, polygon acreage, estimated
disturbance, a feature inventory, and sample points for jurisdiction lookup.
Note whether disturbance exceeds 1 acre — that alone triggers construction
stormwater permitting everywhere.

If there is no KML, ask for one, or ask for the lat/long and county. Do not
proceed on a guessed location.

### 2. Pin the scope

You need these before the review means anything. Ask for whatever is missing:

- **Asset types** — `midstream_pipeline`, `produced_water_line`, `swd_well`,
  `compressor_station`, `gas_processing_plant`, `well_pad`, `tank_battery`,
  `metering`, `access_road`, `electrical_line`, `water_crossing`,
  `temporary_workspace`
- **Product** — gas, oil, condensate, produced water, or a mix
- **New line vs. replacement / relocation** (a relocate often has a narrower path)
- **Compression horsepower** — drives the air permitting tier
- **Surface ownership** — fee, state trust, BLM, tribal (each is a different path)
- **Water or wetland crossings**, **H2S / sour service**, **in-service date**
- **Confidentiality** — inside WES? outside WES? any CA in place?

### 3. Resolve jurisdictions

Federal → state → county → municipal → special district. A route is rarely in
one place: check **every** county and incorporated place along it, not just the
centroid, and watch for extraterritorial jurisdiction (NM ETZ, Texas city ETJ)
that reaches outside city limits.

```bash
python3 regbase/tools/query.py stack --state CO --county Weld --muni Erie \
    --asset midstream_pipeline --asset compressor_station
```

### 4. Generate the draft

```bash
python3 regbase/tools/review.py <project.kmz> \
    --project-name "<name>" --reviewer "<reviewer>" \
    --asset midstream_pipeline --asset compressor_station \
    --product "Gas and Condensate" \
    --state CO --county Arapahoe \
    --out reviews/
```

Writes three files: `.review.json` (schema-conformant interchange), `.md`
(editable draft), `.doc` (opens in Word). Filenames follow the existing
convention — `Form_1.9__Pre_Project_Review__YYMMDD__Project_Name_NTCLRD`.

Add `--offline` when outbound HTTPS is unavailable; jurisdictions then come
only from `--county`/`--muni`, and the draft says so.

### 5. Fill the gaps the generator can't

The generator is honest about what it doesn't know. Work its Open Items list:

- **Costs and timelines** the registry lacks — search the corpus
  (`query.py search "<permit name> fee schedule" --county X`), then the
  jurisdiction's fee schedule. If still unknown, leave blank and say so.
- **Non-muni agencies** — fire district (frequently the single biggest surprise
  cost), USACE district, SHPO, USFWS, state wildlife agency, tribal, irrigation
  and drainage districts, railroads, DOT utility permits.
- **Stakeholders** — the count within the notice radius needs an assessor
  parcel query; the KML cannot answer it. Flag it as an action for real estate.
- **Local knowledge** — has the company done work in this jurisdiction before?
  If not, say so on the form and add schedule contingency, the way the Arapahoe
  County example does.

### 6. Review before issuing

- Is every jurisdiction the route crosses listed?
- Does each permit carry a cost, a timeline, and required docs, or an explicit blank?
- Is every `unverified` registry item marked as such on the form?
- Is the clearance banner right? Default is **NOT CLEARED TO CONSTRUCT**; only
  change it when the permits are actually in hand.
- Are the Open Items assigned to someone?

## Form structure (do not reorder)

Title → Review Date / Reviewer → clearance banner → **Background** (Project #,
Project Name, Lat/Long, New Line Y/N, Linear Ft, Oil and/or Gas, New Equipment:
Compressors / Meter Skids / Cathodic) → **Confidentiality** (inside WES /
outside WES) → **Project Map** → **Regulatory** (Municipality(s) Involved, then
per jurisdiction: permit → Cost → Estimated Time → Required Docs, plus an
optional phased Timing narrative) → **Non-Muni Agencies** → **Stakeholder**
(within 1,000 ft Y/N, mailer required Y/N) → **Other**.

Canonical data model: `regbase/schemas/review.schema.json`.

## Things that repeatedly bite on these projects

Check each one explicitly rather than assuming it doesn't apply:

- Disturbance > 1 acre → construction stormwater permit + SWPPP, state and often local
- Colorado **1041 permits** — a separate, slow, county-level review that runs in
  parallel with a Special Use Permit, not inside it
- Texas **HB 40** — counties have no zoning; cities keep only "commercially
  reasonable" surface regulation. Do not scope a Texas city permit that HB 40 preempts
- New Mexico **ETZ** and Texas **ETJ** — city authority outside city limits
- Fire district review and sign-off — often five figures, often forgotten
- Federal nexus (BLM ROW, USACE 404, tribal) → NEPA, Section 106, Section 7
  consultation, and a much longer schedule
- Air permitting tier set by horsepower and by nonattainment status
  (Uinta Basin, DFW, Houston-Galveston-Brazoria, Permian, northern Front Range)
- Antiquities Code permit in Texas on any state or political-subdivision land

## Coverage gaps

The registry is incomplete, Texas most of all. Before relying on a jurisdiction:

```bash
python3 regbase/tools/query.py gaps --state TX
```

Say plainly when a jurisdiction has no coverage. A review that admits a hole is
useful; one that quietly omits a permit is not.
