# Operating runbook

## Weekly

```bash
python3 regbase/tools/check_updates.py --cadence weekly
```

Reads `corpus/reports/updates_<date>.md`. Changed documents come first, with a
unified diff of the extracted text so you can see the regulatory language that
actually moved rather than just a hash mismatch.

When something material changed:

1. Update the affected record in `regbase/sources/<state>.yaml` — its
   `permits[]`, `documents[]`, `last_reviewed`, and `confidence`.
2. Re-harvest that source: `harvest.py --source-id <id> --force`
3. Rebuild: `build_registry_json.py --indent 1 && build_index.py`
4. Commit, so the diff is in git history and any review generated afterward
   picks up the new requirement.

## Monthly

```bash
python3 regbase/tools/harvest.py --state CO --delay 1.5    # full re-fetch, per state
python3 regbase/tools/watch_agendas.py --state CO
```

The agenda watcher is the early-warning half: it finds proposed land use code
amendments, moratoria, and setback changes *before* adoption, which is when
there is still time to react.

## Quarterly

```bash
python3 regbase/tools/refresh_people.py --stale-days 90
```

Produces a work queue of research prompts. Run them in a Claude session with
search budget. Collection is limited to public, role-related information — see
`regbase/people/README.md`, which is binding.

Re-run in full after any election or a known department reorganization.

## Adding a jurisdiction

1. Add a record to the right `regbase/sources/<state>.yaml`, matching
   `schemas/source.schema.json`. Set `confidence` honestly.
2. Validate:
   ```bash
   python3 -c "import sys; sys.path.insert(0,'regbase/tools'); import common; \
               print('\n'.join(common.validate_sources()) or 'valid')"
   ```
3. `build_registry_json.py --indent 1`
4. `harvest.py --source-id <new-id>`
5. `build_index.py`

## When a review is wrong

The generated review carries a `provenance` block naming every source record it
consulted. Trace the bad requirement back to its `source_id`, fix the registry
record, and regenerate. Do not hand-patch the output — the next review will
repeat the error.

## Search budget

`WebSearch` is capped at 200 calls per Claude session, shared across all
subagents in that session. Research passes are therefore scoped one state (or
one region) per session. With outbound HTTPS enabled, `harvest.py --crawl`
replaces most of that searching and has no such cap.
