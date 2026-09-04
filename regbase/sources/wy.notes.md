# Wyoming Source Registry - Research Notes (2026-09-04)

Session hit its WebSearch budget (200 calls) after covering state agencies, all
23 counties, and 6 of 34 requested municipalities. `wy.yaml` contains 44
validated records (0 schema errors against `regbase/schemas/source.schema.json`).

## (a) County zoning status

**Counties with NO county-wide zoning** (confirmed via search):
- **Fremont** - no zoning or county building code at all; only floodplain zoning + small-wastewater (septic) permits.
- **Big Horn** - no county-wide zoning; only localized Airport Protection zoning.
- **Weston** - no zoning ordinance; only subdivision regulations. State agencies (DEQ, SEO, Fire Prevention) fill the gap for sewer/well/construction.
- **Niobrara** - has a "zoning board" but it only handles land-split/subdivision review; no charge, no permit requirement identified - effectively no substantive zoning code.
- **Campbell** - no *county-wide* zoning; only individually zoned subdivisions carry zoning classifications (Zoning Certificate required there only).

**Counties confirmed to have zoning/development regulations:**
Converse, Sublette, Sweetwater, Natrona, Carbon, Laramie, Lincoln, Uinta,
Sheridan, Park, Platte, Albany, Teton (Jackson/Teton joint LDRs, on Municode).
Sheridan County's zoning explicitly names "Mineral and Oil and Gas Extraction"
as a regulated use category. Laramie County runs a standing weekly (Wed 1pm)
oil & gas pre-application meeting slot with Planning/Public Works/Environmental
Health.

**Ambiguous / could not confirm zoning status (marked `unverified` in YAML):**
- **Johnson** - materials referred to "Draft Zoning Regulations"; adoption status unconfirmed.
- **Washakie** - has adopted Subdivision *and Development* Regulations (2023/2024); unclear if this constitutes full district-based zoning.
- **Hot Springs** - has a Land Use Plan and subdivision/septic permitting; no zoning-district ordinance was located.
- **Crook** - has a Land Use Planning & Zoning Commission but the underlying zoning-ordinance text (vs. subdivision-review-only authority) was not located.
- **Goshen** - only a Planning Commission was confirmed; zoning status entirely unresearched beyond that.

## (b) Industrial Siting Act threshold & trigger

W.S. 35-12-101 et seq. (Wyoming Industrial Development Information and Siting
Act) requires an **Industrial Siting Permit** from the Industrial Siting
Council for facilities (including large gas plants/pipelines) whose estimated
construction cost exceeds a statutory threshold. Base threshold in statute is
**$96,000,000**, escalated annually by the Council using construction-cost
indices.

**Could not verify the exact current-year dollar figure** - search results
gave two inconsistent numbers without clear vintage: one source cited
~$231,000,000 as "current"; another cited a $283,166,876 full-permit trigger
with a lower $226,533,500 threshold requiring only a "Certificate of
Insufficient Jurisdiction." These may be from different years or different
tiers of the same schedule. **Before using this threshold in any client-facing
determination, pull the Industrial Siting Council's current-year adjusted
threshold directly** (https://deq.wyoming.gov/industrial-siting-2/permitting/).
This is flagged `confidence: unverified` in wy.yaml (`wy-deq-industrial-siting`).

## (c) Sage-grouse Core Area implications

Wyoming's sage-grouse policy is set by **gubernatorial Executive Order** (currently
Gov. Gordon's EO), not by WOGCC/DEQ rule directly - it is implemented through
BLM/state-land lease stipulations and as conditions attached to WOGCC permits
and OSLI easements for projects touching a designated Core Population Area.
Key standard found: **no more than 5% surface disturbance** may be classified
as "disturbed" within a Core Area. A companion EO addresses Mule Deer/Antelope
migration corridors. WGFD publishes "Recommendations for Development of Oil
and Gas Resources" as the operating guidance document
(https://wgfd.wyo.gov/media/2358/download). For a midstream pipeline or
compressor station sited in/near a Core Area, expect WGFD comment, a Core Area
disturbance calculation, and likely BLM/OSLI stipulations layered on top of
standard WOGCC/DEQ permitting - this is a cross-cutting siting constraint, not
a distinct standalone permit, so it is captured as a `wildlife` authority-type
record rather than a permit line item.

## (d) What could NOT be verified / gaps

- **28 of 34 requested municipalities were never researched** (session ran out
  of WebSearch budget): Rock Springs and 5 others (Casper, Gillette, Douglas,
  Cheyenne, Pinedale) ARE in wy.yaml; **NOT researched**: Green River,
  Evanston, Riverton, Lander, Rawlins, Sheridan (city), Buffalo, Wright,
  Glenrock, Mills, Bar Nunn, Evansville, Cody, Worland, Newcastle, Torrington,
  Kemmerer, Laramie (city), Thermopolis, Basin, Sundance, Upton, Moorcroft,
  Lusk, Wheatland, Saratoga, Midwest, Edgerton. No entries were fabricated for
  these - re-run with a larger search budget to fill them in.
- **WYDOT Utility Accommodation Regulation** URL found is a 2004 LSO archive
  copy - needs re-verification against WYDOT's current site.
- **Wyoming Water Quality Rules Chapter 11** URL is from an EQC "closed cases"
  archive - needs verification against the Secretary of State's current
  rules.wyo.gov text before citing as authoritative.
- **Wyoming Pipeline Authority -> Wyoming Energy Authority (WEA)** renaming
  was mentioned in a secondary source but WEA's own current site was not
  located/confirmed - `wy-pipeline-corridor-initiative` is `unverified`.
- **Wyoming811 / One-Call landing URL** - could not confirm a direct
  wyoming811.com URL; only PHMSA and Wyoming Pipeline Association pages
  referencing it were found. Marked `unverified`.
- **DEQ Land Quality Division** and **Solid & Hazardous Waste Division
  Chapter 8** (reserve pits) - only division landing pages were confirmed;
  the specific O&G-waste regulation text/citation was not independently
  pulled. Both marked `unverified`.
- **Gillette's code platform** is EnCodePlus (online.encodeplus.com), which
  has no matching enum value in `source.schema.json`'s `code_platform` list;
  mapped to the closest available value (`sterling`) with a note flagging
  this - worth adding a proper `encodeplus` enum value to the schema.
- Individual WOGCC form URLs (Form 1, 3, 4, 7, 8, 15, 16) were not each
  pulled directly - only the eForms index page was confirmed; per-form direct
  links should be verified before building a machine link table.
- County-level oil & gas-specific chapter text (vs. general zoning) was
  confirmed distinctly only for Laramie (dedicated O&G program page) and
  Sublette (O&G waste disposal facility definitions) and Sheridan (named
  zoning use category); other counties' zoning docs were not searched deeply
  enough to confirm/deny an O&G-specific chapter.
