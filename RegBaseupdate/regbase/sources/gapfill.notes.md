# Gapfill pass — research notes (2026-09-04/07)

Wrote `regbase/sources/gapfill.yaml` (39 new records, 0 schema errors against
`regbase/schemas/source.schema.json`, no id collisions with co/wy/nm/ut/federal/
tx-*.yaml). Research tool was WebSearch only (~38 calls used out of the ~40-call
budget for this pass; WebFetch/curl blocked). `co.yaml`/`wy.yaml`/`nm.yaml`/
`ut.yaml` were NOT edited — all new material lives only in gapfill.yaml per
instructions.

## Priority 1 — Colorado regulation-text URLs: CLOSED

Found direct Secretary-of-State CCR rule-detail pages (the actual regulation
text, not just CDPHE landing pages) for all three named regulations, plus a
Cornell LII mirror for each (useful for pinpoint section citation):

- **Regulation 3** (5 CCR 1001-5, Stationary Source Permitting/APEN):
  `https://www.sos.state.co.us/CCR/DisplayRule.do?action=ruleinfo&ruleId=2337&...`
- **Regulation 7** (5 CCR 1001-9, O&G emissions control):
  `https://www.sos.state.co.us/CCR/DisplayRule.do?action=ruleinfo&ruleId=2341&...`
- **Regulation 61** (5 CCR 1002-61, CDPS discharge permits):
  `https://www.sos.state.co.us/CCR/DisplayRule.do?action=ruleinfo&ruleId=2377&d=`
  plus a direct PDF generator link (versioned, re-verify ruleVersionId before use).

**GP01/GP02**: GP01 is confirmed as the condensate/crude storage tank battery
general permit (fee $2,490.14 per a mid-2025 snippet). GP02's exact scope
(believed to be the glycol dehydrator general permit, by APCD's numbering
pattern) was NOT independently confirmed — flagged unverified. No direct
GP01/GP02 permit-TEXT PDF was found; CDPHE appears to be retiring PDF forms in
favor of an online submission tool, so only the `general-air-permits` index
page is cited. This remains a partial gap.

**CDOT forms — SETTLED, and the task brief's numbers were wrong**: the
correct forms are **CDOT Form 1233** (Utility/Special Use Permit Application —
confirmed directly via `codot.gov/library/forms/cdot1233.pdf/view`) and
**CDOT Form 0137** (State Highway Access Permit Application — confirmed via
`codot.gov/business/permits/accesspermits/forms/cdot0137`). "Form 101" and
"Form 333" do not appear to exist as current CDOT numbers anywhere in search
results across two sessions now — treat those as incorrect and use 1233/0137
going forward.

## Priority 2 — Arapahoe County 1041: ANSWERED — YES, confirmed adopted

Arapahoe County's own Public Works & Development division page is literally
titled **"Land Development Code and 1041 Regulations"**
(`arapahoeco.gov/.../land_development_code_and_regulations/index.php`), and a
direct county-hosted PDF of the regulation text was found:
**"REGULATIONS GOVERNING AREAS AND ACTIVITIES OF STATE INTEREST"**
(`files.arapahoeco.gov/Public%20Works_Development/planning_land%20development/
Regs%20on%20Areas%20Activities%20of%20State%20Interest.pdf`), based on
24-65.1-101 et seq. C.R.S. This settles the open question from
`coverage-and-next-steps.md` and `co.notes.md`: **the consultant who told the
project team a 1041 permit applied in Arapahoe County was correct** — Arapahoe
County does have an adopted 1041 program. One search snippet showed a
document dated December 12, 2006, which may be an early adoption date or an
older amendment; confirm the currently-effective version's date directly
before finalizing a Form 1.9. New record: `co-arapahoe-county-1041-regs`.

## Priority 3 — Utah municipalities: 8 of 12 closed

