# Federal Source Registry — Notes

`regbase/sources/federal.yaml` — 37 records, federal/cross-cutting scope only. Reviewed 2026-09-04.

## (a) Applicability matrix — federal triggers by asset type

Legend: X = routinely applies · (X) = conditional / fact-specific · — = generally does not apply

| Federal requirement | Midstream pipeline | Produced water line | SWD well | Compressor station | Gas processing plant |
|---|---|---|---|---|---|
| PHMSA 49 CFR 192/195/199 (pipeline safety, OQ, IM, incident reporting) | X | (X) — only if line meets 195/regulated-gathering definition | — | X | X (facility piping) |
| PHMSA gathering line rule (Type A/B/C/R) | X (gas gathering) | — | — | (X) if co-located | — |
| PHMSA National Registry / OPID | X | (X) | — | X | (X) |
| FERC NGA §7(c) certificate | (X) — only if interstate-jurisdictional transmission, not gathering | — | — | (X) if on a jurisdictional line | — |
| FERC blanket certificate | (X) — same jurisdictional line-drawing as above | — | — | (X) | — |
| FERC Form 2/2-A/3-Q | (X) — jurisdictional interstate pipelines only | — | — | — | — |
| NGPA §311 / gathering exemption analysis | X (threshold question for every gathering system) | — | — | — | — |
| EPA UIC Class II permit | — | (X) if line feeds a Class II well | X | — | — |
| NSPS OOOO/OOOOa/OOOOb, EG OOOOc | (X) fugitive components | — | — | X | X |
| NESHAP HH/HHH | — | — | — | X (if co-located w/ dehydration) | X |
| Subpart W GHG reporting (40 CFR 98) | X (transmission/gathering segment) | — | X | X | X |
| Title V / PSD / NSR / synthetic minor | — | — | — | X (major or synthetic-minor) | X |
| USACE CWA §404 (NWP 12/3/14, IP) + §10 | X (water crossings) | X (water crossings) | (X) access road only | (X) access road/site prep | (X) access road/site prep |
| CWA §401 WQC | (X) — rides with 404/FERC actions | (X) | — | (X) | (X) |
| NPDES CGP / SWPPP (1+ acre) | X | X | X (pad construction) | X | X |
| SPCC (40 CFR 112) / FRP | (X) if aboveground oil storage | (X) | (X) if tanks present | (X) | X |
| ESA §7 / §10, IPaC | X (federal nexus or listed-species range) | X | X | X | X |
| MBTA / BGEPA | (X) | (X) | (X) | X (flares, structures) | X |
| NEPA (BLM ROW / USACE permit nexus) | X (if federal nexus) | X (if federal nexus) | X (if on federal/Indian minerals) | X (if federal nexus) | (X) |
| BLM ROW (Form 2800-14, FLPMA Title V) | X (crosses BLM land) | X (crosses BLM land) | — | X (crosses BLM land) | (X) |
| BLM APD (3160-3) / Sundry (3160-5) | — | — | X (federal/Indian minerals) | — | — |
| BIA tribal ROW (25 CFR 169) | X (crosses tribal/allotted land) | X | (X) | X | (X) |
| NHPA §106 / SHPO-THPO | X (federal nexus) | X | X (federal nexus) | X | (X) |
| OSHA PSM (1910.119) | — | — | — | (X) if HHC threshold met | X |
| EPA RMP (40 CFR 68) | — | — | — | (X) | X |
| EPCRA 302/311/312/313 | — | — | (X) | X (chemical inventory) | X |
| FAA Form 7460-1 | — | — | — | X (flare/stack height) | X (flare/stack height) |

Notes on the matrix: "federal nexus" for NEPA/ESA §7/NHPA §106 means the project needs *some* federal authorization (BLM ROW, USACE 404 permit, FERC certificate, BIA ROW). Purely private/state-permitted midstream projects with no federal land, water, or funding touchpoint can fall outside NEPA/ESA-§7/NHPA-§106 entirely and instead face ESA §10 / MBTA exposure without a Section 7 consultation pathway.

## (b) Could NOT verify — human should check

