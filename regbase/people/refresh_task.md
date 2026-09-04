# Refresh Task — People Layer

Spec/prompt for a periodic agent that keeps `regbase/people/people.seed.yaml`
(and any per-state files it later splits into) current. Run this task's
instructions through `regbase/people/collection_playbook.md` for the actual
step-by-step research procedure; this file defines *when* to run it, *what*
to re-check, and *how to diff* the result against the existing record.

## Immediate first run (before any cadence applies)

`people.seed.yaml` currently ships as an all-`unverified` structural
scaffold (see `README.md`, "Status of the current seed set") because
WebSearch was unavailable when it was built. **The first refresh run's job
is to actually populate it** — for every record, run the playbook's steps
1-6 and either promote it to `verified`/`probable` with real data, or leave
it `unverified` but now with at least one `review_source_urls` entry
showing what was searched and why it couldn't be confirmed. Treat this
first pass as the priority backlog, ordered by the state groupings already
in the file (CO, WY, NM, UT, TX).

## What to re-check, and how often

| Trigger | What changed | Re-check cadence |
|---|---|---|
| **General election** | Elected seats (BOCC/Commissioners Court/County Judge, City Council, RRC Commissioner) | Within 4 weeks of the relevant state's general election certification, every even year at minimum (odd-year cycles exist for some municipal seats — check each jurisdiction's own calendar) |
| **Gubernatorial appointment cycle** | Board/commission appointees (ECMC, WOGCC, NM OCC, Utah Board of Oil Gas and Mining, TCEQ, Wyoming Industrial Siting Council) | Quarterly spot-check for expired/expiring terms (compare `term_end` to today), plus an immediate check whenever a new governor takes office (appointees are frequently replaced) |
| **Staff turnover** | career_staff roles (directors, division chiefs, planning directors, floodplain administrators, gas well inspectors) | Quarterly roster re-check against the agency's own staff directory page (these turn over on no fixed schedule and are the most likely fields to silently go stale) |
| **New meeting cycle** | `voting_record`, `public_positions`, `decision_patterns` | Monthly or quarterly per active jurisdiction, pulling any new agenda items since the last `last_reviewed` date, per playbook step 3 |
| **Recomputed approval rate** | `decision_patterns.approval_rate_observed` | Recompute in full (not incrementally patched) at each `decision_patterns` refresh, per playbook step 4, using the same window/scope rules |
| **Campaign finance filing deadline** | `campaign_finance` (elected only) | After each filing deadline in the relevant state's election-finance calendar |

If a jurisdiction has had zero activity relevant to the above since its
`last_reviewed` date, still bump `last_reviewed` after confirming that
(don't leave a stale date implying it wasn't checked), and note the
confirming URL in `review_source_urls`.

## How to diff

1. **Never overwrite in place without comparison.** Before editing a
   record, read its current `confidence`, `full_name`, `term_end`, and
   `review_source_urls`.
2. **Name/incumbency change:**
   - If the new search result names someone different from the existing
     `full_name`, do not just replace it. Confirm on the agency's own
     roster page (not just a news mention) before changing a `verified`
     record — a single conflicting source should first move the record to
     `probable` with both URLs cited, not silently overwrite.
   - If the existing record was `full_name`-omitted/`unverified` and this
     run finds a confirmable name, fill it in and set `confidence`
     accordingly (`verified` only if confirmed on the agency's own page).
3. **Term dates:** update `term_start`/`term_end`/`next_election` when a
   more precise or newly-elapsed date is found; do not delete a previously
   verified date just because a new source doesn't repeat it.
4. **Append, don't replace, evidence arrays:** `public_positions`,
   `voting_record`, and `decision_patterns.evidence_urls` should grow by
   appending newly found items with their own dates — do not delete prior
   entries unless they're found to be wrong (e.g. sourced from a page that
   turns out to describe a different person/body).
5. **Log every refresh** by updating `last_reviewed` to the run date and
   appending (not replacing) the URLs actually opened this run into
   `review_source_urls`.
6. **Flag conflicts for a human** rather than resolving them silently
   whenever: two credible sources disagree on the current title-holder, a
   `verified` record would be downgraded, or a role/body appears to have
   been restructured (e.g. a county changing from a commission to a
   council form of government, an agency merger or renaming — Colorado's
   COGCC-to-ECMC rename in 2023 is exactly this kind of change). Leave the
   existing record intact, add a note in `review_source_urls` with both
   conflicting sources, and surface it in the refresh run's summary output
   for a human to resolve.

## Output of a refresh run

A refresh run should produce, alongside the updated YAML:
- A short summary: records checked, records promoted in confidence,
  records changed (name/term/body), records flagged for human resolution,
  records still `unverified` after this pass and why.
- Nothing else is written back into the person records themselves beyond
  what `person.schema.json` allows — a refresh run is bound by the same
  scope/prohibited-fields rules as the initial collection
  (`regbase/people/README.md`).
