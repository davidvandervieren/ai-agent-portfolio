# Utah — Research Notes (Oil & Gas Midstream Regulatory Registry)

**Session constraint:** This task's WebSearch budget (shared session-wide, 200 calls) was
exhausted partway through county-level research. State-level agencies got reasonable
coverage; county coverage stopped after Uintah, Duchesne, Carbon, and Emery (Carbon and
Emery only partially — landing pages found, not full ordinance text). No municipality
was researched at all. `ut.yaml` contains 18 sources, all state/tribal plus those four
counties. Every URL in it was actually returned by a WebSearch call this session — none
invented. Content descriptions come from search-result snippets, not fetched pages
(WebFetch/curl are blocked in this environment), so treat all entries as `confidence:
probable` unless noted otherwise, and re-verify by opening the actual page before citing
it in a work product.

## (a) Uinta Basin ozone nonattainment — which R307 rules bite

- The Uinta Basin (Uintah + Duchesne counties) is an EPA ozone nonattainment area driven
  by winter wintertime ozone from oil & gas VOC/NOx emissions trapped under inversions.
- **R307-401** (Permits: New and Modified Sources / NOI-Approval Order) — any new or
  modified compressor station, gas processing plant, or tank battery needs an Approval
  Order; carries a 30-day public comment period. A prior R307-509 exemption for wells
  holding an R307-401 Approval Order was reported (per a search snippet) as narrowed or
  eliminated by rule amendment — **this specific change needs to be confirmed against the
  current adopted rule text**, not just the snippet.
- **R307-500 series (oil & gas area-source rules)** — adopted 2014, expanded since, and
  is the workhorse series for basin-wide equipment: pneumatic controller emissions,
  storage tank/truck loadout VOC control, leak detection and repair (**R307-509** is
  specifically LDAR — described in a search snippet as recently amended to reflect
  updated, higher VOC emission factors from tanks/components based on new compliance
  inspection data). R307-504/505/506/507 were named in the task brief as relevant but
  their individual scopes were **not independently confirmed** this session beyond
  R307-505 (source registration) and R307-509 (LDAR).
- **R307-505** — statewide registration requirement: any oil & gas source on
  state-jurisdiction land must register once with DAQ.
- **R307-415 (Title V)** — applies once a facility (e.g., a large gas processing plant or
  compressor station) crosses major-source thresholds; not basin-specific but commonly
  triggered by midstream infrastructure.
- Net effect for a midstream project sited in Uintah/Duchesne counties: expect DAQ
  Approval Order review + registration + LDAR program design (R307-509) baked into permit
  conditions from the start, on top of whatever would apply in an attainment county.

## (b) SITLA vs. BLM vs. tribal vs. fee-surface permitting paths

- **SITLA (state trust lands)** — easement/ROW application to Utah School and
  Institutional Trust Lands Administration under R850-30/R850-40; ~30-year term,
  $750 application fee (per a 2026-dated search snippet — reconfirm before quoting),
  rental per Easement Price Schedule or appraisal. Requires cultural/paleontological/
  biological survey coordination and Resource Development Coordinating Committee (RDCC)
  + local government review. This is the path whenever the route crosses School and
  Institutional Trust Lands (checkerboarded through the Uinta Basin and much of eastern
  Utah).
- **BLM (federal public land)** — out of this session's direct search scope (task brief
  focuses on state/tribal), but is the default federal ROW authority for most public land
  in Uintah, Duchesne, Carbon, Emery, Grand, and San Juan counties; would run alongside
  BLM's own NEPA and Section 106 (SHPO coordination) process. **Not independently
  researched this session — no BLM-specific entries were added to ut.yaml** since this
  file's remit is UT state/county/municipal/tribal, but any real project needs a
  companion BLM ROW/APD entry sourced from the federal registry, not this file.
- **Tribal (Ute Indian Tribe, Uintah & Ouray Reservation)** — the Tribe's Energy &
  Minerals Department administers Access Permits and Business Licenses for O&G
  operators working on Reservation trust/allotted land; per a search snippet the Tribe
  leases ~400,000 acres and has ~7,000 producing wells (~45,000 bopd), so this is not a
  peripheral path in the Uinta Basin — it is a primary one for large swaths of
  Uintah/Duchesne acreage. The task brief also names **BIA Uintah & Ouray Agency ROW
  approval under 25 CFR 169** as the federal-trust-land counterpart to a tribal
  easement — **no BIA Uintah & Ouray Agency-specific URL was found or verified this
  session**; the `ut-ute-tribe-energy-minerals` entry is marked `confidence: unverified`
  for that reason, even though the Tribe's own energy-minerals landing page is solid.
- **Fee (private) surface** — no state permitting path is needed for the surface access
  itself (a private surface use agreement governs), but state/county regulatory permits
  (DOGM APD, DAQ Approval Order, county CUP, DWQ stormwater, etc.) still apply regardless
  of surface ownership. Duchesne County's ordinance text explicitly folds a surface use
  agreement requirement into its CUP process for O&G drilling/production sites.

## (c) Counties with vs. without meaningful O&G zoning

**Researched, confirmed to have explicit O&G zoning provisions:**
- **Uintah County** — Title 17 (Zoning) includes a use-and-activity permit table
  (Ch. 17.33) that addresses oil & gas and related uses; Conditional Use Permit process
  administered by Community Development.
- **Duchesne County** — has the most explicit, purpose-built O&G ordinance section found
  this session: Code §8-13-5-4 "Oil and Gas Drilling and Production Sites," with its own
  Administrative CUP track, $700 fee, grandfather clause, and a mandatory Transportation
  Master Plan compliance review + transportation service fee tied specifically to
  spudding/construction.