Closed: **Vernal** (Municode), **Roosevelt** (CodePublishing, Title 17,
mid-code-rewrite), **Naples** (self-hosted Title 17 + a conflicting ecode360
mirror — unresolved which is authoritative), **Helper** (confirmed on
CodePublishing, contrary to a BYU library-guide claim that no online code
exists for it), **Moab** (General Code / moab.municipal.codes, current
through Ord. 26-12, 2026-06-09), **Myton** (American Legal), **Castle Dale**
(only a zoning MAP found, hosted on the Emery County domain, not a Castle
Dale domain — code text not located), **Huntington** (Title 9 was just
entirely replaced by Ordinance 2-2026, passed 2026-03-18 — very recent,
old zoning map is now stale).

**Not closed**: Price City (confirmed to have a "Land Use Management and
Development Code" by name but no hosting platform found — flagged
`unknown`/`unverified`), Ballard (nothing found at all — likely too small
for any online presence), Duchesne City (only a general government
landing page found, no code platform), Green River (only a zoning-contact
phone/email found, no code text or platform). These four remain open gaps.

## Priority 4 — Utah counties: all 5 target counties closed

**Grand County**: Land Use Code on CodePublishing, current through Ord. 687
(2023-11-07); Article 3 confirmed to prohibit commercial injection wells in
the Valley Aquifer impact zone / any sole-source aquifer zone — directly
relevant to SWD siting.
**San Juan County**: replaced prior zoning with a new **Land Use,
Development and Management Ordinance (LUDMO)**, which includes a named
**"San Juan County Energy Zone"** covering oil, gas, potash, uranium, etc. —
the most directly on-point O&G zoning category found anywhere in this Utah
pass. Adoption date and Energy Zone's specific text not independently opened.
**Summit County**: Municode, current through Ord. 1010 (2026-04-22); split
into Snyderville Basin (Title 10, resort-area) and **Eastern Summit County**
(Title 11, rural — more relevant to O&G) development codes.
**Sevier County**: Title 14 Zoning confirmed via a third-party (UDOT) mirror
dated 2021-05-25 — re-verify against the county's current text; two
different county domains (sevier.utah.gov / sevierutah.net) were both
returned, unresolved which is canonical.
**Daggett County**: Title 8 Land Use Regulations (Zoning & Subdivision
Ordinance) confirmed by name; a separate Dutch John Planning District
sub-ordinance also exists. No code-hosting platform URL was found — flagged
unknown/unverified.
Carbon and Emery counties (previously `unverified` with only landing pages)
got a further look: Emery County's zoning maps for Castle Dale and
Huntington were found directly, but Emery's own base zoning ordinance TEXT
(vs. maps) and Carbon County's ordinance text remain unfound.

## Priority 5 — New Mexico municipalities: all 10 target cities closed

**Two high-value finds — dedicated municipal O&G ordinance chapters**:
- **Farmington**: Code of Ordinances **Chapter 19, "Oil and Gas Wells"**
  (Municode), confirmed directly by node URL — the strongest municipal O&G
  ordinance found in this whole NM pass.
- **Aztec**: City Code **Chapter 15, "Oil and Gas Wells"** — a direct,
  currently-effective (2024-04-10) PDF was found and confirmed to require a
  completed application/permitting process before any drilling, plugging, or
  abandonment activity, or preparatory work, within city limits. Chapter 26
  is Aztec's separate zoning chapter.

