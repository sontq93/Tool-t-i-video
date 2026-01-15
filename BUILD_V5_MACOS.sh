#!/bin/bash
# Install PyInstaller if not exists
pip install pyinstaller --quiet

# Clean previous build
rm -rf build dist

# Build Command
# --noconfirm: overwrite output directory
# --onedir: build a folder (easier to debug and faster than --onefile)
# --windowed: no terminal window
# --name: App name
# --add-data: include yt-dlp binary
# --collect-all: include customtkinter assets
# --hidden-import: ensure Pillow and Tkinter are found

pyinstaller --noconfirm --onedir --windowed --name "VideoDownloaderProV5" \
    --add-data "yt-dlp:." \
    --collect-all customtkinter \
    --hidden-import "PIL" \
    --hidden-import "PIL._tkinter_finder" \
    app_v5.py

echo "Build Complete! App is in dist/VideoDownloaderProV5.app"
