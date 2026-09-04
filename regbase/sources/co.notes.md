# Colorado RegBase Source Notes

Compiled via WebSearch only (no direct page fetches — WebFetch/curl/wget are blocked in this
environment). All URLs were transcribed verbatim from search results. 79 records total in
`co.yaml`: 11 state agencies, 30 counties, 38 municipalities. Confidence breakdown:
22 verified, 33 probable, 24 unverified.

## (a) Counties confirmed to have adopted 1041 (Areas & Activities of State Interest) regulations

Confirmed via direct evidence (adopted regulation text, county code article, or a
DLG/Colorado Counties Inc. case study naming the jurisdiction):

- **Weld County** — Article V of the Charter and County Code designates the *entire*
  unincorporated county as a Mineral Resource Area of State Interest (Ord. 2019-10), adopted
  under AASIA (24-65.1-101 et seq.). This is Colorado's most aggressive use of 1041 powers for
  oil & gas.
- **Boulder County** — Land Use Code Article 8 (1041 / Location and Extent review).
- **Larimer County** — Land Use Code Article 10.0 (1041 Regulations), adopted 2008.
- **Adams County** — Uses a 1041 "Areas and Activities of State Interest (AASI)" permit
  alongside its Oil and Gas Facility (OGF) permit (Accela case type "RCU").
- **Cheyenne County** — "Regulations for Areas and Activities of State Interest" adopted 2019
  (direct PDF found on county site) — notable because it's a small eastern-plains county, not
  one of the usual mountain/urban-corridor 1041 adopters.
- **Town of Silt** (Garfield County) — confirmed via a Colorado DLG 1041 case study page
  ("Use of 1041 Regulations Case Study: Town of Silt").
- **Arapahoe County** — has a dedicated Land Development Code oil & gas amendment (2021,
  strengthened 2023-24) but I found no direct evidence of a 1041 program specifically; DLG lists
  it in the case-study index (URL pattern `dlg.colorado.gov/use-of-1041-regulations-Arapahoe-County`
  was returned by search but not opened/confirmed) — **flagged, not fully verified**.

Counties named as 1041 adopters elsewhere in secondary sources but **not independently
confirmed** this pass (found only in general "25 of 64 CO counties use 1041 powers" framing,
without a name-specific source): Eagle, Routt, Summit, Otero, Clear Creek. These are outside
this task's target county list except where noted.

Counties in the target list where I found **no evidence either way** of a 1041 program
(absence of evidence, not evidence of absence): Garfield (county-level; only Town of Silt
confirmed within it), Rio Blanco, Mesa, La Plata, Las Animas, Yuma, Washington, Logan, Morgan,
Elbert, Jackson, Moffat, Kit Carson, Lincoln, Pueblo, Huerfano, Archuleta, Montezuma, Delta,
Gunnison, Douglas, El Paso, Denver, Broomfield.

**Bottom line: only Weld, Boulder, Larimer, Adams, and Cheyenne counties (plus the Town of
Silt) have confirmed 1041 regulations in this pass.** This is very likely an undercount —
1041 authority is common across CO — but I will not claim it for a jurisdiction without a
directly-sourced URL, per the no-guessing rule. Follow-up research should specifically query
`dlg.colorado.gov/use-of-1041-regulations-<County>` and `dlg.colorado.gov/land-use-codes` for
each remaining target county.

## (b) Jurisdictions with express oil & gas / pipeline chapters vs. none confirmed

**Express, dedicated O&G chapter/article confirmed (state or local code text located):**
State: ECMC 100-1200 series rules (all); CDPHE Reg 7/Reg 3/Reg 22.
Counties: Weld (Art. V), Boulder (Art. 12), Larimer (Art. 11.0), Garfield (Art. 7/9 LUDC),
Rio Blanco (Art. 9), La Plata (Ch. 90), Las Animas (dedicated O&G reg PDF), Arapahoe
(2024 LDC O&G amendment), Broomfield (Ch. 17-54), Morgan (Zoning Regs, O&G use
classification), Cheyenne (1041 regs), Douglas (DCZR Sec. 21), Adams (OGF permit + guidance
doc), Moffat (APD county-review process).
Municipalities: Greeley (Ch. 16 & 18), Erie (Title 10), Aurora (Ch. 135), Johnstown (Art. XI),
Longmont (Title 15), Louisville (Ch. 17.68), Thornton (Art. X), Fort Collins (Land Use Code
Art. 4, near-total ban adopted 2023), Mead (Art. X), Berthoud (Ch. 30 / Ord. 1336).

