import subprocess
import os
import sys

# Đường dẫn đến file công cụ tải (nằm cùng thư mục)
tool_path = os.path.join(os.path.dirname(__file__), "yt-dlp")

def tai_video():
    print("--- CÔNG CỤ TẢI VIDEO TIKTOK (Sử dụng yt-dlp) ---")
    
    # 1. Nhập link
    if len(sys.argv) > 1:
        link = sys.argv[1]
    else:
        link = input("👉 Dán link video (hoặc link trang cá nhân) vào đây rồi ấn Enter: ").strip()

    if not link:
        print("❌ Chưa nhập link!")
        return

    print(f"\n⏳ Đang tải video từ: {link}...")
    
    print("⚠️  LƯU Ý: Nếu tải CẢ KÊNH, sẽ mất 1-2 phút để lấy danh sách video trước khi bắt đầu tải. Vui lòng kiên nhẫn đợi...")
    
    # 2. Chạy lệnh tải
    # Mẹo: format tên file là 'Tên người đăng - Mô tả.mp4'
    # Tự động tạo thư mục tên người đăng để chứa video
    # --ignore-errors: Lỗi 1 video không làm dừng cả quá trình
    cmd = [tool_path, "--no-check-certificate", "--ignore-errors", "-o", "%(uploader)s/%(upload_date)s - %(title)s.%(ext)s", link]
    
    try:
        subprocess.run(cmd, check=True)
        print("\n✅ TẢI XONG! Video đã được lưu trong thư mục này.")
    except Exception as e:
        print(f"\n❌ Có lỗi xảy ra: {e}")
        print("Có thể link không đúng hoặc mạng có vấn đề.")

if __name__ == "__main__":
    tai_video()
