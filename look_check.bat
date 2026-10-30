@echo off
cd /d "%~dp0"
rem Where the dashboard lives on this PC. Edit this line if you move it.
set "DASHBOARD=C:\Weather Station\ecowitt-dashboard"

echo Stopping any servers left running from an earlier check on ports 8501 and 8502...
for %%P in (8501 8502) do (
  for /f "tokens=5" %%I in ('netstat -ano ^| findstr /R /C:":%%P .*LISTENING"') do taskkill /PID %%I /F >nul 2>&1
)

echo Installing the browser tool (quick if it is already installed)...
python -m pip install --quiet playwright
if errorlevel 1 goto failed
python -m playwright install chromium
if errorlevel 1 goto failed

echo Starting Weather Lab on port 8501...
start "Weather Lab" cmd /k python -m streamlit run app.py --server.port 8501
echo Starting the dashboard on port 8502...
start "Dashboard" /D "%DASHBOARD%" cmd /k python -m streamlit run dashboard_v2.0.py --server.port 8502

echo Waiting 20 seconds for both apps to start...
timeout /t 20 /nobreak >nul

python tools\compare_looks.py --pages Live Settings --dashboard-pages Live Live
if errorlevel 1 goto failed

echo.
echo Report written to report\index.html. Opening it...
start "" "report\index.html"
pause
exit /b 0

:failed
echo.
echo Stopped: a step failed. Read the messages above.
pause
exit /b 1