**Confirmed to have a land use/zoning code but no O&G-specific chapter located this pass**
(may still exist — just not surfaced by search): Mesa County, El Paso County, Pueblo County,
Elbert, Kit Carson, Lincoln, Jackson, Huerfano, Archuleta, Montezuma, Delta, Gunnison, Yuma,
Washington, Logan counties; and municipalities Firestone, Frederick, Dacono, Fort Lupton,
Brighton, Windsor, Loveland, Timnath, Milliken, Platteville, Superior, Lafayette, Northglenn,
Commerce City, Rifle, Parachute, Silt, New Castle, Durango, Bayfield, Trinidad, Grand
Junction, Fruita, Evans, Kersey, Eaton, Ault, Severance, Denver.

**Note on Lafayette**: the town has a well-known history of a local hydraulic-fracturing ban
ordinance; I could not confirm its current legal status (largely superseded/preempted by
SB19-181 and later state law) in this pass — flagged for follow-up, do not rely on the
"unverified" Lafayette record for current enforceability.

## (c) Explicit list of what could NOT be verified (do not treat as fact)

- **co-yuma-county-landuse, co-washington-county-landuse, co-elbert-county-zoning,
  co-huerfano-county-landuse, co-montezuma-county-landuse, co-delta-county-landuse,
  co-gunnison-county-landuse** — only a generic planning department page found; no
  confirmed O&G-specific chapter, code platform, or 1041 status.
- **co-pueblo-county-udc** — Pueblo consolidated its Titles 16/17 into a "Unified
  Development Code" per search snippets, but I could not locate a working Municode/direct
  URL for the UDC itself this pass. `code_platform` marked `municode` based on the
  historical Chapter 16 Municode URL fragment seen, but this is unconfirmed for the current
  UDC.
- **co-frederick-municode, co-fort-lupton-municode, co-brighton-municode,
  co-loveland-municode, co-timnath-municode, co-platteville-municode, co-superior-municode,
  co-lafayette-municode, co-northglenn-municode, co-parachute-municode,
  co-bayfield-municode, co-evans-municode, co-kersey-municode, co-eaton-municode** —
  Municode landing page located, but no O&G-specific chapter/article confirmed.
- **co-ault-municode** — could not confirm a Municode (or any) code URL for the Town of Ault
  directly; the URL in `co.yaml` follows the pattern used by neighboring Weld County towns
  but was **not independently verified** — treat as a placeholder, re-verify before use.
- **co-trinidad-municode** — Trinidad's code portal (trinidad.co.gov) does not appear to be
  Municode-hosted; only utility/gas-tariff chapters were found, no O&G land-use/drilling
  chapter confirmed.
- **CDOT Form 101 / Form 333** — the task brief named these form numbers; search only
  surfaced "Form 1233" as CDOT's utility/special-use permit form. The Form 101/333 naming
  could not be corroborated and may be outdated or a different CDOT process (e.g. access
  permits vs. utility permits) — flagged in the `co-cdot-utility-permits` record's permit
  notes.
- **ECMC Form 31 vs Form 33** — confirmed both exist and are UIC-related (Form 31 =
  Underground Injection Formation Permit Application - Intent), but I could not fully verify
  the precise "Subsequent" vs. "Intent" split description beyond the search snippet's own
  characterization; recommend a direct confirm against the ECMC forms page before citing to
  a client.
- **Grand Junction code platform** — search returned it hosted on both `codepublishing.com`
  and `ecode360.com` (`GR4464`); recorded `code_publishing` with a note flagging the conflict
  — verify which is authoritative.
- **CDPHE Regulation 3 (APEN/construction permit) and Regulation 61 exact regulation-text
  URLs, GP01/GP02 general permit text, and Alternative Location Analysis rule text** —
  the search budget was exhausted (200/200 WebSearch calls used this session) before these
  could be looked up individually; only landing/summary pages are cited in `co-cdphe-apcd`
  and `co-cdphe-wqcd`. These are the most consequential known gaps — follow up directly on
  `cdphe.colorado.gov/aqcc-regulations` or equivalent.
- **GIS/ArcGIS REST endpoints** — only two were actually observed in search results:
  Douglas County's ArcGIS Hub (`https://dcdata-dougco.opendata.arcgis.com/`, confirmed
  `arcgis_rest`-style open data portal) and ECMC's Flowlines GIS Data page (data-download
  page, not a raw REST endpoint — `service_type: unknown`). No other county or municipality
  GIS/ArcGIS service URLs were confirmed this pass, despite the task's request to flag every
  one seen — for most jurisdictions none surfaced in search results.

## Session constraint note

The WebSearch tool budget (200 calls) was exhausted before Denver-specific O&G ordinance
detail, exact CDPHE regulation text URLs, and several remaining unverified municipalities
could be re-queried. If more searches are available in a follow-up session, prioritize: (1)
CDPHE Reg. 3/7/61 exact regulation-text URLs, (2) 1041 status for Garfield, Rio Blanco,
Mesa, La Plata, Douglas, El Paso, Pueblo, Gunnison, Archuleta, Montezuma, Delta counties via
`dlg.colorado.gov/use-of-1041-regulations-<County>`, (3) the ~24 "unverified" municipal
records listed above.
