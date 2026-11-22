@echo off
title Jellyfin AI Assistant - Install Plugin
echo ============================================
echo   Jellyfin AI Assistant - Install Plugin
echo ============================================
echo.

set "PLUGINS_DIR="
if exist "%LOCALAPPDATA%\jellyfin\plugins" set "PLUGINS_DIR=%LOCALAPPDATA%\jellyfin\plugins"
if exist "%PROGRAMDATA%\Jellyfin\Server\plugins" set "PLUGINS_DIR=%PROGRAMDATA%\Jellyfin\Server\plugins"
if exist "%~dp0plugins" set "PLUGINS_DIR=%~dp0plugins"
if exist "%~dp0..\plugins" set "PLUGINS_DIR=%~dp0..\plugins"

if not "%PLUGINS_DIR%"=="" goto found
echo [WARN] Could not auto-detect the Jellyfin plugins folder.
set /p PLUGINS_DIR="Please type the plugins folder path: "

:found
if not exist "%PLUGINS_DIR%" (
    echo.
    echo [ERROR] Folder not found: %PLUGINS_DIR%
    echo.
    pause
    exit /b 1
)

echo Plugins folder: %PLUGINS_DIR%
echo.

set "DEST=%PLUGINS_DIR%\Jellyfin.Agent"
if not exist "%DEST%" mkdir "%DEST%"

copy /Y "%~dp0plugin\Jellyfin.Plugin.Agent.dll" "%DEST%\" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Could not copy the plugin file. It is likely locked by Jellyfin.
    echo Please exit Jellyfin first (right-click its tray icon, click Exit),
    echo then run this script again.
    echo.
    pause
    exit /b 1
)
copy /Y "%~dp0plugin\meta.json" "%DEST%\" >nul 2>&1

echo [DONE] Plugin installed to:
echo   %DEST%
echo.
echo Next steps:
echo   1. Restart Jellyfin
echo   2. Double-click start-ai-assistant.bat
echo   3. Open Jellyfin web, go to AI Assistant in main menu, fill DeepSeek API Key
echo.
pause
