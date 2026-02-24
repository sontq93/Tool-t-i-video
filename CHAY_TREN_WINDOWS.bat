@echo off
chcp 65001 >nul
echo --- TU DONG TAO FILE EXE CHO WINDOWS ---
echo.

:: 1. Kiem tra Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [LOI] May ban chua cai Python! Hay cai Python vao may truoc nhe.
    pause
    exit /b
)

:: 2. Cai dat thu vien can thiet
echo [1/3] Dang cai dat thu vien PyInstaller...
pip install pyinstaller

:: 3. Tai yt-dlp phien ban Windows (.exe)
echo [2/3] Dang tai yt-dlp.exe phien ban moi nhat...
curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe -o yt-dlp.exe

:: 4. Dong goi
echo [3/3] Dang dong goi thanh file .exe...
pyinstaller --noconfirm --onefile --windowed --name "TikTokDownloader" --add-binary "yt-dlp.exe;." app_tai_video.py

echo.
echo ========================================================
echo THANH CONG! File chay cua ban nam trong thu muc 'dist'
echo Ten file la: TikTokDownloader.exe
echo ========================================================
pause
