# TX-West (Statewide + Permian Basin + Panhandle/Anadarko) — Research Notes

## 0. Coverage blocker — read this first

This session's WebSearch budget was **shared across the whole environment** and was
already exhausted (0/200 remaining, confirmed by a sibling agent's `tx-east.yaml`
run) before this task effectively started. Only **2 WebSearch calls returned
results** (10 distinct links, all Railroad Commission of Texas pages) before the
budget hard-capped every subsequent call, including retries. `WebFetch`/`curl`/
`wget` are blocked by the network egress proxy per task instructions, so there was
no fallback research tool.

Per the task's standing rule ("never guess" / "NEVER invent or reconstruct a URL"),
`tx-west.yaml` contains only the 3 records built from URLs actually seen (all RRC:
Statewide Rules Ch. 3 landing/TAC page, the Ch. 4 waste-rule overhaul, and Pipeline
Safety Form T-4/POPS). **Zero records exist for TCEQ, GLO, THC, TxDOT, TWDB, TPWD,
any groundwater conservation district, any of the ~60 in-scope counties, or any of
the ~45 in-scope municipalities** — none of them were reachable via search this run.
Everything below this point is **general regulatory/legal knowledge, not
search-verified**, offered so a follow-up pass has a concrete checklist and starting
hypotheses rather than a blank page. Treat every specific fact, form number, and URL
guess below as **unverified** and confirm before citing or publishing.

The single highest-priority next step is re-running this same task once WebSearch
budget is restored (or WebFetch is opened to `*.texas.gov`, `*.state.tx.us`, county/
municipal domains, and municode/american legal/ecode360). RRC alone has ~20 more
statewide-rule and form pages queued (SWR 9/14/36/46, Form W-1/W-2/W-3/W-14, P-4/P-5,
H-1/H-2/H-9, PS-48/79/80/81, R-series). TCEQ (Ch. 106 PBR, Ch. 116 NSR/air standard
permit, Edwards Aquifer Ch. 213, UIC Ch. 331), GLO, THC Antiquities Code, TxDOT UIR/
driveway permits, TWDB, all 8 named GCDs, the top-15 Permian counties, and all
in-scope municipalities are entirely unresearched.

## (a) What Texas HB 40 (2015) leaves to municipalities — general knowledge, unverified

HB 40 (adding Texas Natural Resources Code §81.0523) established that oil and gas
operations are subject to the state's exclusive jurisdiction, and preempted municipal
ordinances, regulations, or other actions that purport to regulate an oil and gas
operation. It carved out a narrow band municipalities may still regulate, generally
described as ordinances that:
- Are limited to **aboveground activity related to an oil and gas operation** that
  occurs at or above the surface (not the operation itself, e.g. not well spacing,
  completion technique, or the decision to drill/inject/dispose);
- Are **commercially reasonable** (do not effectively prohibit an operation conducted
  in a commercially reasonable manner);
- Do not impose a **fee** that isn't a "reasonable and necessary" fee for actual costs
  of administering the ordinance;
- Have been in effect continuously (or fall within the traditional categories courts
  and the statute recognize), typically including: **fire and emergency response
  standards, traffic and road-use conditions/oversize-overweight routing, noise
  limits, lighting/dark-sky requirements, setbacks from occupied structures, notice
  to the city before operations begin, and reclamation/site-restoration/landscaping
  requirements.**
- Municipalities **cannot** ban drilling/fracking outright (the direct trigger for HB
  40 was the 2014 Denton frac ban), cannot regulate well density/spacing, cannot
  regulate subsurface matters (casing, cementing, injection, disposal — RRC's
  domain), and cannot use zoning to exclude oil and gas use categorically from a
  district in a way that is not "commercially reasonable."
- Municipalities generally **retain** general police-power authority over
  right-of-way use/access (driveway cuts, utility installation permits), building
  and fire codes as applied to structures, and floodplain/drainage ordinances, to the
  extent these do not single out or effectively prohibit oil and gas operations.

**Not verified this run** — confirm against the actual TNRC §81.0523 text, RRC/TML
guidance, and any post-2015 case law (e.g. the frequently-cited *Denbury*/
*Trinity East* line and any Permian-specific municipal ordinance litigation) before
relying on this summary.

## (b) County-level permitting reality — general knowledge, unverified

Texas counties have **no general zoning authority** (unlike home-rule municipalities)
and cannot regulate land use or oil & gas operations the way a city can. What Texas
counties **do** typically administer, and that a midstream project in the Permian or
Panhandle should expect to touch:
- **Subdivision platting** (Local Government Code Ch. 232) — relevant mainly if the
  project involves creating new parcels, not typical for a pipeline/SWD easement.
