@echo off
echo DSTURN AI Logo Update Script
echo ============================
echo.

REM Check if the logo file exists
if not exist "dsturn_ai_logo.png" (
    echo ERROR: dsturn_ai_logo.png not found!
    echo Please place your DSTURN AI logo in this directory first.
    echo.
    pause
    exit /b 1
)

echo Found dsturn_ai_logo.png
echo Updating logo files...

REM Copy main icon
copy /Y "dsturn_ai_logo.png" "icon.png"
echo Updated icon.png

REM Copy tray icon (you may want to resize this manually)
copy /Y "dsturn_ai_logo.png" "icon_tray.png" 
echo Updated icon_tray.png

REM Copy logo
copy /Y "dsturn_ai_logo.png" "logo.png"
echo Updated logo.png

echo.
echo IMPORTANT: 
echo - You'll need to manually create icon.ico and icon.icns files
echo - Use an online converter or tools like ImageMagick
echo - icon.ico should contain multiple sizes (16x16, 32x32, 48x48, 256x256)
echo - icon.icns is for macOS and requires special formatting
echo.
echo Basic logo files updated successfully!
pause
