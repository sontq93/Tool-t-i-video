#!/bin/bash
# Script tự động tạo file app cho macOS

echo "--- TỰ ĐỘNG TẠO FILE APP CHO MACOS ---"
echo ""

# 1. Kiểm tra Python
if ! command -v python3 &> /dev/null; then
    echo "[LỖI] Máy bạn chưa cài Python! Hãy cài Python vào máy trước nhé."
    echo "Bạn có thể cài Python bằng Homebrew: brew install python3"
    exit 1
fi

echo "Phiên bản Python: $(python3 --version)"

# 2. Cài đặt thư viện cần thiết
echo "[1/3] Đang cài đặt thư viện PyInstaller..."
python3 -m pip install pyinstaller

# 3. Tải yt-dlp phiên bản macOS
echo "[2/3] Đang tải yt-dlp phiên bản mới nhất cho macOS..."
curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -o yt-dlp
chmod +x yt-dlp

# 4. Đóng gói
echo "[3/3] Đang đóng gói thành file .app..."
python3 -m PyInstaller --noconfirm --onefile --windowed --name "TikTokDownloader" --add-binary "yt-dlp:." app_tai_video.py

echo ""
echo "========================================================"
echo "THÀNH CÔNG! File chạy của bạn nằm trong thư mục 'dist'"
echo "Tên file là: TikTokDownloader.app"
echo "========================================================"
echo ""
echo "Lưu ý: Nếu macOS chặn app, hãy vào:"
echo "System Preferences > Security & Privacy > General"
echo "và nhấn 'Open Anyway'"
echo ""
