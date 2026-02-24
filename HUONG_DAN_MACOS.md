# Hướng Dẫn Sử Dụng TikTok Downloader trên macOS

## Yêu Cầu Hệ Thống
- macOS 10.13 (High Sierra) trở lên
- Python 3.7 trở lên
- Kết nối Internet

## Cài Đặt Python (nếu chưa có)

### Cách 1: Sử dụng Homebrew (Khuyến nghị)
```bash
# Cài đặt Homebrew nếu chưa có
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Cài đặt Python
brew install python3
```

### Cách 2: Tải từ python.org
Truy cập https://www.python.org/downloads/macos/ và tải bản cài đặt

## Cách Sử Dụng

### Bước 1: Mở Terminal
- Nhấn `Cmd + Space` và gõ "Terminal"
- Hoặc vào `Applications > Utilities > Terminal`

### Bước 2: Di chuyển đến thư mục chứa file
```bash
cd /đường/dẫn/đến/thư/mục/tiktok_tool
```

### Bước 3: Cấp quyền thực thi cho script
```bash
# Cho phiên bản cơ bản
chmod +x CHAY_TREN_MACOS.sh

# Hoặc cho phiên bản V4
chmod +x BUILD_V4_MACOS.sh
```

### Bước 4: Chạy script build
```bash
# Phiên bản cơ bản
./CHAY_TREN_MACOS.sh

# Hoặc phiên bản V4 (khuyến nghị)
./BUILD_V4_MACOS.sh
```

### Bước 5: Chạy ứng dụng
Sau khi build xong, file `.app` sẽ nằm trong thư mục `dist/`

```bash
# Mở ứng dụng
open dist/TikTokDownloader_V4.app
```

## Xử Lý Lỗi Bảo Mật macOS

Nếu macOS chặn ứng dụng với thông báo "cannot be opened because the developer cannot be verified":

### Cách 1: Qua System Preferences
1. Mở `System Preferences` (hoặc `System Settings` trên macOS Ventura+)
2. Vào `Security & Privacy` > `General`
3. Nhấn `Open Anyway` bên cạnh thông báo về ứng dụng

### Cách 2: Dùng Terminal (Nhanh hơn)
```bash
# Bỏ qua kiểm tra Gatekeeper
xattr -cr dist/TikTokDownloader_V4.app

# Sau đó mở lại ứng dụng
open dist/TikTokDownloader_V4.app
```

## So Sánh Phiên Bản

### Phiên Bản Cơ Bản (CHAY_TREN_MACOS.sh)
- Tải video TikTok đơn giản
- Giao diện cơ bản

### Phiên Bản V4 (BUILD_V4_MACOS.sh) - **Khuyến nghị**
- ✅ Giới hạn số video tải (tránh bị chặn)
- ✅ Delay giữa các video (chống rate limit)
- ✅ Tự động resume khi bị ngắt
- ✅ Auto-retry 10 lần khi lỗi
- ✅ Nút tạm dừng/tiếp tục
- ✅ Giao diện thân thiện hơn

## Gỡ Lỗi

### Lỗi: "python3: command not found"
**Giải pháp:** Cài đặt Python theo hướng dẫn ở trên

### Lỗi: "Permission denied"
**Giải pháp:** 
```bash
chmod +x BUILD_V4_MACOS.sh
```

### Lỗi: "No module named 'tkinter'"
**Giải pháp:** 
```bash
# Cài đặt tkinter
brew install python-tk@3.11
```

### Ứng dụng bị crash khi mở
**Giải pháp:** Chạy từ Terminal để xem lỗi:
```bash
./dist/TikTokDownloader_V4.app/Contents/MacOS/TikTokDownloader_V4
```

## Ghi Chú
- Lần đầu chạy script sẽ tải `yt-dlp` (khoảng 3-10 MB)
- Quá trình build mất khoảng 1-3 phút
- File `.app` cuối cùng có dung lượng khoảng 15-25 MB
- Có thể chia sẻ file `.app` cho người khác dùng macOS

## Hỗ Trợ
Nếu gặp vấn đề, hãy kiểm tra:
1. Phiên bản Python: `python3 --version`
2. Phiên bản macOS: `sw_vers`
3. Log lỗi khi chạy script
