# Refresh Log — People Layer

**Run date:** 2026-09-04
**Run by:** research agent, WebSearch-only (WebFetch/curl/wget blocked), shared
session budget of ~200 searches across 5 concurrent agents; this run was
budgeted to ~35 searches and used 28.

## Result summary

- Total person records in `people.seed.yaml`: **91** (up from the 70 seed
  placeholders — several single-seat placeholders representing a
  multi-member body were split into one record per confirmed person, per
  `collection_playbook.md` §7, with a companion "-other-seats" placeholder
  added for any seats still unconfirmed on that body).
- `confidence: verified` — **18** records (named directly from the
  agency's own official page, an official org chart/PDF dated within the
  current cycle, or an official press release from the appointing
  authority).
- `confidence: probable` — **15** records (named via a credible but
  secondary source — dated news reporting, a partial/ambiguous official
  page, or an official source that did not itself carry a name so a
  secondary source filled it in).
- `confidence: unverified` — **59** records remain placeholders: `title`,
  `body`, `jurisdiction_id`, `level`, `role_type` filled in from known
  office structure; `full_name` intentionally omitted because no live
  source could be confirmed this pass, or because budget ran out before
  that seat's turn came up in the priority order.

Every added `full_name` carries `review_source_urls` copied verbatim from
the WebSearch results actually opened. No name, title, term date, or URL
was invented or reconstructed from memory.

## What got verified, by priority tier

1. **CO ECMC** — Director confirmed (Jennifer Walker Graf, appointed July
   2026 after Julie Murphy's departure — probable, dnr.colorado.gov +
   Denver Gazette). 3 of an assumed ~7 commissioner seats confirmed
   (Jeffery Robbins — Chair, Trisha Oeth, John Messner — verified via
   ecmc.colorado.gov press release, terms to 2028-07-01). Remaining
   commissioner seats left as an "-other-seats" placeholder.
2. **TX RRC** — All three elected Commissioners confirmed (Jim Wright —
   Chairman, Christi Craddick, Wayne Christian — probable, via
   rrc.texas.gov/about-us/commissioners/). Executive Director Wei Wang
   confirmed (probable — sourced to the 2018 RRC appointment press
   release and a biography page; a human should re-confirm he is still
   in the role in 2026, since the strongest cite is the original
   appointment announcement).
3. **NM OCD/OCC** — OCD Director Albert C.S. Chang confirmed (verified —
   also serves ex officio as OCC Chairman per EMNRD's own 2026 OCC
   meeting-notice PDF). The other 2 of 3 statutory OCC seats (Commissioner
   of Public Lands' designee; EMNRD Secretary's designee) are named
   designees whose current occupants were not found this pass — left
   unverified with the statute cited.
4. **WY WOGCC** — Full 5-member commission confirmed (verified, agency's
   own commission page): Governor Mark Gordon (Chairman, ex officio),
   Stacia Berry (Acting Chair, ex officio), Ranie Lynds (ex officio), Paul
   Geiger, Shane True. Supervisor Tom Kropatsch confirmed (verified).
5. **UT DOGM/Board** — Director Richard "Mick" Thomas confirmed (verified,
   naturalresources.utah.gov). Board of Oil, Gas and Mining: only
   partial — one member (Stephen B. Church) surfaced but the chair and
   full 7-member roster were not confirmed this pass; **left as the
   original placeholder, not modified**, since no single name could
   anchor a reliable record.
6. **TCEQ** — All three Commissioners confirmed (verified, official
   org-chart PDF dated June 2026): Brooke T. Paup (Chairwoman), Catarina
   R. Gonzales, Tonya R. Miller (term to 2031-08-31). Executive Director
   Kelly Keel confirmed (verified, tceq.texas.gov directory, current as
   of March 2026).
7. **CO counties** — Weld County: Commissioner Mike Freeman (Chair,
   District 1) and Planning Services Director David Eisenbraun both
   confirmed (verified, weld.gov). Garfield County: Commissioner Perry
   Will confirmed (probable); the search also surfaced pages for John
   Martin, Mike Samson, and Tom Jankovsky that could **not** be confirmed
   as current vs. stale/cached — flagged for human resolution rather than
   guessed. Adams County: all 5 commissioners named (probable — official
   adcogov.org roster page, but district/seat assignment per person not
   confirmed). Broomfield: Mayor Guyleen Castriotta confirmed (verified).
   Garfield's Community Development Director and Adams'/Broomfield's
   other seats remain unverified — not reached this pass.
