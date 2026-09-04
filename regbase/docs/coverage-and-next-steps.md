# Coverage and next steps

Status as of the initial build. Read this before trusting the registry for a
live project.

## What is in the registry today

| Scope | Records | State |
| --- | ---: | --- |
| Federal | 37 | Good. PHMSA, FERC, EPA UIC/air, USACE 404, ESA/MBTA, BLM, NEPA, Section 106, PSM/RMP. |
| Colorado | 79 | Best coverage. 11 state agencies, 30 counties, 38 municipalities. |
| Wyoming | 44 | 16 state agencies, all 23 counties, 6 of 34 municipalities. |
| New Mexico | 28 | 19 state/tribal, 8 counties, 2 municipalities. |
| Utah | 18 | 13 state agencies, 1 tribal, 4 counties, 0 municipalities. |
| **Texas** | **3** | **Effectively empty. Only RRC records.** |

Totals: 209 sources, 535 documents, 134 structured permits.

## Why Texas is empty

The research pass runs on `WebSearch`, which is capped at **200 calls per
session** across all agents. Colorado, Wyoming, New Mexico, and Utah consumed
the budget before the two Texas agents ran. They correctly refused to fabricate
~180 county, city, and district records from memory — government and Municode
URLs drift, and a wrong URL in a machine-consumed registry is worse than a
missing one.

Both Texas agents left a full research plan in
`sources/tx-west.notes.md` and `sources/tx-east.notes.md`, including the
jurisdiction checklists and the recommended order.

## To finish the registry

Each of these is a fresh Claude session (the search budget resets per session).
Run them one per session, or in an environment with outbound HTTPS where the
harvester can crawl directly instead of searching.

1. **Texas state agencies** — TCEQ (Ch. 106 PBRs, Ch. 116 NSR, TPDES CGP
   TXR150000, Ch. 213 Edwards Aquifer), GLO, Texas Historical Commission
   Antiquities permits, TxDOT UIR, TPWD, TWDB, groundwater conservation
   districts. Highest value per unit of effort — these apply statewide.
2. **Texas Permian + Panhandle** counties and cities.
3. **Texas Eagle Ford, Barnett/DFW, East Texas, Gulf Coast** — DFW cities have
   the most developed oil & gas ordinances in the country and are worth depth.
   The Gulf Coast adds navigation districts, drainage districts, and GLO coastal
   easements, which are easy to miss and hard to schedule around.
4. **Utah municipalities** (34 listed, 0 done) and the remaining 23 counties.
5. **New Mexico municipalities** (26 listed, 2 done) and 24 remaining counties.
6. **Wyoming municipalities** (28 of 34 remaining).
7. **Colorado** — fill in CDPHE Reg 3/7/61 and GP01/GP02 direct regulation-text
   URLs, and the ~24 municipal records that have a code platform but no
   identified oil & gas chapter.

`python3 regbase/tools/query.py gaps --state TX` reports this from the data
rather than from this document, and stays current as records are added.

## Known open questions carried in the registry

Recorded in the per-state `notes.md` files and flagged `confidence:
unverified` on the affected records:

- **Wyoming Industrial Siting Act threshold** — the statutory base is $96M,
  escalated annually; current-year sources disagree ($226.5M / $231M / $283.1M
  tiers). Confirm with the Industrial Siting Division before scoping a large
  plant.
- **Nationwide Permit 12 status** — the 2021 reissuance was set to expire in
  March 2026 and a new cycle appeared to be underway. Confirm what is in effect.
- **Lesser prairie-chicken ESA status** — listed 2022, vacated by a Texas court
  in 2025, delisted February 2026, with a new status review open. Volatile;
  re-check every time it matters.
- **EG OOOOc state plans** — whether CO/WY/NM/UT/TX have EPA-approved plans
  determines when existing-source methane rules bind.
- **Sandoval County NM oil & gas ordinance** — contested status, unresolved.
- **Arapahoe County CO 1041** — flagged as possible but not confirmed. The
  example Form 1.9 in hand says a consultant told the team it was required, so
  this one matters and should be settled directly with the county.
- **Grand Junction CO code platform** — sources conflict between Code
  Publishing and eCode360.

## People profiles

`people/people.seed.yaml` holds 70 records. All are **unverified placeholder
seats** — title, body, and jurisdiction filled, names deliberately omitted,
because the search budget was gone before any could be confirmed. This is the
intended failure mode: an empty slot the refresh task fills, not a fabricated
roster.

Run `python3 regbase/tools/refresh_people.py --stale-days 0` to generate the
research work queue, then execute it in a session with search budget.

The collection policy in `people/README.md` is binding: public, role-related
information only.

## Harvesting

Nothing has been downloaded yet — `corpus/raw/` and `corpus/text/` are empty
because outbound HTTPS is blocked in the build environment. The registry's 535
document URLs are ready to fetch:

```bash
python3 regbase/tools/harvest.py --dry-run --state CO      # inspect the plan
python3 regbase/tools/harvest.py --state CO --delay 1.5    # fetch
python3 regbase/tools/harvest.py --state CO --crawl --platform municode
```

Crawl the codes state by state rather than all at once, and keep `--delay` at
1.5s or higher. The per-platform crawl patterns in `harvest.py` are written from
each publisher's public URL shapes but have **not** been validated against live
sites; check the page counts in the run summary on the first real pass and tune
the `PLATFORMS` table.