Other closures: **Hobbs** (Municode, Title 18 Planning & Development),
**Lovington** (American Legal, Title 17 Zoning), **Artesia** (planning dept
page only, no platform confirmed), **Eunice** (Municode, Ch. 102 Zoning /
Ch. 78 Planning), **Bloomfield** (Municode, no O&G-specific chapter
confirmed), **Roswell** (Municode, Appendix A Zoning, 2020 amendment PDF, no
dedicated O&G chapter found — consistent with a prior agent's finding).

**Not closed / thin**: Jal — only a code-enforcement (nuisance/weeds/
abandoned structures) page was found; no zoning title or platform surfaced at
all for this small Lea County city.

## Priority 6 — Wyoming municipalities: 8 of 12 closed

Closed: **Douglas** (Municode, Title 16 Unified Land Development Code Ch. 4
Zoning), **Wright** (American Legal, Title 11 Zoning, current through Ord.
2025-03), **Evansville** (Municode — a node titled roughly "Office of
Mineral and Industrial Production" was spotted but not opened; flagged as a
priority follow-up read), **Buffalo** (self-hosted, Ch. 29 Zoning
Ordinance), **Sheridan** (Municode, Appendix A Zoning — city-level mirror of
the county's confirmed "Mineral and Oil and Gas Extraction" use category not
verified), **Riverton** (ecode360, Title 17, Sec. 17.04.050), **Lander**
(self-hosted — **actively mid-repeal-and-replace** of its Title 4 Zoning
Code via Ordinance 2024-08; treat any citation as unstable until the new
version is confirmed adopted), **Rawlins** (self-hosted, Title 19 Zoning, a
"Dec 2025" version PDF found — appears current, superseding a 2020
amendment).

**Not closed**: Glenrock (only the town's bare landing page found — no code
platform surfaced at all), Mills, Bar Nunn, Worland — not reached this pass
(budget ran out); no entries fabricated for these.

## Priority 7 — Wyoming Industrial Siting Act threshold: ANSWERED

Pulled directly from the Wyoming DEQ's own permitting page
(`https://deq.wyoming.gov/industrial-siting-2/permitting/`, page metadata
indicates last updated September 2024): the disagreement in prior research
was because **there are two tiers, not one number**:

- **$283,166,876 or more** → full **Industrial Siting Permit** required
  (decision body: Wyoming Industrial Siting Council).
- **$226,533,500 to $283,166,876** → only a **Certificate of Insufficient
  Jurisdiction** is required (a lesser determination, not a full permit).

Both the $283.1M and $226.5M figures that earlier research flagged as
conflicting are in fact **both currently correct** — they are the upper and
lower bounds of the two-tier structure, not competing estimates of the same
cutoff. The other numbers seen in earlier research ($231M, $290,444,666)
most likely come from adjacent escalation years, since the statutory base
($96,000,000, per W.S. 35-12-101 et seq.) escalates annually — they are not
necessarily errors, just different vintages. **Caveat**: DEQ's page itself
carries a September 2024 "last updated" signal, so before using either
figure in a live client determination, call the Industrial Siting Division
(307-777-7174) to confirm the number has not escalated again since. New
record: `wy-deq-industrial-siting-threshold-confirmed`.

## What remains open (honest gap list for the next pass)

- CO: GP01/GP02 exact permit-text PDFs (only an index page found); the
  ~24 CO municipalities flagged in `co.notes.md` as code-platform-confirmed-
  but-no-O&G-chapter were not re-visited this pass (out of scope/budget).
- UT: Price City, Ballard, Duchesne City, Green River (municipalities);
  Carbon and Emery counties' actual ordinance TEXT (only maps/landing pages
  found for Emery, nothing further for Carbon this pass).
- NM: Jal (thin); the other 18 of 28 NM municipalities not in this
  priority list remain untouched (Clovis, Portales, Rio Rancho, Santa Fe,
  Albuquerque, Las Cruces, etc. — see nm.notes.md's original list).
- WY: Glenrock, Mills, Bar Nunn, Worland municipalities; the Evansville
  "Office of Mineral and Industrial Production" chapter (spotted, not read);
  the current-year re-verification of the Industrial Siting thresholds.
- Cross-cutting: no new GIS/ArcGIS REST endpoints were found in this pass —
  the search results consistently returned document/text pages rather than
  service endpoints, mirroring the pattern noted in all four prior notes.md
  files.

## Session housekeeping

All 39 records validated cleanly against `regbase/schemas/source.schema.json`
(jsonschema, 0 errors) and have no `id` collisions with the existing
co/wy/nm/ut/federal/tx-*.yaml files (checked programmatically before writing
this note). `last_reviewed` is set to `2026-09-04` per the task's date
convention (matching the other sources.md files' dating), though the actual
research and writing happened in this 2026-09-07 session.
