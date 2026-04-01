#!/bin/bash
# Build Talk2Txt.app and create DMG
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
DICT_DIR="$PROJECT_DIR/dictation"
SIGN_IDENTITY="Talk2Txt Signing"

# Get version from app.py
VERSION=$(grep 'VERSION = ' "$DICT_DIR/app.py" | grep -o '"[^"]*"' | tr -d '"')
echo "Building Talk2Txt v$VERSION..."

cd "$DICT_DIR"
source .venv/bin/activate

# Build with PyInstaller
pyinstaller \
  --windowed \
  --name Talk2Txt \
  --icon "$PROJECT_DIR/scripts/Talk2Txt.icns" \
  --noconfirm \
  --hidden-import recorder \
  --hidden-import transcriber \
  --hidden-import paster \
  --hidden-import config \
  --hidden-import updater \
  --hidden-import autostart \
  --hidden-import mlx \
  --hidden-import mlx.core \
  --hidden-import mlx_metal \
  --hidden-import parakeet_mlx \
  --hidden-import AppKit \
  --hidden-import ApplicationServices \
  --collect-all mlx \
  --collect-all mlx_metal \
  --collect-all parakeet_mlx \
  --collect-all sounddevice \
  --collect-all librosa \
  --osx-bundle-identifier com.przemo.talk2txt \
  app.py

APP="dist/Talk2Txt.app"

# Patch Info.plist
defaults write "$PWD/$APP/Contents/Info" LSUIElement -bool true
defaults write "$PWD/$APP/Contents/Info" NSMicrophoneUsageDescription \
  "Talk2Txt needs microphone access for speech-to-text dictation."

# Sign with stable identity (preserves macOS permissions across updates)
codesign --force --deep --sign "$SIGN_IDENTITY" "$APP"

# Create DMG
DMG_TMP="/tmp/Talk2Txt_dmg"
DMG_OUT="$PROJECT_DIR/Talk2Txt-$VERSION.dmg"
rm -rf "$DMG_TMP" "$DMG_OUT"
mkdir -p "$DMG_TMP"
cp -R "$APP" "$DMG_TMP/"
ln -s /Applications "$DMG_TMP/Applications"
hdiutil create -volname "Talk2Txt" -srcfolder "$DMG_TMP" -ov -format UDZO "$DMG_OUT"
rm -rf "$DMG_TMP"

echo ""
echo "=== Build complete ==="
echo "App: $DICT_DIR/$APP"
echo "DMG: $DMG_OUT ($(du -sh "$DMG_OUT" | cut -f1))"
echo ""
echo "To install: cp -R $APP /Applications/"
echo "To release: gh release create v$VERSION $DMG_OUT --title 'Talk2Txt v$VERSION'"
