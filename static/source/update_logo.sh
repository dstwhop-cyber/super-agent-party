#!/bin/bash

echo "DSTURN AI Logo Update Script"
echo "============================"
echo

# Check if the logo file exists
if [ ! -f "dsturn_ai_logo.png" ]; then
    echo "ERROR: dsturn_ai_logo.png not found!"
    echo "Please place your DSTURN AI logo in this directory first."
    echo
    exit 1
fi

echo "Found dsturn_ai_logo.png"
echo "Updating logo files..."

# Copy main icon
cp "dsturn_ai_logo.png" "icon.png"
echo "Updated icon.png"

# Copy tray icon (you may want to resize this manually)
cp "dsturn_ai_logo.png" "icon_tray.png" 
echo "Updated icon_tray.png"

# Copy logo
cp "dsturn_ai_logo.png" "logo.png"
echo "Updated logo.png"

echo
echo "IMPORTANT: "
echo "- You'll need to manually create icon.ico and icon.icns files"
echo "- Use an online converter or tools like ImageMagick"
echo "- icon.ico should contain multiple sizes (16x16, 32x32, 48x48, 256x256)"
echo "- icon.icns is for macOS and requires special formatting"
echo
echo "Basic logo files updated successfully!"
