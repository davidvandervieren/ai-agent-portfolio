# TX-Gulf regulatory source registry — research notes (2026-09-07)

Builds on the prior agent's `tx-east.notes.md` research plan (that agent had zero
WebSearch budget and produced no records). This pass used ~32 WebSearch calls
(shared budget) and produced 38 records / 37 permits in `tx-gulf.yaml`, covering
DFW/Barnett cities and counties, Eagle Ford counties/cities, Gulf Coast counties
and special districts, and a starter set for East Texas/Haynesville.

## 1. DFW/Barnett cities with enforceable gas well ordinances post-HB 40

All of these cities kept a distinct gas-well-drilling code chapter after HB 40
(2015). None claim to regulate the underlying O&G *operation* (RRC's exclusive
turf); all instead frame their surviving authority around the "commercially
reasonable" surface bucket HB 40 preserves: setbacks, noise, emergency
response/fire access, road-use/ROW, notice, insurance/security, and platting
adjacency to existing wells.

- **Fort Worth** (verified, `codelibrary.amlegal.com/codes/ftworth`) — Ch. 15
  "Gas": § 15-34 permit required, § 15-36 permitting procedure, § 15-42
  technical regs (noise, emergency response plans), § 15-45 plugged/abandoned
  wells, Art. III fees. This is the most complete, most citable ordinance in
  scope.
- **Denton** (probable/unverified numbers) — Municipal Code § 19-2131 plus
  Development Code Subchapter 6 per the city's own FAQ page; setback figures
  circulating online (1,000 ft standard / 250 ft reverse, or 1,200 ft per a
  different secondary source) were **not** cross-checked against the current
  ordinance text this session — numbers conflict across sources and need a
  direct pull from Denton's code library before being relied on. Historically
  significant as the city whose 2014 fracking ban triggered HB 40's passage.
- **Arlington** — Gas Drilling and Production Chapter (GDPO), adopted 2003,
  amended 2011 to a Council-approved "drilling zone" model rather than
  per-well permits; 600 ft setback from parks/protected uses, supermajority
  Council vote required inside 600 ft. Verified via the city's own ordinance
  PDF.
- **Southlake** — Article IV, Ch. 9.5 plus a mandatory Specific Use Permit;
  ~1,000 ft setback cited by secondary sources (Ordinance 880-B, 2011).
  Not independently confirmed against Southlake's own code text.
- **Colleyville** — 1,000 ft setback cited only by a third-party well-tracking
  site (texas-drilling.com); the city's own ordinance chapter/number was
  **not** located this session. Treat as unverified until pulled directly.
- **Grapevine** — Code Ch. 12 (Health & Sanitation), Art. VII "Oil and Gas
  Well Drilling and Regulation," § 12-143, via Municode; requires a Special
  Use Permit (application PDF captured).
- **Keller** — Gas well regulation lives inside the Unified Development Code,
  Article Twelve, per a Granicus-hosted PDF; current Municode section numbers
  not cross-checked.
- **Mansfield** (well verified) — Ch. 114 "Gas Well Drilling and Production"
  (permit requirements, compressors, seismic surveys, road-repair agreements,
  insurance/security, periodic reports) cross-referenced with Ch. 155 Zoning
  § 155.102, requiring a Specific Use Permit with a 90–120 day zoning
  timeline.
- **Flower Mound** — Appendix B Art. III "Gas" and Ch. 34 Art. VIII (Oil and
  Gas Pipelines/Storage); original 2003 ordinance, rewritten 2011; the 2011
  version's water-well sampling requirement (within 1,500 ft of a gas well,
  pre/post-drilling) and $2,000/day penalty are among the most stringent
  surface provisions found in this pass and were reportedly used as a
  template by other North Texas cities.

**Not reached / no distinct ordinance confirmed:** none of the 9 target
cities were skipped, but Denton, Southlake, Colleyville, and Keller all rest
on secondary sources for their numeric specifics (setback distances, exact
current section numbers) rather than a direct pull of the current code text
— flagged `unverified` or `probable` accordingly in the YAML.

