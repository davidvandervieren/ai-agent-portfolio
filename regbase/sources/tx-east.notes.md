# TX-East regulatory source registry — research notes

## 0. Why `tx-east.yaml` has zero records

This task requires live-verified URLs (WebSearch results, transcribed exactly;
no invented/reconstructed URLs; unverifiable items marked `confidence:
unverified` but still sourced from something actually seen). At task start
the session's WebSearch budget was already exhausted (0 of 200 remaining —
confirmed on a retry after the first batch of 4 calls all failed identically).
WebFetch, curl, and wget were explicitly out of scope per the task setup
(proxy-blocked). No other live-research tool was available in this session.

Consequently **no URL was actually seen this run**, and per the standing
"never guess" rule no source records were fabricated. `tx-east.yaml` contains
`sources: []` and a header explaining this. Everything below is general
structural/legal knowledge (not sourced from a lookup this session) intended
to make the follow-up research pass fast — every claim here should be treated
as **unverified** and re-confirmed against a primary source before it is
promoted into the YAML registry.

## 1. DFW cities likely to still have enforceable gas well ordinances post-HB 40

HB 40 (2015) preempts municipal regulation of oil & gas *operations* but
preserves "commercially reasonable" surface-level regulation: setbacks,
fire/emergency response, traffic, noise, lighting, notice/registration, and
reclamation/site restoration — provided the rule doesn't effectively prohibit
operations and doesn't duplicate the state's (RRC's) role as regulator of the
operation itself. Cities that had built out detailed Barnett Shale-era gas
drilling ordinances (chapters typically titled "Gas Well Drilling and
Production," "Oil and Gas Wells," or similar, usually in the code's
Business/License or Health & Safety title) generally kept those ordinances on
the books post-2015 but pared or reinterpreted them to the surface-only scope
HB 40 allows. Cities I'd expect (from general knowledge, unverified) to still
carry the most developed surviving ordinance frameworks:

- **Fort Worth** — historically the most extensive gas well ordinance in the
  US (originally Ch. 15, "Gas Well Drilling and Production," recodified at
  points); permit process, setbacks from occupied structures/schools,
  pipeline routing/franchise requirements, noise/lighting standards,
  gas well review committee. Needs re-verification of current chapter number
  and whether it was formally amended post-HB 40 (likely yes, ~2015-2016).
- **Southlake, Colleyville, Grapevine, Keller** — Tarrant County suburbs with
  their own detailed drilling ordinances (setbacks often larger than Fort
  Worth's, notice/hearing requirements) layered on top of extensive Barnett
  Shale build-out; strong candidates for still-active surface-only chapters.
- **Arlington** — sizable ordinance framework (gas well permit, gas well
  review process) given dense in-city drilling.
- **Denton** — notable post-hoc history: Denton's 2014 voter-approved
  fracking *ban* was the direct trigger for HB 40's passage and was
  invalidated by the statute; Denton's current ordinance is very likely a
  narrowed, surface-only successor (setbacks, notice, road use) — this is
  a high-value, well-documented case study to verify first.
- **Mansfield, Grand Prairie, Flower Mound, Lewisville, Azle, Saginaw,
  Burleson, Cleburne, Weatherford** — mid-tier Barnett cities that generally
  adopted at least a baseline gas well permit ordinance during the 2005-2012
  boom; likely retained a surface-only version.
- Smaller Wise/Denton-county boom towns (Bridgeport, Decatur, Rhome,
  Boyd) and DFW inner-suburbs without significant in-city pad density
  (Bedford, Euless, Hurst, Haltom City, North Richland Hills, Roanoke,
  Argyle, Justin, Krum, Ponder, Alvarado, Midlothian, Waxahachie, Mineral
  Wells, Granbury) are unverified — some may have only a thin
  registration/ROW-permit ordinance rather than a full drilling code.

**Recommended verification order:** Fort Worth → Denton → Southlake →
Arlington → Colleyville/Grapevine/Keller → the remaining DFW list, using each
city's Municode/American Legal/eCode360 landing page plus a search for
"[city] gas well ordinance" / "[city] oil and gas drilling ordinance."

## 2. Navigation / drainage district crossing-permit landscape (Gulf Coast)

Structural picture (unverified specifics, verify each entity's actual
permit/crossing-agreement requirements and forms):

- **Navigation districts / port authorities** typically hold their own
  submerged-land/channel-easement and crossing-permit authority independent
  of GLO where pipelines or utility lines cross district-owned channels,
  turning basins, or ROW — Port of Houston Authority, Port of Corpus Christi
  Authority, Port of Beaumont, Port Arthur Navigation District, Port of
  Victoria, Calhoun Port Authority, Brazos River Harbor Navigation District
  (Freeport/Brazoria), Orange County Navigation & Port District, Matagorda
  County Navigation District. Expect each to require a crossing/easement
  agreement plus engineering review for any pipeline under/over their
  channels or ROW, separate from USACE Section 10/404 review.
- **Drainage districts / flood control districts** require crossing permits
  for any produced-water or midstream line crossing a district-maintained
  channel, bayou, or levee: Harris County Flood Control District (largest,
  most active — permit for any work in/across HCFCD-maintained channels),
  Brazoria County Drainage District #4, Jefferson County Drainage District
  6 and 7, plus county-level engineering ROW permits (Harris County
  Engineering Department ROW permit) for any county road/ditch crossing.
- **MUDs** (Municipal Utility Districts) in Harris/Brazoria/Fort Bend can
  hold utility-easement authority over their own infrastructure corridors
  where a pipeline crosses MUD-owned utility ROW; this is much more
  fragmented (hundreds of individual MUDs) and would need to be scoped
  per-project rather than exhaustively cataloged.
- **Levee improvement districts** along the Brazos/San Jacinto and Gulf
  Coast add a further crossing-permit layer wherever a levee or its
  easement is crossed.

## 3. Coastal (GLO / CMP) triggers

Structural picture (unverified specifics):

- Texas GLO administers the Coastal Management Program (CMP) and requires
  **consistency review** for state/federal permitted activities within the
  statutorily defined **coastal zone** (the 18 CMP-designated coastal
  counties, which include essentially every Gulf Coast county in this
  agent's scope — Harris, Brazoria, Galveston, Chambers, Jefferson, Orange,
  Matagorda, Victoria [partial], Refugio, Calhoun, Nueces, San Patricio,
  Jackson [partial], Aransas, Kleberg, plus others further south/north).
  Any USACE Section 404/10 permit, any activity in submerged/state-owned
  land (bay bottoms, tidally influenced wetlands), and any activity
  requiring a state agency permit within the coastal zone likely triggers
  CMP consistency review by GLO / the Coastal Coordination Advisory
  Committee.
- **GLO coastal easements** are specifically required for any pipeline or
  facility crossing state-owned submerged land (bay/estuary bottoms,
  beaches) — a produced-water or midstream line crossing Galveston Bay,
  Sabine Lake, Matagorda Bay, Corpus Christi Bay, etc. would need a GLO
  easement in addition to USACE and local navigation-district approval.
- **USACE Galveston District** is the relevant Corps district for the full
  Gulf Coast scope (Galveston Bay, Sabine Lake/Neches-Sabine, Corpus
  Christi Ship Channel, Matagorda/Colorado systems) — Section 10 (navigable
  waters) and Section 404 (wetlands/dredge-fill) both apply to pipeline
  water crossings and any new dock/mooring/temporary workspace in
  jurisdictional waters.
- **Texas Windstorm Insurance Association (TWIA)** requirements and
  associated coastal construction / wind-loading standards apply to
  above-ground structures (compressor stations, tank batteries, gas
  processing plants) sited in the TWIA-designated first-tier coastal
  counties — relevant as a design/insurance-eligibility constraint rather
  than a permit, but worth its own source record once verified.

## 4. Full jurisdiction checklist (not yet researched — queue for next pass)

**Counties — Eagle Ford (25):** Karnes, DeWitt, La Salle, Dimmit, Webb,
Zavala, Frio, Atascosa, McMullen, Live Oak, Gonzales, Lavaca, Wilson, Bee,
Goliad, Duval, Jim Wells, Brooks, Maverick, Medina, Bastrop, Fayette,
Burleson, Lee, Milam.

**Counties — Barnett/DFW (14):** Tarrant, Denton, Wise, Johnson, Parker,
Hood, Ellis, Dallas, Somervell, Erath, Palo Pinto, Jack, Montague, Cooke.

**Counties — East TX/Haynesville (19):** Panola, Harrison, Rusk,
Nacogdoches, Shelby, San Augustine, Gregg, Smith, Upshur, Marion, Cass,
Angelina, Cherokee, Henderson, Anderson, Freestone, Limestone, Leon,
Robertson.

**Counties — Gulf Coast (22):** Harris, Brazoria, Galveston, Chambers,
Jefferson, Orange, Matagorda, Victoria, Refugio, Calhoun, Nueces, San
Patricio, Jackson, Fort Bend, Waller, Wharton, Colorado, Austin, Liberty,
Hardin, Aransas, Kleberg.

**Depth-focus counties (do first):** Tarrant, Denton, Wise, Johnson, Parker,
Karnes, DeWitt, La Salle, Dimmit, Webb, Panola, Harrison, Harris, Brazoria,
Nueces, San Patricio, Jefferson, Chambers.

**Municipalities — DFW (34):** Fort Worth, Arlington, Dallas, Denton,
Mansfield, Grand Prairie, Southlake, Colleyville, Grapevine, Keller, Flower
Mound, Lewisville, Bedford, Euless, Hurst, Haltom City, North Richland
Hills, Burleson, Cleburne, Weatherford, Azle, Saginaw, Roanoke, Argyle,
Justin, Krum, Ponder, Decatur, Bridgeport, Alvarado, Midlothian,
Waxahachie, Mineral Wells, Granbury.

**Municipalities — Eagle Ford (20):** Laredo, Pearsall, Kenedy, Karnes
City, Carrizo Springs, Cotulla, Dilley, Cuero, Yorktown, Three Rivers,
George West, Beeville, Gonzales, Hallettsville, Floresville, Poteet,
Jourdanton, Pleasanton, Eagle Pass, Crystal City.

**Municipalities — East TX (13):** Longview, Carthage, Marshall,
Henderson, Nacogdoches, Center, Kilgore, Tyler, Gladewater, Tatum,
Jefferson, Palestine, Athens.

**Municipalities — Gulf Coast (30):** Houston, Pasadena, Baytown, La
Porte, Deer Park, Texas City, Freeport, Lake Jackson, Angleton, Alvin,
Corpus Christi, Portland, Ingleside, Gregory, Taft, Robstown, Victoria,
Port Lavaca, Beaumont, Port Arthur, Nederland, Groves, Orange, Bay City,
Sugar Land, Katy, Galveston, Seadrift, Point Comfort.

**Gulf-Coast special regimes (own source records):** Texas GLO
coastal easements/CMP consistency review, Texas Coastal Coordination
Advisory Committee; Port of Houston Authority, Port of Corpus Christi
Authority, Port of Beaumont, Port Arthur (navigation district), Port of
Victoria, Calhoun Port Authority, Brazos River Harbor Navigation District,
Orange County Navigation & Port District, Matagorda County Navigation
District; Harris County Flood Control District, Harris County Engineering
ROW permits, Brazoria County Drainage District #4, Jefferson County
Drainage District 6 & 7; TWIA/coastal construction requirements; USACE
Galveston District (Galveston Bay / Sabine Lake).

## 5. What could not be verified (everything)

Every item in Sections 1-4 above is general/trained knowledge, not a result
of a lookup performed this session, and must be treated as **unverified**:
county/city government domain names, Municode/eCode360/American Legal
platform assignments, specific ordinance chapter numbers, GIS REST endpoints,
permit form URLs, and even whether some smaller cities have a gas well
ordinance at all. Nothing in `tx-east.yaml` reflects the above because none
of it was confirmed against a live source. Recommended immediate next step:
re-run this research task once WebSearch (or another live-lookup tool) is
available, working the depth-focus list first, then the DFW ordinance
cities, then the Gulf Coast special districts, then the remaining county/
municipality long tail.
