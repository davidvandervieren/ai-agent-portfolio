# Windows setup

Target location: `C:\Users\david\OneDrive\Desktop\WES Reg Project`

Nothing in the toolchain hardcodes a path — everything resolves relative to
`regbase/`, so the project works wherever you put it.

## Install

Unzip the delivered archive so the structure is:

```
C:\Users\david\OneDrive\Desktop\WES Reg Project\
    regbase\
    .claude\
    .github\
    README.md
```

Then, in PowerShell:

```powershell
cd "C:\Users\david\OneDrive\Desktop\WES Reg Project"
powershell -ExecutionPolicy Bypass -File .\regbase\tools\setup-windows.ps1
```

That installs the dependencies, sets `REGBASE_RAW` and `REGBASE_UA`, and builds
the index. **Open a new terminal afterwards** so the environment variables take
effect.

## The OneDrive problem

`corpus/raw/` will hold the downloaded PDFs and HTML — plausibly tens of
gigabytes once the municipal codes are crawled. Inside OneDrive that becomes a
sync problem, not a storage problem.

The setup script therefore points `REGBASE_RAW` at `C:\RegBaseCorpus\raw`,
outside OneDrive. `corpus/text/` — the extracted text, which is small and is
what change-detection diffs — stays in the project where it syncs and stays
diffable.

To choose a different location:

```powershell
.\regbase\tools\setup-windows.ps1 -RawCorpus "D:\RegBaseCorpus\raw"
```

## Commands

Windows uses `py` rather than `python3`. Everywhere the docs say `python3`,
substitute `py`:

```powershell
py regbase\tools\query.py stack --state CO --county Weld --asset compressor_station
py regbase\tools\query.py permits --state NM --county Lea
py regbase\tools\query.py gaps --state TX

py regbase\tools\harvest.py --dry-run --state CO
py regbase\tools\harvest.py --state CO --delay 1.5

py regbase\tools\review.py "C:\path\to\project.kmz" `
    --project-name "Silo Station" --reviewer "David Van der Vieren" `
    --asset midstream_pipeline --asset compressor_station `
    --state CO --county Arapahoe --out reviews
```

PowerShell continues lines with a backtick, not a backslash.

## The KML tool

Double-clicking `regbase\web\pre-project-review.html` works, but a `file://`
page cannot `fetch` `registry.json`. The tool detects this and offers a
"Load registry.json" file picker — point it at `regbase\web\registry.json` and
everything works.

To skip that step, serve the folder:

```powershell
py -m http.server 8000 --directory regbase\web
```

then open <http://localhost:8000/pre-project-review.html>.

## Scheduled update checks

The repo ships a GitHub Actions workflow, but if you are running this locally,
use Task Scheduler instead:

```powershell
$action  = New-ScheduledTaskAction -Execute "py" `
    -Argument "regbase\tools\check_updates.py --due" `
    -WorkingDirectory "C:\Users\david\OneDrive\Desktop\WES Reg Project"
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At 6:15am
Register-ScheduledTask -TaskName "RegBase update check" `
    -Action $action -Trigger $trigger -Description "Weekly regulatory change check"
```

Reports land in `regbase\corpus\reports\`.

## Git

The project is a git repository with full history. If you want it on GitHub,
create the repo and push from here:

```powershell
git remote -v                        # check what is configured
git push -u origin claude/oil-gas-regulatory-requirements-tsu7xs
```

History is worth keeping — the update checker's value is in diffing regulatory
text over time, and git is where that record lives.