## 2. DFW/Barnett counties

Tarrant, Denton, Johnson, Parker, Hood, and Ellis all have the expected
Texas-county authority bundle: subdivision/plat regulations, county road
ROW/utility permits, and (Tarrant, Hood, Ellis) an explicit floodplain
administrator/permit process. Wise County's OSSF/permit forms page was found
but its subdivision/road-use-agreement specifics were not. None of these
counties publish an oil-and-gas-specific ordinance — consistent with Texas
law (counties have no zoning and no O&G regulatory authority; RRC is
exclusive). Tarrant County's subdivision regs explicitly reference gas well
site requirements to be shown on plats, which is the one county-level
document in this batch that names oil & gas directly.

## 3. Eagle Ford counties/cities

Direct oil-and-gas-specific county ordinances were **not found** for Karnes,
DeWitt, La Salle, Dimmit, Webb, Atascosa, McMullen, Live Oak, Gonzales, Frio,
Zavala, or Wilson counties, or for Cotulla, Pearsall, Kenedy, Karnes City,
Carrizo Springs, Cuero, or Beeville — consistent with the Texas legal reality
that counties can't regulate O&G operations, only roads/platting/floodplain/
OSSF, and small Eagle Ford towns generally don't publish standalone O&G
ordinances online. What **is** well documented and captured as its own
record is the Eagle Ford heavy-truck **county road damage** fight: La Salle
County's lawsuit against TxDOT over Energy Sector Road grant funding
allocation (lost at trial court, 2014) and Dimmit County's separate suit
against 21 Eagle Ford operators over road damage — both are real,
citable regulatory-adjacent history even though they aren't "permits." Laredo
(Webb County) has confirmed Municode chapters for its fuel gas code and
streets/ROW rules. Recommend a follow-up pass specifically searching each
remaining county's own domain (`co.<name>.tx.us`) for "road use agreement"
or "special road use permit" language, which several Eagle Ford counties are
known (anecdotally) to have adopted during the 2010–2014 boom but which did
not surface in general web search this session.

## 4. Gulf Coast special districts — navigation, port, and drainage

This was the highest-value, most likely-to-be-missed part of the brief, and
the pass found concrete permitting mechanics for most of the named entities:

- **Port of Houston Authority** — pipeline crossings of PHA property/Houston
  Ship Channel ROW go through a Channel Infrastructure/Real Property
  "pipeline license," typically a 30-year term; an example fee ($16,684 for
  a 10-year initial term on a 2-pipe rack) came from 2024 Port Commission
  minutes — fee scales with pipe count/size, not a flat schedule.
- **Port of Corpus Christi Authority** — pipeline easements/leases approved
  by the Port Commission (Bluewater Texas Terminal is the confirmed 2020
  example); a "Pipeline License Agreement Application" PDF exists but is
  hosted by the **City** of Corpus Christi, not the Port Authority directly
  — worth confirming which entity is the actual counterparty before use.
- **Port of Beaumont Navigation District** and **Calhoun Port Authority** —
  existence, general channel/ROW authority, and USACE Galveston District
  coordination confirmed; neither entity's own crossing-permit application
  page was located this session (both records are `unverified`).
- **Port Freeport / Brazos River Harbor Navigation District** — confirmed
  that "Port Freeport" is the current operating name of the Brazos River
  Harbor Navigation District of Brazoria County named in the task brief;
  the port's own permitting pages were not retrieved (record is
  `unverified`, landing_url is the confirmatory background source actually
  seen, not the port's own site).
- **Harris County Flood Control District** — real, well-documented
  regulatory mechanism: pipeline crossings of HCFCD ROW/channels require a
  bond (corporate surety or personal bond with two sureties) per crossing or
  per mile/part-mile of parallel run, reviewed via Harris County Engineering
  jointly with HCFCD and potentially USACE.
