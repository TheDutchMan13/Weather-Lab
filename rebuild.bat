@echo off
cd /d "%~dp0"
echo Running tests...
python -m unittest discover -s tests -p "test_*.py"
if errorlevel 1 goto failed
echo.
echo Building the exe...
python build_exe.py
if errorlevel 1 goto failed
echo.
echo Building the installer...
python build_installer.py
if errorlevel 1 goto failed
echo.
echo Done.
echo   Exe:       dist\WeatherLab\WeatherLab.exe
echo   Installer: installer\WeatherLabSetup-0.16.0.exe
pause
exit /b 0

:failed
echo.
echo Stopped: a step failed. Read the messages above.
pause
exit /b 1
