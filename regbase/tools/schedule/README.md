# RegBase change-monitoring — automation wiring

Three ways to run the change-monitoring subsystem on a schedule. Pick one (or
run cron for the sweep and the Claude Routine for the review — they compose).

| | what runs it | good for |
|---|---|---|
| `regbase-weekly.cron` | a machine you control | full control, no API limits, logs on disk |
| `../../../.github/workflows/regbase-update-check.yml` | GitHub Actions | no server to own; opens an issue when something changes |
| `claude_routine.md` | a Claude scheduled Routine | the *review* step — reading the diffs and updating the YAML |

Everything here needs **outbound HTTPS**. `check_updates.py` and
`watch_agendas.py` probe egress up front and exit non-zero with instructions
rather than emitting hundreds of connection failures. `refresh_people.py`
never touches the network at all.

---

## 1. cron

```bash
python3 -m pip install -r regbase/tools/requirements.txt   # pinned toolchain
mkdir -p /opt/regbase/regbase/corpus/logs        # the cron lines log here
crontab -l | cat - regbase/tools/schedule/regbase-weekly.cron | crontab -
crontab -l                                        # verify
```

Edit `REGBASE_HOME` and `REGBASE_UA` at the top of the file first. `REGBASE_UA`
is read by `common.Fetcher`; put a real contact address in it.

The schedule, in words:

| when | command | why |
|---|---|---|
| Mon 06:15 | `check_updates.py --cadence weekly` | sources that opted into a weekly cadence |
| Mon 06:45 | `check_updates.py --due` | **the practical weekly sweep** — anything whose own cadence has elapsed |
| Mon 08:00 | `watch_agendas.py --days 45` | pending-change early warning |
| 1st 03:00 | `check_updates.py` (no filter) | full monthly sweep of every watched URL |
| 1st 07:00 | `check_updates.py --cadence monthly` | monthly-cadence sources (drop if you keep the full sweep) |
| Quarterly 04:00 | `check_updates.py --cadence quarterly` | quarterly-cadence sources |
| Quarterly 05:00 | `refresh_people.py --stale-days 90` | rebuild the people research queue |

### Why `--due` and not just `--cadence weekly`

`--cadence X` selects sources whose `update_watch.cadence` **is** `X`. Nothing
in the registry currently declares `weekly`, so that line is a no-op until a
source opts in. `--due` instead asks "has this URL's own cadence elapsed since
`last_checked`?" — so a single weekly job self-paces the whole registry and
never re-polls a quarterly source seven times a quarter. Run both; they cost
almost nothing when there is nothing due.

### Politeness

`--delay` is a per-host floor between requests, applied by `common.Fetcher`
along with retry/backoff and conditional GET. Do not drop it below ~1s against
county and municipal sites; many are small shared-hosting installs. The
monthly full sweep is ~580 URLs — at `--delay 3` that is comfortably an
overnight job.

### Output

- `corpus/reports/updates_<date>.md` / `.json`
- `corpus/reports/agenda_watch_<date>.md`
- `corpus/reports/people_refresh_queue_<date>.md`
- `corpus/watch_state.json` — per-URL etag/hash/last-changed state
- `corpus/watch_text/` — text snapshots, so the *next* run can diff

Commit `corpus/reports/` and `corpus/watch_state.json`; the change history is
the point. `corpus/raw/` is already gitignored.

---

## 2. GitHub Actions

`.github/workflows/regbase-update-check.yml` (repo root) runs the checker
weekly on a GitHub-hosted runner, uploads the report as an artifact, and opens
an issue when something changed. It uses only the built-in `GITHUB_TOKEN` —
**no secrets to add** — with `permissions:` narrowed to `contents: write` (to
commit the report and updated watch state) and `issues: write`.

Trigger it by hand from the Actions tab (`workflow_dispatch`) to test; it also
accepts a `cadence` input there.

---

## 3. Claude Routine (the review step)

Cron and Actions detect change. They cannot tell you whether a moved paragraph
matters to a compressor-station siting. `claude_routine.md` holds the exact
standalone prompt to paste into a Claude scheduled Routine so a session runs
the checker, reads the diffs, judges materiality, and updates the affected
`regbase/sources/*.yaml` records' `last_reviewed`/`confidence`.

Suggested cadence: weekly, an hour after the cron sweep, so the reports are
already on disk.
