@echo off
chcp 65001 >nul
echo ========================================================
echo    BUILD TIKTOK DOWNLOADER V4.0 - ANTI RATE LIMIT
echo ========================================================
echo.

:: 1. Kiem tra Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [LOI] May ban chua cai Python! Hay cai Python vao may truoc nhe.
    pause
    exit /b
)

:: 2. Cai dat thu vien can thiet
echo [1/3] Dang cai dat PyInstaller...
python -m pip install pyinstaller --quiet

:: 3. Tai yt-dlp phien ban Windows (.exe) neu chua co
if not exist yt-dlp.exe (
    echo [2/3] Dang tai yt-dlp.exe phien ban moi nhat...
    curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe -o yt-dlp.exe
) else (
    echo [2/3] yt-dlp.exe da ton tai, bo qua buoc tai.
)

:: 4. Dong goi phien ban V4
echo [3/3] Dang dong goi V4.0 thanh file .exe...
python -m PyInstaller --noconfirm --onefile --windowed --name "TikTokDownloader_V4" --add-binary "yt-dlp.exe;." app_tai_video_v4.py

echo.
echo ========================================================
echo THANH CONG! File V4.0 nam trong thu muc 'dist'
echo Ten file: TikTokDownloader_V4.exe
echo 
echo TINH NANG MOI:
echo  - Gioi han so video tai (tranh bi chan)
echo  - Delay giua cac video (chong rate limit)
echo  - Tu dong resume khi bi ngat
echo  - Auto-retry 10 lan khi loi
echo  - Nut tam dung
echo ========================================================
pause
