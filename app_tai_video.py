import tkinter as tk
from tkinter import messagebox, scrolledtext, filedialog, ttk
import subprocess
import os
import sys
import threading
import time
import datetime
import platform

# Xác định đường dẫn file khi chạy bình thường hoặc khi đã đóng gói (Frozen)
if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
else:
    base_path = os.path.dirname(__file__)

# Tự động chọn tên file tủy theo hệ điều hành đang chạy
tool_name = "yt-dlp.exe" if platform.system() == "Windows" else "yt-dlp"
TOOL_PATH = os.path.join(base_path, tool_name)

def log(message):
    log_area.insert(tk.END, message + "\n")
    log_area.see(tk.END)

def chon_thu_muc():
    folder_selected = filedialog.askdirectory()
    if folder_selected:
        entry_folder.delete(0, tk.END)
        entry_folder.insert(0, folder_selected)

def tai_video_thread():
    link = entry_link.get().strip()
    save_folder = entry_folder.get().strip()

    if not link:
        messagebox.showwarning("Chưa nhập link", "Bạn ơi, dán link vào đã nhé!")
        return

    # Nếu chưa chọn thư mục thì dùng thư mục hiện tại
    if not save_folder:
        save_folder = os.getcwd()

    # Lấy các tùy chọn
    is_mp3 = var_mp3.get()
    quality = cmb_quality.get() 
    schedule_time = entry_schedule.get().strip()
    use_cookies = var_cookies.get()

    # Xử lý hẹn giờ
    if schedule_time:
        try:
            now = datetime.datetime.now()
            target = datetime.datetime.strptime(schedule_time, "%H:%M").replace(
                year=now.year, month=now.month, day=now.day
            )
            if target < now:
                target += datetime.timedelta(days=1)
            
            wait_seconds = (target - now).total_seconds()
            
            btn_download.config(state=tk.DISABLED, text=f"Đang đợi đến {schedule_time}...")
            log(f"⏰ Đã hẹn giờ! Máy sẽ tự động tải sau {int(wait_seconds)} giây nữa...")
            time.sleep(wait_seconds)
            
        except ValueError:
            messagebox.showerror("Lỗi ngày giờ", "Giờ hẹn không đúng format HH:MM (Ví dụ: 23:00)")
            return

    # Bắt đầu tải
    btn_download.config(state=tk.DISABLED, text="Đang xử lý...")
    log(f"🚀 Đang kết nối với: {link}")
    
    def run_process():
        try:
            cmd = [TOOL_PATH, "--no-check-certificate", "--ignore-errors"]
            
            # 1. Xử lý MP3
            if is_mp3:
                cmd.extend(["-x", "--audio-format", "mp3"])
                output_format = "%(uploader)s/%(upload_date)s - %(title)s.mp3"
                log("🎵 Chế độ: Chỉ tải âm thanh (MP3)")
            else:
                output_format = "%(uploader)s/%(upload_date)s - %(title)s.%(ext)s"
            
            # 2. Xử lý Chất lượng
            if quality == "Tiết kiệm dung lượng (480p)":
                cmd.extend(["-f", "worstvideo[height>=480]+bestaudio/worst"])
                log("📉 Chế độ: Tiết kiệm dung lượng")
            else:
                log("💎 Chế độ: Chất lượng cao nhất (HD/4K)")

            # 3. Xử lý Cookies (Private Video)
            if use_cookies:
                cmd.extend(["--cookies-from-browser", "chrome"])
                log("🍪 Đang dùng Cookies từ Chrome (Để tải video riêng tư/nhóm kín)")

            # Thêm output và link
            cmd.extend(["-o", output_format, link])
            
            # Thêm tùy chọn paths (-P) để lưu vào thư mục mong muốn
            cmd.extend(["-P", save_folder])

            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True,
                cwd=save_folder 
            )

            for line in process.stdout:
                log_area.insert(tk.END, line)
                log_area.see(tk.END)
            
            process.wait()

            if process.returncode == 0:
                messagebox.showinfo("Thành công", f"✅ Tải xong rồi!\nLưu tại: {save_folder}")
                log(f"\n✅ XONG! File đã lưu ở: {save_folder}")
            else:
                log("\n❌ Có lỗi xảy ra.")

        except Exception as e:
            messagebox.showerror("Lỗi", f"Có lỗi: {e}")
        finally:
            btn_download.config(state=tk.NORMAL, text="Tải Ngay 🚀")

    threading.Thread(target=run_process).start()

