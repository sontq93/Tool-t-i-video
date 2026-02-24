# 🚀 Hướng Dẫn Sử Dụng GitHub Actions

## 📋 Bước 1: Tạo Repository trên GitHub

1. Vào https://github.com/new
2. Đặt tên repository (ví dụ: `tiktok-downloader`)
3. Chọn **Public** hoặc **Private** (tùy ý)
4. Nhấn **Create repository**

## 📤 Bước 2: Push Code Lên GitHub

Mở Terminal trong thư mục `tiktok_tool` và chạy:

```bash
# Khởi tạo git (nếu chưa có)
git init

# Thêm tất cả file
git add .

# Commit
git commit -m "Initial commit - TikTok Downloader V5.0"

# Thêm remote (thay YOUR_USERNAME và YOUR_REPO)
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git

# Push lên GitHub
git branch -M main
git push -u origin main
```

## 🏷️ Bước 3: Tạo Release (Trigger Build)

### Cách 1: Tự động với Git Tag
```bash
# Tạo tag version mới
git tag v5.0

# Push tag lên GitHub
git push origin v5.0
```

GitHub Actions sẽ **tự động**:
- Build trên macOS → tạo file `.app`
- Build trên Windows → tạo file `.exe`
- Tạo GitHub Release với 2 file download

### Cách 2: Chạy Thủ Công
1. Vào repository trên GitHub
2. Nhấn tab **Actions**
3. Chọn workflow **"Build TikTok Downloader"**
4. Nhấn **Run workflow** → **Run workflow**

## 📥 Bước 4: Download File Build

Sau khi build xong (khoảng 5-10 phút):

1. Vào tab **Releases** trên GitHub
2. Download:
   - `TikTokDownloader_V4_macOS.zip` → cho Mac
   - `TikTokDownloader_V4.exe` → cho Windows

## 🔄 Cập Nhật Sau Này

Khi bạn sửa code và muốn build lại:

```bash
# Sửa code xong
git add .
git commit -m "Update: thêm tính năng xyz"
git push

# Tạo version mới
git tag v5.1
git push origin v5.1
```

GitHub Actions sẽ tự động build lại!

## ⚠️ Lưu Ý

- GitHub Actions **MIỄN PHÍ** cho public repo
- Private repo có giới hạn: 2000 phút/tháng (vẫn đủ dùng)
- Mỗi lần build mất khoảng 5-10 phút
- File build sẽ lưu trữ vĩnh viễn trong Releases

## 🆘 Khắc Phục Sự Cố

Nếu build bị lỗi:
1. Vào tab **Actions**
2. Click vào build job bị lỗi
3. Xem log để biết lỗi gì
4. Sửa code và push lại

## 📞 Hỗ Trợ

- Tài liệu GitHub Actions: https://docs.github.com/en/actions
- Ví dụ workflow: https://github.com/actions/starter-workflows