- **Harris County Engineering** — separate general ROW/utility "County
  Approval Certificate" process (E-Permits online system) confirmed with
  phone contact (713-274-3920).
- **Jefferson County Drainage District No. 6** (Beaumont) — has a published
  Pipeline-Utility Permit Application (dd6.org); District No. 7 (Port
  Arthur/Nederland/Groves area) could **not** be independently located this
  session — flagged unverified, existence only inferred from the DD6
  pattern and general county structure.
- **Jefferson County Engineering** — has its own separate "Pipeline Permit
  Policy" document (2020 rev.) distinct from DD6/DD7, confirmed with a phone
  contact (409-835-8584).
- **Brazoria Drainage District No. 4** — confirmed utility/pipeline crossing
  permit application exists (bdd4.org/permits/); exact fee/turnaround not
  captured.

## 5. GLO coastal triggers

Confirmed and citable this session (not just carried over from the prior
agent's unverified notes):
- Texas GLO's Coastal Management Program (CMP) requires **federal
  consistency review** (31 TAC Ch. 26, e.g. § 501.24 for submerged-land
  waterfront structures) for federal actions — including USACE Section
  10/404 permits — affecting the statutory Texas coastal zone; a live
  example consistency-review public notice (Targa Downstream LLC) and the
  USACE Galveston District's own CMP consistency certification form were
  both located.
- GLO issues **Miscellaneous Easements** for pipelines and other ROW uses on
  state-owned coastal submerged lands and uplands — this is the mechanism
  for any line crossing bay bottoms/tidal wetlands, separate from any
  navigation-district or USACE approval.

## 6. East Texas / Haynesville — partial coverage only

Budget ran out before this region could get the same depth as DFW/Gulf.
**Longview** (Gregg County) is well documented: a City Engineer-issued
"pipeline license" for private pipelines in public ROW, currently $1/linear
foot/year, distinct from a franchise agreement. Panola, Harrison, Rusk,
Nacogdoches, Shelby, and Smith counties, and Carthage, Marshall, Henderson,
Kilgore, and Tyler cities, were **not** reached with dedicated searches this
session — only a placeholder Panola County record (explicitly unverified)
was added to mark the gap. **This is the top follow-up priority** for the
next research pass, given Panola/Harrison/Rusk sit squarely in the
Haynesville play.

## 7. What could not be verified / needs a follow-up pass

- Denton's current numeric setbacks (conflicting secondary-source figures);
  Southlake's and Colleyville's exact current ordinance chapter/section
  numbers; Keller's UDC article/section numbers — all need a direct
  Municode/AmLegal pull rather than secondary sources or news coverage.
- Port of Beaumont Navigation District's and Calhoun Port Authority's own
  crossing-permit application forms/fees.
- Jefferson County Drainage District No. 7's own permitting page/contact
  (existence assumed by structural analogy to DD6, not confirmed).
- Port Freeport / Brazos River Harbor Navigation District's own site and
  permitting process (only background confirmation of its identity was
  retrieved).
- All of East Texas/Haynesville beyond Longview: Panola, Harrison, Rusk,
  Nacogdoches, Shelby, Gregg (county-level), Smith counties and
  Carthage/Marshall/Henderson/Kilgore/Tyler cities.
- Remaining Eagle Ford counties/cities beyond Webb/Laredo and the road-damage
  litigation context (DeWitt, La Salle's own permitting page, Dimmit,
  Atascosa, McMullen, Live Oak, Gonzales, Frio, Zavala, Wilson, and all
  smaller Eagle Ford cities).
- Remaining Gulf Coast counties not reached: Victoria, Refugio, Matagorda
  (only FEMA disaster-designation context found, no county permitting page).
- TWIA / coastal construction wind-loading requirements (flagged by the
  prior agent as a candidate record; not researched this session at all).