- **County road use / oversize-overweight & utility-line road-crossing permits** —
  county road & bridge / commissioners court permits for boring, trenching, or
  hanging a line across or along a county road right-of-way; often a simple road-use
  agreement plus bond, administered by the County Road & Bridge Department or
  Commissioners Court.
- **Floodplain administration** (under the National Flood Insurance Program) —
  county floodplain administrator issues a floodplain development permit for
  construction (including pipeline crossings, compressor stations, tank batteries)
  within a mapped FEMA Special Flood Hazard Area; this is one of the few areas where
  counties have real regulatory teeth via NFIP participation agreements.
- **911 addressing** — county 911 addressing authority assigns a site address,
  typically required before/alongside building permits or as a prerequisite for
  emergency response mapping at compressor stations, SWD facilities, etc.
- **On-Site Sewage Facility (OSSF) permits** (30 TAC 285, administered locally) — for
  septic systems at manned facilities (compressor stations, gas plants with staff
  buildings).
- **Sand, gravel, caliche/dust and haul-road agreements** — some counties require a
  road-damage/haul agreement or bond for heavy construction traffic tied to pipeline
  or facility builds.
- Counties do **not** issue building permits county-wide by default (only certain
  counties have adopted limited building-code authority) and have **no** land-use/
  zoning permit equivalent to a city's conditional-use or special-use permit.

**Not verified this run** — no specific county department page, permit name, form,
or fee was confirmed for any of the ~60 in-scope counties. The above is the general
statutory framework (Local Government Code, Water Code floodplain provisions, Health
& Safety Code OSSF provisions), not county-specific citations.

## (c) Edwards Aquifer & H2S (SWR 36) triggers — general knowledge, unverified

- **Edwards Aquifer (30 TAC Ch. 213):** TCEQ's Edwards Aquifer Protection Program
  applies to regulated activity over the **Edwards Aquifer Recharge Zone, Contributing
  Zone, or Transition Zone** — a Water Pollution Abatement Plan (WPAP) or Contributing
  Zone Plan (CZP) is required before construction of pipelines, roads, or facilities
  in those zones, plus geologic assessment in sensitive-feature areas. **Scope note
  for this task's Permian/Panhandle region:** the Edwards Aquifer's mapped recharge/
  contributing zones are centered on the Balcones Fault Zone (Central Texas — Kinney,
  Uvalde, Medina, Bexar, Comal, Hays, Travis, Williamson counties and similar), which
  is **outside** the Permian Basin and Panhandle counties listed for this task's
  scope. Ch. 213 is flagged in the task prompt as CRITICAL generally for TX midstream
  work, but for TX-West specifically it likely only matters for the southeastern edge
  counties near the Permian's boundary (e.g. Val Verde/Sutton/Schleicher/Crockett are
  plausibly near but not confirmed to be within the mapped zones) — **verify against
  TCEQ's actual Edwards Aquifer zone GIS map** before concluding it applies (or
  doesn't) to any specific TX-West county.
- **SWR 36 (H2S, 16 TAC §3.36):** Statewide Rule 36 requires operators to file a
  Form H-1 (or H-15 for exception) or H-2 (contingency plan) whenever a well or
  facility is expected to encounter or handle fluid with H2S at concentrations that
  trigger the rule's radius-of-exposure (ROE) calculation — generally, any well
  reasonably expected to produce H2S in concentrations of 100 ppm or greater in the
  gas stream (exact regulatory threshold/definitions **not verified this run**),
  requiring public notice, contingency planning, and possibly a public hearing if the
  ROE encompasses occupied structures. **This is highly relevant to the Permian
  Basin (Delaware Basin sour gas — Reeves, Loving, Ward, Winkler, Culberson, Pecos,
  Reagan, Crockett counties are widely known in the industry for elevated H2S)** —
  pipeline and compressor-station siting, gas processing plant siting, and SWD
  facility design in these counties should expect SWR 36 contingency-plan and
  possibly public-notice obligations. **Not verified this run**: the exact ppm
  threshold, current Form H-1/H-2/H-9 identifiers, and RRC's H2S rule page were not
  reachable via search.

## (d) Groundwater Conservation Districts over the Permian/Panhandle — names only, URLs NOT verified

The task prompt itself names these GCDs as relevant to Permian/Panhandle frac and SWD
water supply. Their existence and approximate coverage area is standard public
knowledge, but **no URL for any of them was confirmed via WebSearch this run** — do
not publish or cite a URL for these until independently verified:
- Middle Pecos Groundwater Conservation District (Pecos/Reeves County area)
- Santa Rita Groundwater Conservation District (Reagan/Irion County area)
- Permian Basin Underground Water Conservation District (Crane/Upton County area)
- Panhandle Groundwater Conservation District (Carson/Gray/Hutchinson/Roberts/Wheeler area)
- High Plains Underground Water Conservation District No. 1 (Lubbock/South Plains area)
- Hemphill County Underground Water Conservation District
- North Plains Groundwater Conservation District (far northern Panhandle — Dallam/Hartley/Sherman/Moore/Hansford/Ochiltree/Lipscomb)
- Llano Estacado Underground Water Conservation District (Yoakum/Terry/Gaines area)

