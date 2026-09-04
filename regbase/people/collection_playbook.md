# Collection Playbook — People Layer

A repeatable procedure for an agent to build or refresh the person records
for **one jurisdiction/body** (e.g. "Weld County BOCC," "ECMC," "Fort Worth
gas well inspection"). Follow it top to bottom. Every step that produces a
fact must end with a URL pasted verbatim from the tool result that produced
it — never typed from memory, never reconstructed by pattern-matching a
domain name.

Read `regbase/people/README.md` first. Everything below is bounded by its
scope and prohibited-fields rules — if a step would turn up a home address,
personal phone, family info, health/religion, non-public financial data, or
anything from a personal social account, stop, discard it, and move on.

## 0. Hard rule

If you cannot open/confirm a fact against a public source this run, do not
write it in. Leave `full_name` (and any other unconfirmed field) out of the
record, set `confidence: unverified`, and add a one-line note in
`review_source_urls` pointing to whatever you *did* find (even a "could not
confirm current roster" search result page is worth citing so the next run
knows what was tried). A wrong name in this system is worse than a blank
one.

## 1. Find the body's official roster page first

Before anything else, find the agency/body's own "About/Commissioners/Board
Members/Staff Directory" page — this is the only source that gets a name
`confidence: verified` on its own.

Query patterns:
- `"<agency name>" commissioners current members site:.gov`
- `"<county name> county" "board of county commissioners" official site`
- `"<agency name>" staff directory OR leadership OR "org chart"`
- `"<agency name>" director appointed 2026`

If the official page can't be found or won't load, fall back to a recent,
dated news article naming the title-holder and mark the record
`confidence: probable`, citing the article URL. Never promote to `verified`
without independently finding the agency's own page in a later pass.

## 2. Find where agendas, minutes, and packets live

Identify the meeting-management platform the body uses — this determines
the query pattern for steps 3-5. Common platforms by name, and how to spot
them:

| Platform | Typical URL/markers | Search pattern |
|---|---|---|
| **Granicus** | `*.granicus.com`, "Legislative Management", agenda pages with a Granicus footer | `"<body name>" agenda granicus` |
| **Legistar** | `*.legistar.com`, `Calendar.aspx`, `LegislationDetail.aspx` | `"<body name>" legistar agenda` |
| **NovusAgenda** | `*.novusagenda.com`, `AgendaPublic` | `"<body name>" novusagenda` |
| **BoardDocs** | `*.boarddocs.com`, `/Board.nsf` | `"<body name>" boarddocs` |
| **CivicPlus / CivicClerk** | `*.civicplus.com`, `*.civicclerk.com`, "Agenda Center" | `"<body name>" "agenda center" civicplus` |
| **Municode Meetings** | `meetings.municode.com` | `"<body name>" municode meetings` |
| **County/city clerk records** | often a plain `.gov` "Clerk and Recorder" or "County Clerk" page with a records-search tool | `"<county name>" clerk and recorder meeting minutes search` |
| **YouTube channel archive** | body's name as a channel, video titles date-stamped meeting recordings | `"<body name>" youtube channel meeting recording` |

Once found, note the platform in the collection run's working notes (not in
the person record itself) — it lets the next refresh start at step 2
directly.

## 3. Find recent approvals/denials for the relevant matter types

- Distinguish **consent agenda** items (routine, usually unanimous,
  low-signal for "decision pattern") from **regular/public-hearing agenda**
  items (contested or discretionary, high-signal).
- Pull the **staff report** for each matter when available — it usually
  states the recommended conditions of approval, which is the best source
  for `decision_patterns.common_conditions_imposed` and
  `process_notes.known_completeness_pitfalls`.
- Query patterns:
  - `"<body name>" agenda "special use permit" OR "conditional use" pipeline OR "compressor station" OR "gas processing"`
  - `"<body name>" minutes approved "tank battery" OR "SWD" OR "produced water"`
  - `"<body name>" staff report conditions of approval midstream`
  - `"<county name>" planning commission denied permit oil gas 2024 OR 2025 OR 2026`
- Record each individual member's vote (not just the outcome) when the
  minutes name votes by member — that is what populates `voting_record`.
  If minutes only record the outcome and not per-member votes, do not
  fabricate a per-member vote; record the outcome at the body level and
  leave that member's `voting_record` entries out for that matter.

## 4. Compute an observed approval rate honestly

`decision_patterns.approval_rate_observed` must be reproducible from
`evidence_urls`. To compute it:

1. Fix a **date window** (e.g. the last 24 months, or since the person's
   term began, whichever is shorter/more relevant) and state it.
2. Fix the **project-type scope** to the specific `applies_to` categories
   relevant to midstream (e.g. `gas_processing_plant`, `swd_well`,
   `compressor_station`, `midstream_pipeline`) — do not silently fold in
   unrelated matter types (e.g. residential rezonings) just to inflate the
   sample.
3. **Denominator** = every matter of that project-type scope that reached a
   vote/decision by that body in that window, found via step 3 — including
   denials and withdrawals-before-vote if the record shows them as
   effectively decided. Do not cherry-pick only the approvals you found
   first.
4. **Numerator** = the subset the record shows as approved (including
   approved-with-conditions).
5. Write it out explicitly, e.g.:
   `"7/9 (78%) midstream-related matters approved, BOCC regular agenda, Jan 2024-Dec 2025"`
   — never a bare percentage with no denominator or window.
6. If the sample is small (say, under 5 matters), say so explicitly instead
   of implying a stable pattern — e.g. append `"(small sample, n=3)"`.

## 5. Citing

- Every `source_url` field must be the exact URL from the search result or
  page actually opened — copy/paste, never retyped from memory.
- Prefer a deep link to the specific agenda item/minutes/docket page over a
  bare homepage link when the platform supports it (Legistar and Granicus
  both generate stable per-item links).
- `source_type` should reflect what was actually read: `meeting_minutes` for
  approved minutes, `agenda` for a pre-meeting agenda/packet (use when
  minutes aren't posted yet — note it may still change), `vote` for a
  docket/order with a recorded vote, `press` for a news article or agency
  press release, `filing` for a campaign-finance or regulatory filing.

## 6. Marking uncertainty

- A record's `confidence` is the *floor* set by its weakest verified fact —
  if the name is verified but the term dates are only "probable" from a
  news mention, the record can still say `confidence: probable` overall
  with a note, or (preferably) leave `term_end` blank rather than pull the
  whole record's confidence down further than necessary. Use judgment, but
  never round unverified facts up to look more complete.
- If a body's roster appears to have changed (a name search turns up
  someone new) but you can't confirm it's not just an old cached page,
  leave the existing record as `probable` and add both source URLs to
  `review_source_urls` with a note for a human to resolve — do not silently
  overwrite a `verified` name with an unconfirmed one.
- When nothing about a slot can be confirmed at all (agency doesn't publish
  a roster, or search turns up nothing usable), keep the placeholder: fill
  `title`, `body`, `jurisdiction_id`, `state`, `level`, `role_type` (from
  the office's known structure/statute, which is a fact about the office,
  not the person) and leave `full_name` and `official_contact` empty,
  `confidence: unverified`.

## 7. One record per person, one file per jurisdiction batch

Add/update entries directly in `regbase/people/people.seed.yaml` (or a
per-state file if the collection splits by state later) rather than
creating parallel files — keeps `id` collisions visible via review.