**Referenced but not confirmed in depth:**
- **Carbon County** — has a Development Code and an official zone map with industrial-
  type zones ("M & G", "C-1") that plausibly cover O&G/midstream uses, but the specific
  ordinance chapter and hosting platform were not located this session. Treat as
  "probably has some zoning coverage, unconfirmed specifics."
- **Emery County** — a search snippet confirms oil & gas wells are referenced somewhere
  in the county's zoning ordinance, but the exact chapter/section was not found. Only the
  Building & Zoning department landing page and a zoning-maps page were verified.

**Not researched at all (budget exhausted before these could be searched):**
Grand, San Juan, Sevier, Sanpete, Summit, Daggett, Garfield, Kane, Millard, Juab,
Box Elder, Utah, Salt Lake, Davis, Weber, Tooele, Wasatch, Iron, Beaver, Piute, Wayne,
Rich, Morgan, Cache. This includes three of the task's own "depth focus" counties —
**Grand, San Juan, and Summit** — plus **Sevier** and **Daggett**, all of which the brief
flagged as carrying real O&G activity. This is the single biggest gap in this
deliverable and should be the first thing a follow-up session tackles.

General expectation (from general knowledge, NOT verified this session, so not
included in ut.yaml): San Juan County (Aneth field, Navajo Nation lands) and Grand
County (Cane Creek/Lisbon Valley area, also adjacent to Moab's tourism-sensitive land
use politics) likely have their own O&G-specific provisions or at least industrial/
extraction zoning categories; Summit and Daggett are lower O&G-activity counties where
zoning may be generic rather than O&G-specific. **Do not cite these expectations as
fact** — they need the same search-and-verify treatment applied to Uintah/Duchesne.

## (d) What could not be verified (honest gap list)

1. **All municipalities in scope** (Vernal, Roosevelt, Duchesne, Price, Helper,
   Wellington, Moab, Naples, Ballard, Myton, Castle Dale, Huntington, Green River,
   Monticello, Blanding, East Carbon, Manila, Altamont, Neola, Tabiona, Salina,
   Richfield, Nephi, Delta, Park City, Coalville, Kamas, Ferron, Orangeville, Clawson,
   Emery, Bluff) — zero searches performed, zero entries in ut.yaml. One incidental hit:
   a search snippet showed Naples City's land use ordinance page references/co-adopts
   Uintah County's land use ordinance, suggesting Naples may not have a fully
   independent code — worth checking first in a follow-up.
2. **Counties**: Grand, San Juan, Sevier, Sanpete, Summit, Daggett, Garfield, Kane,
   Millard, Juab, Box Elder, Utah, Salt Lake, Davis, Weber, Tooele, Wasatch, Iron,
   Beaver, Piute, Wayne, Rich, Morgan, Cache — not researched.
3. **Carbon and Emery counties** — only department landing pages found; actual ordinance
   text/platform not located, so both entries are `confidence: unverified`.
4. **DOGM R649 rule text authority** — the compiled PDF at
   `oilgas.ogm.utah.gov/pub/Rules/R649_All.pdf` is an official DOGM-hosted document and
   was used as primary source, but individual-section citations were cross-checked only
   against a third-party mirror (`utrules.elaws.us`), not the official
   `rules.utah.gov`/`adminrules.utah.gov` text. Re-verify exact rule numbering
   (R649-3 subsections, R649-9 waste provisions) against the official Utah Office of
   Administrative Rules site before using in a legal work product.
5. **R307-504/506/507** (named in the task brief) — scopes not independently confirmed;
   only R307-401, R307-415 (by reference), R307-505, and R307-509 were substantiated by
   search snippets.
6. **R315-321 (Class VII E&P waste landfill)** and **TENORM R313-25** — R315-321 was
   named in a search-result summary but no direct rule-text URL was located; TENORM
   R313-25 (flagged in the task brief as relevant to SWD/produced-water solids) was
   **not searched at all** this session and has no entry in ut.yaml.
7. **LUDMA oil & gas preemption question** — the task brief specifically asked about
   "statutory limits on local regulation of oil & gas" under LUDMA. Search results
   described LUDMA's general framework (general plan requirement, 45-day decision
   timeline) but did **not** surface an explicit statutory clause preempting or limiting
   county/municipal regulation of oil & gas specifically. This is flagged as unverified
   in the `ut-ludma-county-land-use-act` entry — a targeted follow-up search
   (e.g., "Utah Code 17-27a oil gas preemption" combined with reading the statute text
   directly, not just snippets) is needed to answer this definitively.
8. **BIA Uintah & Ouray Agency** (25 CFR 169 ROW process) — named in the task brief as
   essential for tribal trust/allotted land crossings but no BIA Uintah & Ouray
   Agency-specific page was found; only a general BIA O&G plays PDF for the reservation.
9. **Utah PSC vs. DPU pipeline safety** — confirmed the Pipeline Safety Group sits within
   the Division of Public Utilities (Dept. of Commerce), not the Public Service
   Commission itself, though PSC dockets reference pipeline safety filings
   (`pscdocs.utah.gov`). The exact institutional relationship/overlap between PSC and DPU
   on pipeline safety was not fully disambiguated.
10. **No ArcGIS REST / GIS service endpoints were confirmed** for any Utah agency or
    county this session — DOGM's "OGM Data Explorer" was referenced by name in general
    knowledge but no working service URL was seen in search results, so `ut.yaml`
    intentionally leaves GIS entries thin/absent rather than guessing an endpoint.

**Recommended next step:** re-run this task in a fresh session (fresh WebSearch budget)
starting from item 2 above (the 23 un-researched counties, prioritizing Grand, San Juan,
Summit, Sevier, Daggett first per the task's own depth-focus list), then proceed to
municipalities, then close gaps 4-10.