1. **USACE district boundaries for CO/WY/NM/UT/TX** (Albuquerque, Omaha, Sacramento, Tulsa, Fort Worth, Galveston). I could not retrieve a working district-specific regulatory-program URL for each district before the search budget for this session was exhausted — `usace-cwa-404-permitting` cites only the national USACE Nationwide Permit and Locations pages. A human should pull each district's actual "Regulatory Program" page and confirm which district(s) cover which counties in each state (district lines do not follow state lines cleanly, especially in CO/NM/UT).
2. **EG OOOOc state-plan status per state.** Whether CO, WY, NM, UT, and TX have EPA-approved OOOOc state plans in effect (vs. a federal plan applying) was not confirmed. This determines *when* existing-source methane/VOC standards actually bind a given facility.
3. **2026 OOOOb/OOOOc reconsideration and "burden reduction" rulemaking.** Search results referenced an EPA "2026 Final Rule to Reduce Burden on the Oil and Natural Gas Industry" and an April 4, 2026 reconsideration, both after my knowledge cutoff. The exact current text of NSPS OOOOb / EG OOOOc should be re-confirmed against eCFR before relying on specific numeric thresholds.
4. **NWP 12 (and the broader Nationwide Permit set) current expiration/reissuance status.** The 2021 reissuance was set to expire March 14, 2026; a Federal Register notice dated January 8, 2026 indicates a further reissuance/modification cycle was underway. I could not confirm whether new NWP 12 terms are now in effect, or what the current expiration date is.
5. **NESHAP HH/HHH reconsideration (announced April 2026).** EPA announced a technology review and reconsideration of the 2012 HH/HHH amendments; I could not confirm whether a proposed or final rule has since issued, or what it changes.
6. **Lesser prairie-chicken current federal status.** This is genuinely volatile: listed in 2022 (two DPS), vacated by a Texas federal court in August 2025 at USFWS's own request, formally delisted by USFWS on February 26, 2026, with a new 12-month status review opened (comment deadline March 30, 2026 per one source). **As of this review the species is NOT ESA-listed**, but this could change again within months — treat as a live litigation/rulemaking tracker, not a settled fact.
7. **Dunes sagebrush lizard critical habitat.** Listed as endangered effective June 20, 2024, but the final listing rule did not designate critical habitat; USFWS reportedly had ~1 year to propose it. I could not confirm whether a critical-habitat proposed or final rule has since been published.
8. **ACHP Section 106 tribal-consultation rule overhaul (reported July 2026).** Industry alerts referenced a "sweeping overhaul" of Section 106 tribal consultation regulations proposed by ACHP; I could not confirm rule status, comment deadlines, or effective date.
9. **BIA right-of-way process specifics per tribe** (Navajo Nation, Southern Ute, Ute Mountain Ute, Uintah & Ouray/Ute, Jicarilla Apache, Wind River/Eastern Shoshone-Northern Arapaho). The federal 25 CFR 169 framework is documented, but consent thresholds and each tribe's own code/process supplementing 169 were not individually verified — these can differ materially by tribe and should be confirmed with the specific BIA agency office and tribal government before relying on any generic timeline.
10. **FERC "gathering vs. jurisdictional transmission" line-drawing** is inherently fact-specific (the *Farmland Industries* primary-function test) and was described only at a conceptual level — no specific current FERC declaratory orders were pulled. Any specific midstream system's jurisdictional status should be independently assessed (often via outside counsel / a FERC declaratory order request), not inferred from this registry.
11. **State-level Class II UIC primacy dates** (TX 1982, NM 1982, CO 1984, WY 1982, UT 1982) were taken from search-result summaries of EPA/state pages rather than the primary Federal Register primacy-approval notices themselves — dates are believed correct (verified confidence) but the underlying FR citations were not individually pulled for each state.
12. **EPA NPDES program delegation status per state** for the Construction General Permit record — CGP applicability depends on whether EPA or the state is the NPDES permitting authority in a given location; CO/WY/NM/UT/TX authority status (mostly state-delegated, with some federal-lands/tribal exceptions) should be confirmed per state/facility rather than assumed from the federal CGP record alone.

## Session/search constraints
All research was done via `WebSearch` only (no direct page fetches — `WebFetch`/`curl`/`wget` are blocked in this environment); every URL in `federal.yaml` was transcribed verbatim from a WebSearch result. This WebSearch session hit its call budget near the end of research (used for the six items above plus the USACE district lookups), so items 1 and a few secondary cross-checks were left unverified rather than guessed.
