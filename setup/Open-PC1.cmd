@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Open-PC1.ps1"
if errorlevel 1 pause
