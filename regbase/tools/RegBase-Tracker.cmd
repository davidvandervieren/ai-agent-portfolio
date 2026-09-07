@echo off
REM Live RegBase corpus tracker.
REM
REM Regenerates the tracker page on an interval and opens it once. The page
REM carries a matching <meta refresh>, so an open browser tab keeps pace with a
REM harvest that is still running. Close this window (or Ctrl+C) to stop.
REM
REM Works both from regbase\tools\ and as a copy on the Desktop: it looks for
REM the project next to itself first, then falls back to REGBASE_HOME, then to
REM C:\RegBase.

setlocal
set "TRACKER=%~dp0..\..\regbase\tools\tracker.py"
if not exist "%TRACKER%" set "TRACKER=%REGBASE_HOME%\regbase\tools\tracker.py"
if not exist "%TRACKER%" set "TRACKER=C:\RegBase\regbase\tools\tracker.py"
if not exist "%TRACKER%" (
  echo Could not find regbase\tools\tracker.py.
  echo Set REGBASE_HOME to the folder containing "regbase", then run this again.
  pause
  exit /b 1
)

set "OUT=%USERPROFILE%\Desktop\RegBase-tracker.html"
if exist "%USERPROFILE%\OneDrive\Desktop\" set "OUT=%USERPROFILE%\OneDrive\Desktop\RegBase-tracker.html"

echo RegBase tracker - refreshing every 20s. Close this window to stop.
echo Page: %OUT%
echo.
py "%TRACKER%" --out "%OUT%" --watch 20 --open
endlocal
