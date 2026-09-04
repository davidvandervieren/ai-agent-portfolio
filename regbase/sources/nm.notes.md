# New Mexico regulatory source registry — research notes (2026-09-04)

Covers `regbase/sources/nm.yaml` (28 source records). Research tool was WebSearch only
(no fetch/curl); the session's WebSearch budget was exhausted partway through the
municipal pass (200/200 calls used), which is why municipal coverage below is thin —
see "Not verified / not reached" at the bottom.

## (a) Counties: zoning vs. no zoning

- **Confirmed:** Socorro County has no zoning (found directly in search results — real
  estate/land-use commentary calling out Socorro as zoning-free "just south of
  Albuquerque").
- **Could not confirm a full list.** New Mexico county zoning authority is enabling,
  not mandatory (NMSA 1978 § 3-21-1 lets counties adopt zoning but does not require
  it), and no authoritative single source enumerating every NM county's zoning status
  turned up in search. What the search did surface:
  - Counties with an identifiable land-use/zoning or O&G-specific ordinance apparatus:
    Lea (Planning Dept + subdivision regs, no confirmed dedicated O&G chapter),
    Eddy (O&G drilling ordinance O-75-05), Chaves (Planning & Zoning Commission,
    ordinance text not confirmed), San Juan (Land Use, Development and Management
    Ordinance), Rio Arriba (Oil and Gas Ordinance 2009-01), Sandoval (draft/contested
    O&G ordinance, Municode-hosted general code), Santa Fe (Ordinance 2009-11,
    Municode-hosted).
  - Roosevelt County has an ordinances/resolutions page but content not confirmed.
  - Mora County had a 2013 outright drilling ban, later struck down (2015) and
    repealed by the county itself the same year — see history section below.
  - The remaining 24 counties in scope (Chaves partially covered; Bernalillo,
    Torrance, Colfax, Union, Harding, Quay, De Baca, Otero, Lincoln, Guadalupe,
    Cibola, Valencia, Sierra, Luna, Hidalgo, Grant, Catron, San Miguel, Taos,
    Los Alamos, Curry, Dona Ana) were **not individually searched** this pass due to
    the search-budget cutoff. Treat their zoning/no-zoning status as unknown, not as
    "no zoning" by default — do not assume absence of a finding means absence of a
    zoning ordinance.
- **Practical implication:** for counties without confirmed zoning, oil & gas
  midstream siting review defaults almost entirely to state (OCD/NMED/PRC/SLO) and
  any county subdivision/road-cut/floodplain rules that exist independent of zoning.

## (b) ETZ / extraterritorial jurisdiction implications

New Mexico municipalities can hold extraterritorial zoning authority extending
control beyond city limits (via joint city-county extraterritorial planning/zoning
commissions under state enabling law). This session was **not able to confirm
specific ETZ boundaries or ETZ ordinance text for any individual municipality** —
the municipal research pass ended before it began due to the search-budget cutoff.
Practically, for a pipeline/compressor/SWD project sited near Hobbs, Carlsbad,
Artesia, Farmington, Aztec, Roswell, Clovis, Rio Rancho, Las Cruces, or other cities
in scope, an ETZ check against that city's extraterritorial platting/zoning authority
should be treated as an **open, unverified item** — do not assume county zoning
(or its absence) is the only applicable land-use layer near any of these cities.

## (c) 20.2.50 NMAC Ozone Precursor Rule — affected counties (CONFIRMED)

Effective 2022-08-05. Per NMED/third-party rule-tracking summary found in search:
**Chaves, Dona Ana, Eddy, Lea, Rio Arriba, Sandoval, San Juan, and Valencia**
counties are subject to the rule. Bernalillo County is explicitly excluded because it
runs its own separate air quality regulatory agency (Albuquerque-Bernalillo County
Air Quality Program), not the state NMED/AQB program.

Primary sources captured in `nm.yaml` (`nmed-20-2-50-ozone-precursor-rule`):
- https://www.srca.nm.gov/parts/title20/20.002.0050.html (adopted rule text, SRCA)
- https://www.env.nm.gov/air-quality/wp-content/uploads/sites/2/2022/07/Oil-and-Gas-Sector-Ozone-Precursor-Polutants-Final-rule-20.2.50-NMAC-06Jul22.pdf

The county list itself came from a WebSearch AI-summary of secondary sources
(ALL4, Platinum Control, CDH Consulting), not a direct read of the NMED PDF's
applicability section — confidence marked `verified` because the two independent
compliance-consulting summaries agree and match the rule's known geographic focus
(San Juan Basin + Permian Basin ozone-precursor counties), but the applicability
section of the rule PDF itself was not independently re-read line-by-line.

## (d) What could NOT be verified this pass

**Hard constraint:** WebSearch is capped at 200 calls per session and the cap was
hit mid-task, before any municipality-specific searches beyond Carlsbad and Roswell
could run. No WebFetch/curl was available as a fallback (both blocked by egress
proxy per task instructions), so nothing below could be double-checked or expanded.

- **Municipalities not researched at all:** Hobbs, Lovington, Jal, Eunice, Loving,
  Tatum, Farmington, Aztec, Bloomfield, Kirtland, Clovis, Portales, Rio Rancho,
  Bernalillo (city), Cuba, Raton, Santa Fe (city), Albuquerque, Las Cruces, Gallup,
  Grants, Espanola, Tucumcari, Hatch, Dexter, Hagerman. No entries were added to
  `nm.yaml` for these — fabricating Municode/ecode360/self-hosted URLs was avoided
  per the "never guess" rule. These need a fresh research pass.
- **Municipalities partially researched:** Carlsbad (confirmed Ch. 34 "Oil and Gas
  Wells and Pipelines" on Municode) and Roswell (confirmed 2020 zoning ordinance PDF,
  but no dedicated O&G/pipeline chapter located within it).
- **County code_platform for most counties:** left as `unknown` where no Municode/
  American Legal/ecode360 landing page was actually seen (e.g., Lea, Chaves,
  Roosevelt). Do not assume `municode` just because many NM counties use it.
- **NM Produced Water Act — current rulemaking status of 20.6.8 NMAC:** the WQCC/
  NMED rulemaking to regulate produced-water reuse *outside* oil & gas jurisdiction
  appeared, in search results, to still be in a "proposed rule" / public-participation
  phase as of the sources found. Whether 20.6.8 NMAC has since been formally adopted
  was **not confirmed** — marked `confidence: probable` in the registry.
- **Sandoval County O&G ordinance adoption status:** search results describe a
  contentious multi-year (2017-2021+) drafting process, industry pushback (NMOGA
  litigation threat over a proposed 750-ft setback), and a failed amendment vote, but
  **no source confirmed whether a final ordinance is currently in force**, and if so
  its current setback/permitting terms. This is flagged `unverified` in the registry
  and should be checked directly against Sandoval County's Municode code tree
  (https://library.municode.com/nm/sandoval_county) before being relied on.
- **NMDGF (Game & Fish) pipeline/stream-crossing permit specifics:** could not locate
  a named permit/form for O&G pipeline stream/habitat crossings; NMDGF coordination
  appears to be informal/consultative alongside OSE and federal ESA review rather than
  a standalone permit — unconfirmed.
- **Navajo Nation NNDFW biological clearance and formal ROW permit/fee schedule:**
  not located; only general DNR/EPA landing pages and one 2026 news item about a
  Tallgrass/GreenView pipeline ROW resolution were found.
- **Southern Ute / Ute Mountain Ute (NM border crossings):** not researched at all
  this pass — out of budget.
- **19.15.34 NMAC, 19.15.9 NMAC and other specific OCD parts** named in the task
  brief were reached only via the OCD rules index landing page
  (og-rules-and-forms/), not opened and cited individually — treat citation_root
  references to these parts as index-level, not confirmed part-by-part.
- **NMDOT utility permit application (A-063b):** the only working link found was a
  third-party bid-document mirror (realfile.rtsclients.com), not dot.nm.gov itself —
  flagged `probable`, needs a direct dot.nm.gov ePermitting link.
- **GCP-O&G $17,550 fee figure:** sourced from a compliance-consulting third party
  (ALL4), not directly confirmed on the env.nm.gov fee schedule page — flagged in the
  document's own `notes` field.

## Recommended next pass

1. Spend a fresh WebSearch budget entirely on the 26 unresearched municipalities,
   prioritizing Hobbs, Carlsbad (deepen), Artesia, Lovington, Jal, Eunice (Lea/Eddy
   cluster — highest Permian midstream density) and Farmington, Aztec, Bloomfield,
   Kirtland (San Juan Basin cluster).
2. Confirm Sandoval County's current O&G ordinance status directly on Municode.
3. Confirm ETZ boundaries/ordinances for at least Hobbs, Carlsbad, Farmington, Roswell,
   Rio Rancho, Las Cruces, Santa Fe city, Albuquerque.
4. Re-fetch the 20.2.50 NMAC PDF's applicability section directly (not via AI-search
   summary) to lock down the affected-county list with a primary-source pin cite.
5. Determine current adoption status of 20.6.8 NMAC (produced water reuse outside
   O&G).
