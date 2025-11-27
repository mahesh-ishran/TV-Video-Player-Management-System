@echo off
echo ===================================
echo WebOS Video Receiver App - Setup
echo ===================================
echo.

REM Create project directory
set PROJECT_NAME=video-receiver-app
echo Creating project directory: %PROJECT_NAME%
mkdir %PROJECT_NAME% 2>nul
cd %PROJECT_NAME%

echo.
echo Setting up project structure...

REM Create necessary files
echo Creating appinfo.json...
(
echo {
echo   "id": "com.example.videoreceiver",
echo   "version": "1.0.0",
echo   "vendor": "My Company",
echo   "type": "web",
echo   "main": "index.html",
echo   "title": "Video Receiver",
echo   "icon": "icon.png",
echo   "resolution": "1920x1080"
echo }
) > appinfo.json

REM Create placeholder icon (80x80)
echo Creating placeholder icons...
echo. > icon.png
echo. > largeIcon.png

echo.
echo ===================================
echo Project structure created!
echo ===================================
echo.
echo Next steps:
echo 1. Copy the index.html file into this directory
echo 2. Connect your TV to Developer Mode
echo 3. Run: setup-tv.bat
echo.
echo Project location: %CD%
echo.
pause