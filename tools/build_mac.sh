#!/bin/bash
# Build "Madden Roster Exporter.app" from rosgui.py — macOS only.
#
#   chmod +x build_mac.sh
#   ./build_mac.sh
#
# Result lands in dist/. Run once; rebuild only when rosgui.py changes.

set -e
cd "$(dirname "$0")"
APP="Madden Roster Exporter"

if [ ! -f rosgui.py ]; then
  echo "rosgui.py must sit next to this script."; exit 1
fi

echo "==> checking tkinter"
python3 -c "import tkinter" 2>/dev/null || {
  echo "Your python3 has no tkinter, so the app cannot be built."
  echo "Install Python from python.org (it bundles tkinter) and try again."
  exit 1
}

echo "==> installing pyinstaller if needed"
python3 -m pip install --quiet --upgrade pyinstaller

echo "==> cleaning previous build"
rm -rf build dist "$APP.spec"

echo "==> building (this takes a minute)"
# --onedir, not --onefile: PyInstaller warns that onefile plus a .app bundle
# "don't make sense and clashes with macOS's security", and it becomes an error
# in v7. onedir also launches faster. The .app is still a single icon either way.
python3 -m PyInstaller \
  --onedir \
  --windowed \
  --name "$APP" \
  --osx-bundle-identifier com.pgm3.rosexporter \
  --noconfirm \
  rosgui.py

# Register .ros and .dbt so files can be dropped on the icon and
# "Open With" lists the app.
PLIST="dist/$APP.app/Contents/Info.plist"
if [ -f "$PLIST" ]; then
  echo "==> registering .ros / .dbt as document types"
  /usr/libexec/PlistBuddy -c "Add :CFBundleDocumentTypes array" "$PLIST" 2>/dev/null || true
  /usr/libexec/PlistBuddy -c "Add :CFBundleDocumentTypes:0 dict" "$PLIST"
  /usr/libexec/PlistBuddy -c "Add :CFBundleDocumentTypes:0:CFBundleTypeName string 'Madden Roster'" "$PLIST"
  /usr/libexec/PlistBuddy -c "Add :CFBundleDocumentTypes:0:CFBundleTypeRole string Viewer" "$PLIST"
  /usr/libexec/PlistBuddy -c "Add :CFBundleDocumentTypes:0:LSHandlerRank string Alternate" "$PLIST"
  /usr/libexec/PlistBuddy -c "Add :CFBundleDocumentTypes:0:CFBundleTypeExtensions array" "$PLIST"
  /usr/libexec/PlistBuddy -c "Add :CFBundleDocumentTypes:0:CFBundleTypeExtensions:0 string ros" "$PLIST"
  /usr/libexec/PlistBuddy -c "Add :CFBundleDocumentTypes:0:CFBundleTypeExtensions:1 string dbt" "$PLIST"
  # Ad-hoc sign so Gatekeeper complains once rather than every launch.
  codesign --force --deep --sign - "dist/$APP.app" 2>/dev/null \
    && echo "==> ad-hoc signed" \
    || echo "==> could not sign (harmless; you will approve it once)"
fi

echo
echo "Built:  dist/$APP.app"
echo
echo "FIRST RUN: macOS will refuse to open it because it is unsigned."
echo "Right-click the app -> Open -> Open. Once only."
echo
echo "Then drag it to /Applications if you want it there."