Each GCD independently permits water wells (including large-capacity industrial/
SWD-supply wells) within its district and typically requires a permit/registration
and production reporting before a midstream or SWD operator can source or dispose of
significant water volumes from groundwater. **Next step:** search `"<district name>
Texas groundwater conservation district"` individually for each once budget allows;
each is a distinct special_district-level source record with its own rules,
permitting forms, and management plan.

## (e) What could NOT be verified this run (full list)

- **RRC**: exact current text and thresholds of SWR 9 (disposal wells), SWR 14
  (plugging), SWR 36 (H2S, including the ppm trigger), SWR 46 (fluid injection into
  productive reservoirs), SWR 30, SWR 32 (flaring/venting), SWR 40, SWR 74; 16 TAC
  Ch. 7 (gas utilities), Ch. 4 Subchapter B (commercial recycling/produced water); all
  specific form URLs/IDs beyond T-4/T-4B (W-1, W-1D, W-2, W-3, W-3A, W-3X, W-4, W-14,
  P-4, P-5, H-1, H-2, H-9, H-10, PS-48, PS-79, PS-80, PS-81, PS-95, PS-96, PS-97,
  PS-83, G-1, G-10, R-1–R-9, P-17, P-18, CI-D/CI-X, Form 1017); whether 16 TAC §3.8
  is still live text or has been superseded/repealed by the new Chapter 4 rules.
- **TCEQ**: nothing verified — Ch. 106 PBR (106.352, 106.492, 106.512), Ch. 116/NSR
  incl. the Oil and Gas Handling and Production Facilities Standard Permit
  (116.620), Title V (Ch. 122), Ch. 111 (visible emissions), Ch. 115 (VOC, incl.
  Permian/DFW/HGB ozone nonattainment applicability), Forms PI-1/PI-7/PI-8, Core Data
  Form 10400, TCEQ Registration 6, ePermits; TPDES CGP TXR150000 and MSGP TXR050000;
  Ch. 213 Edwards Aquifer Program (WPAP/CZP); Ch. 330 (MSW), Ch. 335 (industrial/
  hazardous waste); Class I/III/V/VI UIC under Ch. 331.
- **GLO, TPWD, THC, TxDOT, TWDB**: no pages reached — GLO coastal/submerged-land
  easements, TPWD Sand & Gravel/Marl permit and consultation process, THC Antiquities
  Code Permit process (and confirmation of when it's triggered — state/political
  subdivision land), TxDOT UIR system and Form 1058/2610 driveway permits, TWDB
  programs.
- **All ~60 in-scope counties** (Midland, Ector, Reeves, Loving, Ward, Winkler,
  Culberson, Pecos, Howard, Martin, Glasscock, Upton, Reagan, Crane, Andrews, Gaines,
  Dawson, Borden, Sterling, Irion, Crockett, Val Verde, Terrell, Jeff Davis, Hudspeth,
  Yoakum, Terry, Lynn, Scurry, Mitchell, Nolan, Coke, Tom Green, Schleicher, Sutton,
  Presidio, Brewster, and all Panhandle/Anadarko counties listed in the task): zero
  county sites, road/floodplain department pages, or permit forms confirmed.
- **All ~45 in-scope municipalities** (Midland, Odessa, San Angelo, Lubbock,
  Amarillo, and the rest of the task's list): zero city code platforms, ordinance
  chapters, or permit pages confirmed — including which code platform (municode,
  american legal, ecode360, self-hosted) each uses.
- **Texas811/Lone Star 811**, common-carrier T-4 vs. private-line distinction case
  law, and the exact current statutory text of Natural Resources Code Ch. 111,
  Utilities Code Ch. 121, and Health & Safety Code Ch. 756: not looked up this run
  (referenced above only via general legal knowledge).

## Recommendation

Re-run this task in a session/environment with a fresh (non-shared, or explicitly
raised) WebSearch budget. Suggested query batching for maximum yield per call: one
query per RRC form group (e.g. "RRC Texas Form W-14 injection well permit"), one per
TCEQ program (e.g. "TCEQ Air Quality Standard Permit oil and gas 116.620"), one per
GCD, and one per top-15 county ("<county> County Texas road bridge department
floodplain permit") and top municipality ("<city> Texas municode oil gas
ordinance"). At ~110 discrete jurisdictions/programs in scope, expect to need on the
order of 100-150 successful searches for full coverage at the depth the task
specifies.
