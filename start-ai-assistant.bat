@echo off
title Jellyfin AI Assistant
echo ============================================
echo   Jellyfin AI Assistant
echo   Keep this window open to keep AI running
echo   (close this window to stop the AI service)
echo ============================================
echo.
"%~dp0jellyfin-agent.exe"
echo.
echo AI service stopped.
pause
