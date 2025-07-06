@echo off
REM update_translations.bat
REM Script Windows batch pour mettre à jour toutes les traductions

echo.
echo ℹ️  Mise à jour des traductions Claude Usage Monitor
echo ℹ️  Utilisation du script Python générique...
echo.

REM Changer vers le répertoire du script
cd /d "%~dp0"

REM Exécuter le script Python
python update_all_translations.py %*

REM Vérifier le code de retour
if %ERRORLEVEL% EQU 0 (
    echo.
    echo ✅ Script terminé avec succès!
) else (
    echo.
    echo ❌ Le script a échoué avec le code: %ERRORLEVEL%
    exit /b %ERRORLEVEL%
)

pause
