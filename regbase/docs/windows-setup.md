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

## Keeping the project in Google Drive

The same sync hazard applies to Google Drive's desktop folder, so harvests
never write there directly. After a run, mirror the whole project:

```powershell
.\regbase\tools\sync-drive.ps1
```

That fills `<Destination>\RegBase\` with the project (tools, registry, docs,
web, people, `corpus\text`, manifest and index) and `<Destination>\RegBase\raw\`
with the raw downloads from `REGBASE_RAW`, keeping the state/jurisdiction
folders and removing files a re-harvest replaced. The default destination is
`G:\My Drive\Datum Power\Repos\Regulations`; pass `-Destination` for another,
`-RawOnly` to skip the project half. The script touches nothing in the
destination outside `RegBase\`, so it sits safely beside other material.

With Drive holding a complete copy, GitHub is optional. Local commits still
give you history; `git push` only matters if you want that history off the
machine too.

Update packages arrive in `<Destination>\RegBase\_updates\`. To apply one:

```powershell
Expand-Archive -Path "G:\My Drive\Datum Power\Repos\Regulations\RegBase\_updates\<name>.zip" -DestinationPath "C:\RegBase" -Force
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

## Troubleshooting

**`Microsoft Visual C++ 14.0 or greater is required` during pip install.**
A dependency had no prebuilt wheel for your Python version, so pip tried to
compile it. You do not need a compiler — you need a version that ships a wheel.
`requirements.txt` uses version floors rather than exact pins for this reason.
If it happens anyway, install that one package unpinned:

```powershell
py -m pip install --upgrade <package>
```

This bit PyYAML on Python 3.14: 6.0.1 has no cp314 wheel, 6.0.2 does.

**`PermissionError: [Errno 13]` reading a `.py` file.**
Mark-of-the-web on files extracted from a downloaded zip. Clear it:

```powershell
Get-ChildItem C:\RegBase -Recurse -File | Unblock-File
```

If that does not do it, the copy inherited restrictive ACLs:

```powershell
takeown /F C:\RegBase /R /D Y
icacls C:\RegBase /grant "$env:USERNAME:(OI)(CI)F" /T
```

**`The argument '.\regbase\tools\setup-windows.ps1' ... does not exist`.**
You are not in the project root. `dir` should show `regbase` and `README.md`.
Watch for a doubled folder — extracting `WESRegProject.zip` into a folder that
is already named for the project nests it one level deeper than expected.

**PowerShell parse errors with mismatched braces all over a `.ps1`.**
Windows PowerShell 5.1 decodes `.ps1` as the system ANSI code page unless the
file has a UTF-8 BOM, so one non-ASCII character corrupts the parse and the
reported line numbers are meaningless. `regbase/tools/tests/test_windows_encoding.py`
checks every shipped script for this.

**Files show `l` in the `Mode` column.**
Those are OneDrive cloud placeholders, not local files. Either mark the folder
"Always keep on this device", or work outside OneDrive — which you want anyway
once the corpus starts growing.

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
