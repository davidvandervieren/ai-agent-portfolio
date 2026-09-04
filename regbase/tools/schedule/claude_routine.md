# Claude scheduled Routine — weekly RegBase regulatory review

Paste the block below into a Claude scheduled Routine (weekly, e.g. Mondays
09:00 local — after the cron sweep at 06:45 so the reports already exist).

The prompt is deliberately **standalone**: a scheduled Routine fires into a
fresh session with no memory of this conversation, this repository, or what
RegBase is. Do not trim the context paragraphs; they are what make the run
reproducible.

---

## Prompt text (copy everything between the rules)

---

You are performing the weekly regulatory-change review for **RegBase**, a
regulatory corpus covering oil & gas **midstream** permitting (gathering and
transmission pipelines, produced-water lines, compressor stations, gas
processing plants, saltwater disposal / Class II injection wells, tank
batteries, metering, access roads and associated corridors) across **Colorado,
Wyoming, New Mexico, Utah, and Texas**, plus the federal layer.

The repository is checked out in the working directory. Orient yourself first:

- `regbase/sources/*.yaml` — the source registry, one record per jurisdiction
  or agency, validated against `regbase/schemas/source.schema.json`. Fields
  that matter to you: `id`, `state`, `jurisdiction_level`, `county`,
  `municipality`, `name`, `landing_url`, `documents[]`, `update_watch`
  (`check_urls`, `cadence`, `method`), `confidence`
  (`verified`/`probable`/`unverified`), `last_reviewed`.
- `regbase/tools/check_updates.py` — the change detector. Read its module
  docstring before interpreting any output; it explains the normalization
  rules that decide what counts as a change and, importantly, what is
  deliberately suppressed as render noise.
- `regbase/corpus/reports/` — where reports land.
- `regbase/corpus/watch_state.json` — per-URL hash/etag state.

### Do this, in order

**1. Run the checker.**

```bash
python3 regbase/tools/check_updates.py --due --delay 2
```

If it exits non-zero saying outbound HTTPS is blocked, stop and say so plainly
in your summary — do not fabricate results, and do not fall back to guessing
from memory what a rule says. If it succeeds it writes
`regbase/corpus/reports/updates_<today>.md` and `.json`.

If nothing is due (possible early in the cadence cycle), run instead:

```bash
python3 regbase/tools/check_updates.py --delay 2 --limit 200
```

**2. Run the early-warning scan.**

```bash
python3 regbase/tools/watch_agendas.py --days 45 --delay 2
```

This writes `regbase/corpus/reports/agenda_watch_<today>.md` — pending items
on meeting agendas, i.e. changes that have not been adopted yet.

**3. Read the diffs — this is the actual work.**

Open `regbase/corpus/reports/updates_<today>.md` and read every unified diff
under **Changed**. For each one, decide: *does this moved language change what
a midstream project must do, how long it takes, or whether it is allowed?*

Material for this domain:
- setback distances, and what triggers them (occupied structures, water,
  schools, disproportionately impacted communities);
- flowline / gathering-line registration, integrity, testing, abandonment;
- Class II injection and saltwater-disposal permitting;
- 1041 / areas-and-activities-of-state-interest designation and thresholds
  (Colorado especially);
- special-use / conditional-use / USR triggers and thresholds for compressor
  stations, processing plants, tank batteries;
- right-of-way, franchise, and road-use terms;
- application contents, hearing requirements, notice radii, review timelines;
- fee schedules;
- air-quality and water-quality permitting thresholds that bind midstream
  equipment.

Not material: navigation changes, staff-directory edits, news posts, PDF
re-exports with identical text, formatting churn. The report already suppresses
most of this; say so briefly rather than padding the summary with it.

Where a document is flagged `hashed over raw bytes (no extractable text)`,
treat it as *unconfirmed* — open the URL yourself and compare before calling it
a change.

**4. Write a summary**, at the top of your reply, structured as:

- **Material changes** — one bullet each: jurisdiction, document, what
  substantively changed (quote the moved language), and the practical effect
  on midstream permitting. Cite the URL.
- **Pending / early warning** — anything from the agenda scan that would matter
  if adopted, with the meeting date and body.
- **Noise suppressed** — one line with the count.
- **Broken sources** — URLs with 3+ consecutive failures, which usually means
  the agency moved the page.

**5. Update the source records.**

For each source whose documents you actually reviewed this run, edit its record
in `regbase/sources/*.yaml`:

- set `last_reviewed` to today's date (`YYYY-MM-DD`) — do this even when
  nothing changed, so a stale date never implies "unchecked";
- adjust `confidence` honestly: `verified` only if you opened the agency's own
  page this run and it says what the record says; `probable` if you are relying
  on a secondary source; `unverified` if you could not confirm it. **Never
  raise `confidence` for a source you did not actually open this run.**
- fix any URL that returned 404/410 by replacing it with the page you actually
  found — and if you cannot find a replacement, leave the URL, add a `notes:`
  saying it is dead as of today, and drop `confidence` to `unverified` rather
  than deleting the record;
- if a rule series was renumbered, superseded, or given a new effective date,
  update that document's `title` and `citation_root` to match.

Then validate before you finish:

```bash
python3 -c "import sys; sys.path.insert(0,'regbase/tools'); import common; \
errs=common.validate_sources(); print('\n'.join(errs) or 'sources valid'); \
sys.exit(1 if errs else 0)"
```

Fix anything it reports. Do not commit a registry that fails validation.

**6. Commit** the reports, `regbase/corpus/watch_state.json`, and the edited
source YAML on a branch, with a message summarizing the material changes. Do
not push to the default branch.

### Rules

- **Never invent a regulatory fact.** If you did not open it this run, it is
  not confirmed. An `unverified` record is a correct outcome; a plausible
  guess is not.
- Every fact you assert must carry the URL you actually opened, pasted from the
  tool result — never retyped from memory or reconstructed from a domain name.
- You are summarizing what a public agency published. You are not giving legal
  advice; say so if the summary reads like it. Regulatory interpretation for a
  specific project needs counsel.
- Keep the summary short enough that a permitting lead reads all of it. If
  there are no material changes, say "no material changes" and stop — a long
  report about nothing trains people to ignore it.
