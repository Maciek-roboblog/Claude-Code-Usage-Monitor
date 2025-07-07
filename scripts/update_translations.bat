@echo off
REM update_translations.bat
REM Windows batch script to update all translations

echo.
echo ℹ️  Updating Claude Usage Monitor translations
echo ℹ️  Using the generic Python script...
echo.

REM Change to the script directory
cd /d "%~dp0"

REM Run the Python script
python update_all_translations.py %*

REM Check the return code
if %ERRORLEVEL% EQU 0 (
    echo.
    echo ✅ Script completed successfully!
) else (
    echo.
    echo ❌ The script failed with code: %ERRORLEVEL%
    exit /b %ERRORLEVEL%
)

pause
