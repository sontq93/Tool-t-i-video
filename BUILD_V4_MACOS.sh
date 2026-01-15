#!/bin/bash
# Script build TikTok Downloader V4.0 cho macOS

echo "========================================================"
echo "   BUILD TIKTOK DOWNLOADER V4.0 - ANTI RATE LIMIT"
echo "========================================================"
echo ""

# 1. Kiểm tra Python
if ! command -v python3 &> /dev/null; then
    echo "[LỖI] Máy bạn chưa cài Python! Hãy cài Python vào máy trước nhé."
    echo "Bạn có thể cài Python bằng Homebrew: brew install python3"
    exit 1
fi

echo "Phiên bản Python: $(python3 --version)"

# 2. Cài đặt thư viện cần thiết
echo "[1/3] Đang cài đặt PyInstaller..."
python3 -m pip install pyinstaller --quiet

# 3. Tải yt-dlp phiên bản macOS nếu chưa có
if [ ! -f "yt-dlp" ]; then
    echo "[2/3] Đang tải yt-dlp phiên bản mới nhất cho macOS..."
    curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -o yt-dlp
    chmod +x yt-dlp
else
    echo "[2/3] yt-dlp đã tồn tại, bỏ qua bước tải."
fi

# 4. Đóng gói phiên bản V4
echo "[3/3] Đang đóng gói V4.0 thành file .app..."
python3 -m PyInstaller --noconfirm --onefile --windowed --name "TikTokDownloader_V4" --add-binary "yt-dlp:." app_tai_video_v4.py

echo ""
echo "========================================================"
echo "THÀNH CÔNG! File V4.0 nằm trong thư mục 'dist'"
echo "Tên file: TikTokDownloader_V4.app"
echo ""
echo "TÍNH NĂNG MỚI:"
echo " - Giới hạn số video tải (tránh bị chặn)"
echo " - Delay giữa các video (chống rate limit)"
echo " - Tự động resume khi bị ngắt"
echo " - Auto-retry 10 lần khi lỗi"
echo " - Nút tạm dừng"
echo "========================================================"
echo ""
echo "Lưu ý: Nếu macOS chặn app, hãy vào:"
echo "System Preferences > Security & Privacy > General"
echo "và nhấn 'Open Anyway'"
echo ""
echo "Hoặc chạy lệnh sau để bỏ qua kiểm tra Gatekeeper:"
echo "xattr -cr dist/TikTokDownloader_V4.app"
echo ""
