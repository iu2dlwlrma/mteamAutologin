@echo off
echo Starting M-Team Auto Login Tool...
echo.

echo Running auto installer...
where python >nul 2>&1
if %errorlevel% == 0 (
    python install.py
) else if exist "%USERPROFILE%\AppData\Local\Microsoft\WindowsApps\python.exe" (
    "%USERPROFILE%\AppData\Local\Microsoft\WindowsApps\python.exe" install.py
) else if exist "python.exe" (
    python install.py
) else if exist "py.exe" (
    py install.py
) else (
    echo Error: Python interpreter not found
    echo Please ensure Python is properly installed
    pause
    exit /b 1
)

echo.
echo Installation complete, starting main program...
echo.

echo Running M-Team Auto Login...
where python >nul 2>&1
if %errorlevel% == 0 (
    python run.py
) else if exist "%USERPROFILE%\AppData\Local\Microsoft\WindowsApps\python.exe" (
    "%USERPROFILE%\AppData\Local\Microsoft\WindowsApps\python.exe" run.py
) else if exist "python.exe" (
    python run.py
) else if exist "py.exe" (
    py run.py
) else (
    echo Error: Python interpreter not found
    echo Please ensure Python is properly installed
    pause
    exit /b 1
)

echo.
echo Program completed, exiting automatically...
timeout /t 2 /nobreak >nul 