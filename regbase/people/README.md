# RegBase — People Layer (Public Officials & Staff Profiles)

This directory holds profiles of the named public officials and career staff
who make or influence permitting decisions for oil & gas midstream projects
(pipelines, gathering/produced-water lines, compressor stations, gas
processing plants, SWD wells, tank batteries, associated access/utility
corridors) across Colorado, Wyoming, New Mexico, Utah, and Texas.

It exists so an analyst or agent can answer: *"Who decides this permit, what
body do they sit on, and what does their public record show about how they
tend to handle matters like this one?"* — not to build dossiers on
individuals.

## Scope: what may be collected

Only information that is **public, professional, and role-related**:

- Official title, agency/body, and term dates.
- Public voting record and published decisions (votes, orders, dockets).
- Public meeting statements — minutes, agendas, staff reports, testimony.
- Official contact information **published by the agency itself** (office
  phone, office email, agency web page, office mailing address).
- Public campaign-finance filings, for **elected** officials only, and only
  facts stated in the filing itself.

Every fact must trace to a citable public source URL. If it can't be traced,
it does not go in the record.

## Prohibited: what must never be collected or stored

The following are never collected, and must never appear in any record in
this layer, regardless of how it was obtained or how relevant it might seem:

- Home address or personal phone/email.
- Family members or personal relationships.
- Health, religion, or other personal/protected characteristics.
- Non-public financial data (anything beyond what a public campaign-finance
  filing itself discloses).
- Anything scraped or inferred from a **personal** (non-official-capacity)
  social media account.

`regbase/schemas/person.schema.json` encodes this as a hard schema
constraint (`additionalProperties: false` plus a `prohibited_fields`
description) so a field for any of the above cannot be silently added later.
If a collection run turns up one of these by accident, discard it — do not
store it "just in case," and do not note that it exists.

## Prohibited uses

This data exists to understand **institutional decision-making patterns and
process** — how a body typically reviews a matter, what staff usually asks
for, how long review tends to take, what conditions tend to get attached —
so that applicants and analysts can prepare complete, responsive submittals
and anticipate process. It must never be used:

- To contact, pressure, or attempt to improperly influence a public official
  outside the normal public process (the public hearing record, published
  comment periods, and an agency's own published contact channels are the
  normal process; back-channel contact prompted by this data is not).
- To build a profile of an official for any purpose other than understanding
  their public decision-making record on matters within this system's scope.
- As a substitute for legal or lobbying-compliance advice.

**Consult counsel before any outreach to a public official informed by this
data.** Colorado, Wyoming, New Mexico, Utah, and Texas each have their own
lobbyist-registration thresholds and gift/hospitality rules, and some county
and municipal bodies layer local ethics rules on top of state law. Whether a
given contact or gift triggers a registration or disclosure obligation is a
legal question, not a data question, and this system does not answer it.

## Data model

- `regbase/schemas/person.schema.json` — the JSON Schema for one person
  record. `jurisdiction_id` is a foreign key to the `id` of a record in
  `regbase/schemas/source.schema.json` (the regulatory-source layer),
  using the same slug convention (e.g. `co-weld-county-landuse`). During
  this seed phase the sources layer had not yet been populated for most of
  these jurisdictions, so several `jurisdiction_id` values are provisional
  slugs following that convention, meant to be resolved once
  `regbase/sources/` is built out — they are identifiers, not verified
  facts about a person.
- `regbase/people/people.seed.yaml` — the seed set of person records
  (see status note below).
- `regbase/people/collection_playbook.md` — the repeatable procedure an
  agent follows to build or refresh one jurisdiction's profiles, including
  exact search-query patterns and how to compute an honest observed
  approval rate.
- `regbase/people/refresh_task.md` — the spec for a periodic refresh agent
  that keeps this layer current as elections, appointments, and staff
  turnover happen.

## Confidence levels

- **verified** — current role/name confirmed directly on the agency's own
  official page or a primary filing, checked within the current review
  cycle.
- **probable** — confirmed via a credible secondary source (e.g. recent
  news reporting the title) not yet cross-checked against the agency's own
  page.
- **unverified** — a placeholder slot: the body/title/jurisdiction is known,
  but the current person has not been confirmed. `full_name` is omitted
  entirely rather than filled with a guess. This is the required outcome
  whenever a name cannot be confirmed against a live public source — an
  unverified placeholder is correct behavior, not a failure to fix by
  guessing.

## Status of the current seed set

`people.seed.yaml` in this repository was generated in a research
environment where the web-search tool's session budget was already
exhausted before any query could run (0 searches available). Per the
standing rule above ("never guess"), **no name, title incumbency, term
date, vote, or URL in this seed file was verified against a live source in
this pass.** Every record is `confidence: unverified`, `full_name` is
omitted throughout, and no `official_contact.office_url` or other URL field
was populated (fabricating a plausible-looking agency URL is exactly the
kind of guess this system exists to prevent). The seed file's value in this
state is as a **structural scaffold** — the correct set of jurisdictions,
bodies, and titles to fill in — for the next run of the refresh agent
(`refresh_task.md`) once WebSearch is available, not as a populated
directory.
