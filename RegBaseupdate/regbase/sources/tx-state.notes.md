# TX-State (Texas statewide agencies) — Research Notes

Scope: `regbase/sources/tx-state.yaml` — Texas STATE-LEVEL regulatory records
(TCEQ air/water/waste/UIC, RRC gaps not already covered by tx-west.yaml/
tx-east.yaml, THC, GLO, TxDOT, TPWD, groundwater conservation districts,
Texas811/common-carrier statutes). 28 records, 49 permits, all schema-valid
(verified against `regbase/schemas/source.schema.json`).

WebSearch budget used: ~30 of the ~45-search allocation. `WebFetch`/`curl`/
`wget` were blocked per task constraints; every URL in tx-state.yaml is one
actually returned in a WebSearch result (never invented/reconstructed), per
the "never guess" standing rule.

## (a) What HB 40 leaves to municipalities

Not independently re-verified this run (no new searches spent on it — see
`tx-west.notes.md` section (a) for the fuller narrative already researched by
the prior agent). Summary for cross-reference: Texas Natural Resources Code
§81.0523 (added by HB 40, 2015) makes oil & gas operations subject to the
state's exclusive jurisdiction and preempts municipal ordinances that purport
to regulate an oil and gas operation. Municipalities retain a narrow band of
authority limited to: (1) **aboveground activity** at or related to an
operation (not subsurface matters — casing, cementing, spacing, injection,
disposal, all RRC's domain); (2) **commercially reasonable** ordinances that
don't effectively prohibit an operation; (3) no fee beyond the actual,
reasonable cost of administering the ordinance; and (4) categories with a
history of municipal regulation — fire/emergency-response standards, traffic
and oversize/overweight routing, noise limits, lighting/dark-sky rules,
setbacks from occupied structures, pre-operation notice to the city, and
reclamation/site-restoration/landscaping conditions. Cities cannot ban
drilling outright, cannot regulate spacing/density, and cannot use zoning to
categorically exclude oil & gas from a district in a non-commercially-
reasonable way. **Not verified**: the current statutory text and any
post-2015 case law refining these boundaries.

## (b) RRC vs. TCEQ jurisdictional split — THE thing people get wrong

This was the specific focus of this run's research and is now backed by real
citations (see `tx-tceq-waste-uic-330-331-335` and `tx-rrc-swr9-disposal-wells`
records in tx-state.yaml):

- **The controlling rule is 16 TAC §3.30 (mirrored at 30 TAC §7.117)** — the
  Memorandum of Understanding between RRC and TCEQ, effective July 1, 2025 (a
  prior version was effective before that date; confirm which version governs
  for any historical determination). Wastes from oil, gas, and geothermal
  E&P activities that are subject to RRC regulation remain under **RRC**
  jurisdiction even when they are processed, treated, or disposed of at a
  TCEQ-authorized Chapter 330 solid-waste facility.
- **Underground injection control (UIC) is split by well class, not by
  "who touches oil and gas":**
  - **RRC holds Class II UIC primacy** — produced-water/oil-gas-waste
    disposal wells (Statewide Rule 9, Form W-14, into non-productive
    formations) and enhanced-recovery/EOR injection into productive
    formations (Statewide Rule 46, Form H-1/H-1A). This is standard SWD and
    waterflood/huff-n-puff work at a midstream site.
  - **TCEQ holds Class I, III, V, and VI UIC jurisdiction** under 30 TAC
    Ch. 331 and Texas Water Code Ch. 27 (TCEQ has UIC jurisdiction over
    injection wells UNLESS the activity is RRC-jurisdictional). Class I is
    hazardous/industrial/municipal waste injected below the lowermost
    underground source of drinking water (USDW); Class III is solution
    mining; Class V is shallow non-hazardous injection (remediation, ASR);
    Class VI is anthropogenic CO2 geologic storage.
  - **Practical trap**: a midstream site can have BOTH an RRC Class II SWD
    well (produced water) and a TCEQ Class I or VI well (e.g. a hazardous
    waste deepwell, or CO2 sequestration tied to a gas processing plant with
    carbon capture) on the same pad. Do not assume RRC "covers injection" at
    an oil & gas facility wholesale — check what is being injected and into
    what kind of formation.
- **Stormwater**: TCEQ regulates stormwater at a company's headquarters,
  permanent offices, or base-of-operations facilities (MSGP TXR050000); RRC
  regulates oil & gas field/production-site stormwater. A gas processing
  plant or compressor-station office/yard is TCEQ; the wellsite/gathering
  system in the field is RRC.
- **Air**: TCEQ has full and undivided air-quality jurisdiction over oil &
  gas facilities (permits by rule, standard permits, Title V/GOP-514) — there
  is no RRC air program. This is the one program area with no split at all.
- **Waste generally**: RRC-jurisdictional E&P waste (drilling fluids, produced
  water, tank bottoms while under RRC's oilfield-waste rules — see the new
  Chapter 4 regime in tx-west.yaml's `tx-rrc-ch4-waste-rules-2025` record) is
  RRC's; non-E&P industrial waste at a midstream facility (used oil, spent
  solvents, non-exempt NORM at a gas plant) is TCEQ's under 30 TAC Ch. 335.

## (c) Edwards Aquifer (30 TAC Ch. 213) trigger

Confirmed and detailed in `tx-tceq-edwards-aquifer-ch213`. Any regulated
activity (construction, pipeline installation, land clearing, AST/UST
installation) over the Edwards Aquifer **Recharge Zone or Transition Zone**
requires an approved **Water Pollution Abatement Plan (WPAP)** before any
soil disturbance; over the **Contributing Zone**, a **Contributing Zone Plan
(CZP)** is required. Administrative review runs up to 30 days; technical
review of an administratively complete application runs up to 90 days (30
TAC §213.4(e)). Geographically this program is centered on the Balcones
Fault Zone / Central Texas corridor (Kinney–Uvalde–Medina–Bexar–Comal–Hays–
Travis–Williamson), which is a hard trigger for pipelines and midstream
facilities that transit or originate in Central Texas or near the Permian/
Eagle Ford's eastern edge. **Not verified this run**: the exact zone boundary
relative to any specific project route — always check TCEQ's Edwards Aquifer
zone GIS layer (linked in the record) rather than assuming from county name
alone.

## (d) SWR 36 (H2S) trigger

Confirmed in `tx-rrc-swr36-h2s`: Statewide Rule 36 (16 TAC §3.36) applies to
drilling, workovers, production, storage, injection, and transportation of
hydrocarbon fluids containing H2S. **Form H-9 (Certificate of Compliance)**
must be filed at least 30 days before commencing drilling or workover
operations where H2S triggers the rule's radius-of-exposure calculation.
This is a critical trigger for the **Permian Delaware Basin** — Reeves,
Loving, Ward, Winkler, Culberson, Pecos, Reagan, and Crockett counties are
widely known for sour gas — affecting pipeline routing, compressor-station
siting, and gas-plant siting decisions. **Not verified this run**: the exact
ppm concentration threshold that triggers the rule and the current H-1/H-2
form identifiers used alongside H-9 (the H-1/H-1A forms confirmed this run
are actually the Statewide Rule 46 fluid-injection forms, NOT H2S forms —
this is a naming trap the task brief itself may have conflated; verify
directly against the Statewide Rule 36 PDF text linked in the record before
citing a specific H-1/H-2 form number for H2S purposes).

## (e) Groundwater Conservation Districts — all 8 named districts verified

All eight GCDs named in the task brief were confirmed with real, working
landing URLs this run (see `tx-gcd-*` records): Middle Pecos (mpgcd.org),
Santa Rita (santaritauwcd.org), Permian Basin UWCD (pbuwcd.com), Panhandle
GCD (pgcd.us), High Plains UWCD No. 1 (hpwd.org), North Plains GCD
(northplainsgcd.org), Hemphill County UWCD (hemphilluwcd.org), and Llano
Estacado UWCD (llanoestacadouwcd.org — covers Gaines County specifically;
note the adjoining Sandy Land UWCD (Yoakum County) and South Plains UWCD
(Terry/Hockley County) are DISTINCT districts not covered in the task's
8-district list and NOT researched this run — flag if Yoakum/Terry County
water sourcing is in scope for a specific project).

## What could NOT be verified this run (explicit list)

- **TCEQ**: exact fee schedules and typical processing timelines for most
  permits (PBR registration turnaround, Standard Permit 116.620 review time,
  GOP-514 ATO timeline, CGP/MSGP NOI effective-date mechanics) were not
  independently confirmed — search results describe the programs but rarely
  quote current fee tables or day-counts. Treat all `typical_timeline_days`
  and `fee` fields in TCEQ records as indicative, not authoritative.
- **RRC**: Form PS-79, PS-80, PS-81 (named in the task brief) were not
  individually confirmed — only PS-48 (new construction) and PS-95
  (semi-annual leak report) were found with working links; the R-1 through
  R-9 series (referenced in the task brief, believed to be radioactive
  material/NORM-related forms) were not searched this run at all. Forms
  W-1/W-2/W-3 (drilling permit family) were not searched — this file relies
  on tx-west.yaml's Ch. 3 statewide-rules index and does not duplicate a
  dedicated W-1 record; if tx-west.yaml lacks one, that is a gap.
- **RRC SWR 36 exact H2S ppm threshold** — described qualitatively in every
  source found, but the precise regulatory concentration trigger and the
  exact ROE (radius of exposure) calculation formula were not confirmed
  from the rule text search snippet; confirm against the full Statewide Rule
  36 PDF (linked in the record) before using a specific number.
- **TxDOT**: whether the legacy "UIR" (Utility Installation Review) system
  named in the task brief has been fully superseded by RULIS (Right of Way
  Utility and Leasing Information System), or the two coexist for different
  transaction types, was not resolved — both are documented in the record
  with that ambiguity flagged.
- **TPWD**: whether pipeline/utility crossings are categorically EXEMPT from
  the Marl/Sand/Gravel/Shell/Mudshell permit (search snippets mentioned a
  pipeline/utility exemption but did not give the exemption's exact statutory
  citation or scope) — confidence marked `unverified` on that record
  specifically because of this ambiguity. Do not assume a project is exempt
  without confirming against Parks & Wildlife Code Ch. 86 directly.
- **GLO**: exact fee schedule, application form number, and processing
  timeline for a state-land/submerged-land pipeline easement were not found
  (only the program landing page and a real example CMP consistency filing
  by Targa Downstream LLC were confirmed).
- **THC**: the notification threshold and process for determining whether a
  specific tract counts as "political subdivision land" (e.g., a county road
  ROW vs. private ROW running parallel to a county road) was not resolved —
  the 30-day THC response window and general trigger are confirmed, but edge
  cases at the state/private land boundary were not.
- **Sandy Land UWCD (Yoakum County) and South Plains UWCD (Terry/Hockley
  County)** — adjoining districts to Llano Estacado UWCD, mentioned in
  passing in search results but not independently searched/added as records.
- **County-level and municipal records** are explicitly out of scope for
  this file (owned by other agents / tx-west.yaml, tx-east.yaml) and are not
  addressed here.

## Top 5 unverified items (for the final reply)

1. Exact TCEQ permit fees and processing-day timelines (PBR/Standard
   Permit/GOP-514/CGP/MSGP) — programs confirmed, numbers not.
2. RRC pipeline-safety Forms PS-79/PS-80/PS-81 and the R-1–R-9 series —
   named in the task brief but no working URL found this run.
3. Exact SWR 36 H2S ppm/ROE trigger threshold and the correct H-1/H-2 vs.
   H-9 form mapping (H-1/H-1A confirmed as SWR 46 EOR-injection forms, not
   H2S forms — needs a targeted re-check against the SWR 36 rule text).
4. TPWD Sand/Gravel/Marl permit exemption scope for pipelines/utilities
   (exemption exists per search snippet; exact statutory carve-out not
   confirmed).
5. TxDOT UIR-vs-RULIS system status (superseded, coexisting, or
   transitional) for utility crossing permits on state highway ROW.