8. **Permian counties** — County Judges confirmed for Midland (Terry
   Johnson, probable), Ector (Dustin Fawcett, probable), and Reeves (Leo
   Hung, probable). **No floodplain administrators were confirmed by
   name for any county** — these offices' current staff did not surface
   in the searches run; all floodplain administrator records remain
   unverified placeholders. Karnes, Tarrant, Denton, and Harris County
   judges/floodplain administrators were not reached this pass.
9. **Fort Worth / Denton gas well inspectors** — Titles and departments
   corrected and confirmed (not just guessed at, as the prior pass
   flagged): Fort Worth's role is titled "Gas Well Inspector" under the
   **Development Services Department** (confirmed via the City's own job
   description PDF). Denton's role sits in a dedicated **Gas Well
   Inspections Division**, and the Development Code's actual
   condition-imposing authority is titled the **"Gas Well Administrator"**
   (confirmed via cityofdenton.com and the Denton Development Code on
   Municode). No individual incumbent name was found for either seat —
   both remain unverified for `full_name`, but the title/department
   fields are now real rather than placeholders.

## Not reached this pass (budget exhausted before their turn)

- CO: Garfield Community Development Director; Boulder and La Plata
  County commissioners (outside the task's named priority list but
  present in the seed); CDPHE APCD Director.
- WY: Industrial Siting Council; county-level (Campbell, Converse,
  Laramie, Sublette) commissioners/planning directors; WDEQ AQD
  Administrator.
- NM: NMED Air Quality Bureau Chief; Lea, Eddy, San Juan, Rio Arriba,
  Sandoval County commissioners/planning directors.
- UT: DAQ Director; Uintah, Duchesne, Carbon, Grand, San Juan (UT) County
  commissioners/planning directors; full UT Board of Oil, Gas and Mining
  roster.
- TX: RRC Pipeline Safety Director (title/division itself still needs
  verification); all floodplain administrators (Midland, Ector, Reeves,
  Karnes, Tarrant, Denton, Harris); Karnes, Tarrant, Denton, Harris County
  Judges.

## Top 5 things a human should confirm first

1. **TX RRC Executive Director (Wei Wang)** — the strongest source found
   is the original 2018 appointment announcement; confirm he is still in
   the role in 2026 directly on rrc.texas.gov before relying on this for
   anything time-sensitive.
2. **Garfield County (CO) commissioner roster conflict** — search
   surfaced individual bio pages for John Martin, Mike Samson, and Tom
   Jankovsky alongside separate, more recent evidence that Perry Will
   holds the District 2 seat as of January 2025. These may be stale
   cached pages, but a human should open
   `https://www.garfield-county.com/board-commissioners/` directly to
   resolve the current 3-member roster rather than trusting either set of
   URLs in this file.
3. **Floodplain administrators (all TX counties)** — the task brief calls
   these out as "the actual gatekeepers for midstream work in Texas
   counties," and none were confirmed by name this pass for Midland,
   Ector, or Reeves. These are worth a dedicated follow-up pass, likely
   via each county's Engineering/Public Works department page rather than
   the Commissioners Court page.
4. **UT Board of Oil, Gas and Mining full roster and chair** — only one
   member (Stephen B. Church) surfaced; the record was intentionally left
   as the original generic placeholder rather than anchored on one
   possibly-non-representative name. Needs a direct pull of
   `https://ogm.utah.gov/board-members/`.
5. **Adams County (CO) commissioner-to-district mapping** — all 5 names
   were confirmed from the official roster page, but which of the 5
   holds which district seat (relevant for `title` and any future
   `portfolio`/ward-based analysis) was not confirmed and is marked
   "district to verify" in each record.

## Ethics compliance note

No home address, personal phone/email, family information, health,
religion, or non-public financial data was collected or stored at any
point. `official_contact` fields populated in this pass contain only
agency-published office URLs/phone numbers. No `voting_record`,
`public_positions`, or `decision_patterns.approval_rate_observed` entries
were added — none could be built from a real, specific docket/vote source
within this pass's budget, and per the task instructions an invented rate
would be worse than none.