# --- GIAO DIỆN CHÍNH ---
window = tk.Tk()
window.title("Siêu Tool Tải Video Đa Năng (V3.1)")
window.geometry("700x650")

# Header
tk.Label(window, text="Hỗ trợ: TikTok, YouTube, Facebook (Reels/Private)", font=("Arial", 14, "bold"), fg="#ff0050").pack(pady=10)

# Frame nhập liệu
frame_input = tk.Frame(window)
frame_input.pack(pady=5)
tk.Label(frame_input, text="Link Video/Kênh:", font=("Arial", 11)).pack(side=tk.LEFT)
entry_link = tk.Entry(frame_input, width=50, font=("Arial", 11))
entry_link.pack(side=tk.LEFT, padx=5)

# Frame Chọn thư mục (Mới)
frame_folder = tk.Frame(window)
frame_folder.pack(pady=5)
tk.Label(frame_folder, text="Lưu tại:", font=("Arial", 11)).pack(side=tk.LEFT)
entry_folder = tk.Entry(frame_folder, width=40, font=("Arial", 10))
entry_folder.insert(0, os.getcwd()) 
entry_folder.pack(side=tk.LEFT, padx=5)
btn_browse = tk.Button(frame_folder, text="📂 Chọn Ổ Đĩa", command=chon_thu_muc)
btn_browse.pack(side=tk.LEFT)

# Frame tùy chọn
frame_options = tk.LabelFrame(window, text="Tùy chọn nâng cao", font=("Arial", 10, "bold"))
frame_options.pack(pady=10, padx=20, fill="x")

# Hàng 1
var_mp3 = tk.BooleanVar()
chk_mp3 = tk.Checkbutton(frame_options, text="Chỉ tải nhạc (MP3)", variable=var_mp3, font=("Arial", 10))
chk_mp3.grid(row=0, column=0, padx=20, pady=5, sticky="w")

var_cookies = tk.BooleanVar()
chk_cookies = tk.Checkbutton(frame_options, text="Dùng Cookies Chrome", variable=var_cookies, font=("Arial", 10), fg="blue")
chk_cookies.grid(row=0, column=1, padx=20, pady=5, sticky="w")

# Hàng 2
tk.Label(frame_options, text="Chất lượng:", font=("Arial", 10)).grid(row=1, column=0, padx=20, pady=5, sticky="w")
cmb_quality = ttk.Combobox(frame_options, values=["Chất lượng CAO (HD)", "Tiết kiệm dung lượng (480p)"], state="readonly", width=25)
cmb_quality.current(0)
cmb_quality.grid(row=1, column=0, padx=100, pady=5, sticky="w")

tk.Label(frame_options, text="Hẹn giờ (HH:MM):", font=("Arial", 10)).grid(row=1, column=1, padx=20, pady=5, sticky="w")
entry_schedule = tk.Entry(frame_options, width=10, font=("Arial", 10))
entry_schedule.grid(row=1, column=1, padx=140, pady=5, sticky="w")

# Nút tải
btn_download = tk.Button(window, text="Tải Ngay 🚀", font=("Arial", 12, "bold"), bg="#00b894", fg="black", height=2, width=20, command=tai_video_thread)
btn_download.pack(pady=10)

# Log
log_area = scrolledtext.ScrolledText(window, width=80, height=15, font=("Courier", 10))
log_area.pack(pady=5, padx=20)

tk.Label(window, text="Mẹo: Để tải video Facebook riêng tư, hãy đăng nhập Facebook trên Chrome trước.", font=("Arial", 9, "italic"), fg="gray").pack(pady=5)

window.mainloop()
