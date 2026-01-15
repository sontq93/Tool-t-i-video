import tkinter as tk
from tkinter import messagebox, scrolledtext, filedialog, ttk
import subprocess
import os
import sys
import threading
import time
import datetime
import platform
import queue
import json
import urllib.request
import re

# Queue để nhận yêu cầu cập nhật giao diện từ luồng khác
gui_queue = queue.Queue()

# Xác định đường dẫn file khi chạy bình thường hoặc khi đã đóng gói (Frozen)
if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
else:
    base_path = os.path.dirname(__file__)

# Tự động chọn tên file tủy theo hệ điều hành đang chạy
tool_name = "yt-dlp.exe" if platform.system() == "Windows" else "yt-dlp"
TOOL_PATH = os.path.join(base_path, tool_name)

# Biến global
current_process = None
is_paused = False
download_thread_running = False
stop_flag = False

# Lưu trữ dữ liệu video sau khi scan
video_data_map = {} 

def check_queue():
    """Hàm kiểm tra hàng đợi để cập nhật giao diện (chạy trên main thread)"""
    try:
        while True:
            task = gui_queue.get_nowait()
            if callable(task):
                task()
    except queue.Empty:
        pass
    finally:
        window.after(100, check_queue)

def update_status(item_id, status_text):
    """Cập nhật trạng thái trong Treeview"""
    gui_queue.put(lambda: tree.set(item_id, "status", status_text))

def log_msg(message):
    """Log tin nhắn vào status bar"""
    print(message) # Debug console
    gui_queue.put(lambda: status_label.config(text=f"{message}"))

def chon_thu_muc():
    folder_selected = filedialog.askdirectory()
    if folder_selected:
        entry_folder.delete(0, tk.END)
        entry_folder.insert(0, folder_selected)

def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "", name)

def save_titles_to_file(folder, videos):
    """Lưu danh sách tiêu đề ra file txt"""
    try:
        path = os.path.join(folder, "titles.txt")
        with open(path, "w", encoding="utf-8") as f:
            for idx, v in enumerate(videos, 1):
                f.write(f"{idx}. {v.get('title', 'Unknown')}\n")
        log_msg(f"📝 Đã lưu titles.txt")
    except Exception as e:
        log_msg(f"❌ Lỗi lưu title: {e}")

def scan_videos_thread():
    """Quét danh sách video từ link"""
    link = entry_link.get().strip()
    if not link:
        messagebox.showwarning("⚠️ Thiếu Link", "Vui lòng nhập link trước khi quét!")
        return
        
    # Auto fix Facebook link
    if "facebook.com" in link or "fb.watch" in link:
        if "videos" not in link and "reels" not in link and "watch" not in link:
            if link.endswith("/"):
                link = link[:-1]
            link += "/videos"
            log_msg(f"ℹ️ Đã tự động đổi link thành: {link}")

    btn_scan.config(state=tk.DISABLED, text="⏳ Đang quét...")
    
    # Xóa dữ liệu cũ
    for item in tree.get_children():
        tree.delete(item)
    video_data_map.clear()

    def run_scan():
        try:
            # CÁCH 1: FAST SCAN (Flat Playlist)
            cmd = [
                TOOL_PATH, 
                "--flat-playlist", 
                "--dump-single-json",
                "--no-check-certificate", 
                "--ignore-errors",
                link
            ]
            
            # UA FIX FOR FACEBOOK
            if "facebook.com" in link or "fb.watch" in link:
                cmd.extend(["--user-agent", "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1"])
            else:
                cmd.extend(["--user-agent", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15"])

            # Check cookies
            if var_cookies.get():
                cmd.extend(["--cookies-from-browser", "chrome"])
            
            log_msg(f"🔍 Đang quét (nhanh): {link[:50]}...")
            
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='ignore')
            stdout, stderr = process.communicate()
            
            # Nếu cách 1 thất bại -> Thử CÁCH 2: FULL SCAN
            if process.returncode != 0 or not stdout.strip():
                log_msg(f"⚠️ Quét nhanh thất bại, thử quét kỹ...")
                
                cmd_full = [
                    TOOL_PATH, 
                    "--dump-single-json",
                    "--no-check-certificate",
                    "--ignore-errors",
                    link
                ]
                
                # UA FIX FOR FACEBOOK (Fallback)
                if "facebook.com" in link or "fb.watch" in link:
                    cmd_full.extend(["--user-agent", "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1"])
                else:
                    cmd_full.extend(["--user-agent", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15"])

                if var_cookies.get():
                    cmd_full.extend(["--cookies-from-browser", "chrome"])
                    
                process = subprocess.Popen(cmd_full, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='ignore')
                stdout, stderr = process.communicate()
                
                if process.returncode != 0:
                    gui_queue.put(lambda: messagebox.showerror("❌ Lỗi Quét", f"Không quét được video.\n\n⚠️ FACEBOOK: Bắt buộc phải đăng nhập Chrome và tick 'Dùng Cookies'.\n\nLỗi: {stderr[:300]}"))
                    return

            try:
                data = json.loads(stdout)
            except json.JSONDecodeError:
                 gui_queue.put(lambda: messagebox.showerror("❌ Lỗi Data", f"Kết quả không hợp lệ.\n{stdout[:300]}"))
                 return
            
            entries = []
            if 'entries' in data:
                entries = list(data['entries'])
            else:
                entries = [data]
            
            entries = [e for e in entries if e]
            
            if not entries:
                gui_queue.put(lambda: messagebox.showinfo("ℹ️ Thông báo", "Không tìm thấy video nào!"))
                return

            def update_ui_tree():
                for idx, entry in enumerate(entries, 1):
                    title = entry.get('title', 'No Title')
                    entry_url = entry.get('webpage_url') or entry.get('url') or link
                    
                    # Thêm checkbox vào cột đầu tiên
                    item_id = tree.insert("", "end", values=("☐", idx, title, "⏸️ Chưa tải"))
                    video_data_map[item_id] = {
                        "url": entry_url,
                        "title": title,
                        "id": entry.get('id'),
                        "original_url": link
                    }
                
                save_folder = entry_folder.get().strip()
                if save_folder and os.path.exists(save_folder):
                    save_titles_to_file(save_folder, entries)
                    
                log_msg(f"✅ Tìm thấy {len(entries)} video")

            gui_queue.put(update_ui_tree)

        except Exception as e:
            gui_queue.put(lambda: messagebox.showerror("❌ Lỗi", f"Lỗi khi quét: {e}"))
        finally:
            gui_queue.put(lambda: btn_scan.config(state=tk.NORMAL, text="🔍 Quét Danh Sách"))

    threading.Thread(target=run_scan, daemon=True).start()

def tai_video_thread():
    """Tải các video đã chọn (có tick checkbox)"""
    global stop_flag, download_thread_running
    
    # Lấy tất cả các item có checkbox được tick (☑)
    selected_items = []
    for item_id in tree.get_children():
        checkbox_state = tree.set(item_id, "check")
        if checkbox_state == "☑":
            selected_items.append(item_id)
    
    if not selected_items:
        all_items = tree.get_children()
        if not all_items:
            messagebox.showwarning("⚠️ Trống", "Vui lòng Quét video trước!")
            return
        
        if messagebox.askyesno("Tải hết?", "Bạn chưa chọn video nào (chưa tick checkbox).\nBạn có muốn tải TOÀN BỘ không?"):
            selected_items = all_items
        else:
            return

    save_folder = entry_folder.get().strip()
    if not save_folder:
        save_folder = os.getcwd()

    is_mp3 = var_mp3.get()
    quality = cmb_quality.get()
    use_cookies = var_cookies.get()
    
    try:
        delay_sec = float(entry_delay.get().strip())
    except ValueError:
        delay_sec = 0
        
    download_images = var_images.get()

    btn_download.config(state=tk.DISABLED, text="⏳ Đang tải...")
    btn_stop.config(state=tk.NORMAL)
    stop_flag = False
    download_thread_running = True

    def run_download_scheduler():
        global stop_flag, download_thread_running
        
        total = len(selected_items)
        success_count = 0
        
        base_cmd = [TOOL_PATH, "--no-check-certificate", "--progress", "--newline"]
        
        if is_mp3:
            base_cmd.extend(["-x", "--audio-format", "mp3"])
            base_cmd.extend(["-o", "%(uploader)s/%(upload_date)s - %(title)s.mp3"])
        else:
            base_cmd.extend(["-o", "%(uploader)s/%(upload_date)s - %(title)s.%(ext)s"])
            
        if quality == "Tiết kiệm (480p)":
            base_cmd.extend(["-f", "worstvideo[height>=480]+bestaudio/worst"])
        
        if use_cookies:
            base_cmd.extend(["--cookies-from-browser", "chrome"])
            
        if download_images:
            base_cmd.extend(["--write-thumbnail", "--convert-thumbnails", "jpg"])

        base_cmd.extend(["-P", save_folder])
        base_cmd.extend(["--user-agent", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15"])

        for i, item_id in enumerate(selected_items):
            if stop_flag:
                break
                
            data = video_data_map.get(item_id)
            if not data: continue
            
            video_url = data['url']
            
            update_status(item_id, "⏳ Đang tải...")
            tree.see(item_id)
            
            cmd = base_cmd.copy()
            cmd.append(video_url)
            
            try:
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    universal_newlines=True,
                    cwd=save_folder
                )
                
                for line in process.stdout:
                    if stop_flag:
                        process.terminate()
                        break
                    
                    match = re.search(r'(\d+\.\d+)%', line)
                    if match:
                        percent = match.group(1)
                        update_status(item_id, f"⬇️ {percent}%")
                
                process.wait()
                
                if process.returncode == 0:
                    update_status(item_id, "✅ Xong")
                    success_count += 1
                else:
                    if stop_flag:
                        update_status(item_id, "⏹️ Đã dừng")
                    else:
                        update_status(item_id, "❌ Lỗi")
            
            except Exception as e:
                update_status(item_id, f"❌ Lỗi")
            
            if i < total - 1 and not stop_flag:
                if delay_sec > 0:
                    update_status(selected_items[i+1], f"💤 Đợi {delay_sec}s...")
                    for _ in range(int(delay_sec * 10)):
                        if stop_flag: break
                        time.sleep(0.1)

        gui_queue.put(lambda: btn_download.config(state=tk.NORMAL, text="🚀 Tải Đã Chọn"))
        gui_queue.put(lambda: btn_stop.config(state=tk.DISABLED))
        
        if success_count == total:
             gui_queue.put(lambda: messagebox.showinfo("✅ Hoàn tất", f"Đã tải xong {success_count}/{total} video!"))

    threading.Thread(target=run_download_scheduler, daemon=True).start()

def direct_download_thread():
    """Tải trực tiếp link nhập vào (Bỏ qua bước Quét)"""
    link = entry_link.get().strip()
    if not link:
        messagebox.showwarning("⚠️ Thiếu Link", "Vui lòng nhập link cần tải!")
        entry_link.focus()
        return

    if not messagebox.askyesno("⚡ Tải Trực Tiếp", "Chế độ này tải NGAY video từ Link\n(Không qua bảng danh sách)\n\n✅ Dùng khi:\n• Quét bị lỗi\n• Chỉ muốn tải 1 video\n• Link Facebook công khai\n\nTiếp tục?"):
        return

    save_folder = entry_folder.get().strip()
    if not save_folder:
        save_folder = os.getcwd()

    is_mp3 = var_mp3.get()
    quality = cmb_quality.get()
    use_cookies = var_cookies.get()
    download_images = var_images.get()
    
    global stop_flag
    btn_direct_dl.config(state=tk.DISABLED, text="⏳ Đang tải...")
    btn_stop.config(state=tk.NORMAL)
    stop_flag = False
    
    def run():
        try:
            log_msg(f"🚀 Bắt đầu tải trực tiếp...")
            
            cmd = [TOOL_PATH, "--no-check-certificate", "--progress", "--newline"]
            
            is_facebook = "facebook.com" in link or "fb.watch" in link
            
            if is_mp3:
                cmd.extend(["-x", "--audio-format", "mp3"])
                cmd.extend(["-o", "%(uploader)s/%(upload_date)s - %(title)s.mp3"])
            else:
                cmd.extend(["-o", "%(uploader)s/%(upload_date)s - %(title)s.%(ext)s"])
                
            if quality == "Tiết kiệm (480p)":
                cmd.extend(["-f", "worstvideo[height>=480]+bestaudio/worst"])
            
            if use_cookies:
                log_msg("⚠️ Lưu ý: Hãy TẮT Chrome để đọc Cookies!")
                cmd.extend(["--cookies-from-browser", "chrome"])
            
            if download_images:
                cmd.extend(["--write-thumbnail", "--convert-thumbnails", "jpg"])
                
            cmd.extend(["-P", save_folder])
            
            if is_facebook:
                cmd.extend(["--user-agent", "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1"])
            else:
                cmd.extend(["--user-agent", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15"])
            
            cmd.append(link)
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                universal_newlines=True,
                cwd=save_folder
            )
            
            for line in process.stdout:
                if stop_flag:
                    process.terminate()
                    break
                
                line = line.strip()
                if line:
                    if "[download]" in line:
                        match = re.search(r'(\d+\.\d+)%', line)
                        if match:
                            log_msg(f"⬇️ {match.group(1)}%")
                    else:
                        print(line)

            process.wait()
            
            if process.returncode == 0:
                gui_queue.put(lambda: messagebox.showinfo("✅ Thành công", f"Đã tải xong!\nLưu tại: {save_folder}"))
                log_msg("✅ Hoàn tất")
            else:
                if stop_flag:
                    log_msg("⏹️ Đã dừng")
                else:
                    gui_queue.put(lambda: messagebox.showerror("❌ Lỗi", "Có lỗi xảy ra.\n\n💡 Thử:\n• Tick 'Dùng Cookies' và đăng nhập FB/Chrome\n• Kiểm tra link có đúng không"))
                    log_msg("❌ Lỗi")

        except Exception as e:
            gui_queue.put(lambda: messagebox.showerror("❌ Lỗi", f"{e}"))
        finally:
            gui_queue.put(lambda: btn_direct_dl.config(state=tk.NORMAL, text="⚡ Tải Thẳng"))
            gui_queue.put(lambda: btn_stop.config(state=tk.DISABLED))

    threading.Thread(target=run, daemon=True).start()

def stop_download():
    global stop_flag
    stop_flag = True
    btn_stop.config(text="⏹️ Đang dừng...", state=tk.DISABLED)

# =============================================================================
# GUI SETUP
# =============================================================================
window = tk.Tk()
window.title("📥 TikTok/Facebook/YouTube Downloader Pro V5.0")
window.geometry("1000x880")
window.configure(bg="#f0f0f0")

window.after(100, check_queue)

# --- HEADER: TIÊU ĐỀ ---
frame_header = tk.Frame(window, bg="#2c3e50", height=60)
frame_header.pack(fill="x", padx=0, pady=0)
frame_header.pack_propagate(False)

tk.Label(
    frame_header, 
    text="📥 Video Downloader Pro", 
    font=("Arial", 18, "bold"), 
    fg="white", 
    bg="#2c3e50"
).pack(pady=5)

tk.Label(
    frame_header, 
    text="✅ TikTok & YouTube | ⚠️ Facebook cần đăng nhập", 
    font=("Arial", 10), 
    fg="#ecf0f1", 
    bg="#2c3e50"
).pack()

# --- HƯỚNG DẪN SỬ DỤNG ---
frame_guide = tk.LabelFrame(
    window, 
    text="📖 HƯỚNG DẪN SỬ DỤNG NHANH", 
    font=("Arial", 11, "bold"), 
    bg="#fff3cd",
    fg="#856404",
    padx=15,
    pady=8
)
frame_guide.pack(fill="x", padx=15, pady=(10, 5))

guide_text = """
✅ TikTok & YouTube: Hoạt động tốt, không cần đăng nhập
⚠️ Facebook: CẦN đăng nhập Chrome và tick "Dùng Cookies"

📝 CÁCH SỬ DỤNG:
1️⃣ Nhập link video/kênh vào ô "Link"
2️⃣ Chọn thư mục lưu file (hoặc để mặc định)
3️⃣ Tùy chỉnh: MP3, Chất lượng, Cookies (nếu cần)
4️⃣ Nhấn "🔍 Quét Danh Sách" để xem tất cả video
5️⃣ Tick chọn video muốn tải (hoặc "✅ Chọn Tất Cả")
6️⃣ Nhấn "🚀 Tải Đã Chọn" để bắt đầu tải

⚡ TẢI NHANH: Nhấn "⚡ Tải Thẳng" để tải 1 video ngay (không cần quét)
"""

tk.Label(
    frame_guide, 
    text=guide_text.strip(),
    font=("Arial", 9),
    bg="#fff3cd",
    fg="#000000",
    justify="left",
    anchor="w"
).pack(fill="x")

# --- PHẦN 1: NHẬP LINK ---
frame_input_section = tk.LabelFrame(
    window, 
    text="📌 BƯỚC 1: Nhập Link Video/Kênh", 
    font=("Arial", 11, "bold"), 
    bg="#ecf0f1",
    fg="#34495e",
    padx=10,
    pady=10
)
frame_input_section.pack(fill="x", padx=15, pady=(10, 5))

frame_link = tk.Frame(frame_input_section, bg="#ecf0f1")
frame_link.pack(fill="x", pady=5)
tk.Label(frame_link, text="Link:", font=("Arial", 10, "bold"), bg="#ecf0f1").pack(side=tk.LEFT, padx=5)
entry_link = tk.Entry(frame_link, font=("Arial", 11), width=70)
entry_link.pack(side=tk.LEFT, fill="x", expand=True, padx=5)

frame_folder = tk.Frame(frame_input_section, bg="#ecf0f1")
frame_folder.pack(fill="x", pady=5)
tk.Label(frame_folder, text="Lưu tại:", font=("Arial", 10, "bold"), bg="#ecf0f1").pack(side=tk.LEFT, padx=5)
entry_folder = tk.Entry(frame_folder, font=("Arial", 10), width=60)
entry_folder.insert(0, os.getcwd())
entry_folder.pack(side=tk.LEFT, fill="x", expand=True, padx=5)
tk.Button(
    frame_folder, 
    text="📂 Chọn", 
    command=chon_thu_muc, 
    bg="#bdc3c7",  # Xám sáng hơn
    fg="#000000",  # Chữ đen
    font=("Arial", 10, "bold"),
    relief="raised",
    borderwidth=2,
    cursor="hand2",
    activebackground="#95a5a6",
    activeforeground="#000000"  # Chữ đen khi hover
).pack(side=tk.LEFT, padx=5)

# --- PHẦN 2: TÙY CHỌN ---
frame_options_section = tk.LabelFrame(
    window, 
    text="⚙️ BƯỚC 2: Cài Đặt Tùy Chọn", 
    font=("Arial", 11, "bold"), 
    bg="#ecf0f1",
    fg="#34495e",
    padx=10,
    pady=10
)
frame_options_section.pack(fill="x", padx=15, pady=5)

# Row 1
frame_opt_r1 = tk.Frame(frame_options_section, bg="#ecf0f1")
frame_opt_r1.pack(fill="x", pady=3)

var_mp3 = tk.BooleanVar()
tk.Checkbutton(frame_opt_r1, text="🎵 Chỉ tải MP3", variable=var_mp3, font=("Arial", 10), bg="#ecf0f1").pack(side=tk.LEFT, padx=15)

var_cookies = tk.BooleanVar()
tk.Checkbutton(frame_opt_r1, text="🍪 Dùng Cookies (Chrome)", variable=var_cookies, font=("Arial", 10, "bold"), fg="#e74c3c", bg="#ecf0f1").pack(side=tk.LEFT, padx=15)

var_images = tk.BooleanVar()
tk.Checkbutton(frame_opt_r1, text="📸 Tải Thumbnail", variable=var_images, font=("Arial", 10), bg="#ecf0f1").pack(side=tk.LEFT, padx=15)

# Row 2
frame_opt_r2 = tk.Frame(frame_options_section, bg="#ecf0f1")
frame_opt_r2.pack(fill="x", pady=3)

tk.Label(frame_opt_r2, text="Chất lượng:", font=("Arial", 10), bg="#ecf0f1").pack(side=tk.LEFT, padx=15)
cmb_quality = ttk.Combobox(frame_opt_r2, values=["HD/Best", "Tiết kiệm (480p)"], state="readonly", width=18, font=("Arial", 9))
cmb_quality.current(0)
cmb_quality.pack(side=tk.LEFT, padx=5)

tk.Label(frame_opt_r2, text="Delay (giây):", font=("Arial", 10), bg="#ecf0f1", fg="#d35400").pack(side=tk.LEFT, padx=(30, 5))
entry_delay = tk.Entry(frame_opt_r2, width=8, font=("Arial", 10))
entry_delay.insert(0, "0")
entry_delay.pack(side=tk.LEFT)
tk.Label(frame_opt_r2, text="(tùy chỉnh)", font=("Arial", 8), fg="gray", bg="#ecf0f1").pack(side=tk.LEFT, padx=3)

# --- PHẦN 3: HÀNH ĐỘNG ---
frame_action_section = tk.LabelFrame(
    window, 
    text="🎬 BƯỚC 3: Chọn Hành Động", 
    font=("Arial", 11, "bold"), 
    bg="#ecf0f1",
    fg="#34495e",
    padx=10,
    pady=10
)
frame_action_section.pack(fill="x", padx=15, pady=5)

frame_buttons = tk.Frame(frame_action_section, bg="#ecf0f1")
frame_buttons.pack(pady=10)

# Row 1: Buttons
frame_btn_row = tk.Frame(frame_buttons, bg="#ecf0f1")
frame_btn_row.pack()

btn_scan = tk.Button(
    frame_btn_row, 
    text="🔍 Quét Danh Sách", 
    font=("Arial", 13, "bold"), 
    bg="#27ae60", 
    fg="#000000",  # Chữ đen
    activebackground="#1e8449",
    activeforeground="#000000",  # Chữ đen khi hover
    relief="raised",
    borderwidth=3,
    cursor="hand2",
    highlightthickness=0,
    height=2, 
    width=18, 
    command=scan_videos_thread
)
btn_scan.pack(side=tk.LEFT, padx=10)

btn_direct_dl = tk.Button(
    frame_btn_row, 
    text="⚡ Tải Thẳng", 
    font=("Arial", 13, "bold"), 
    bg="#2874a6", 
    fg="#000000",  # Chữ đen
    activebackground="#1a5276",
    activeforeground="#000000",  # Chữ đen khi hover
    relief="raised",
    borderwidth=3,
    cursor="hand2",
    highlightthickness=0,
    height=2, 
    width=18, 
    command=direct_download_thread
)
btn_direct_dl.pack(side=tk.LEFT, padx=10)

# Row 2: Labels
frame_label_row = tk.Frame(frame_buttons, bg="#ecf0f1")
frame_label_row.pack(pady=5)

tk.Label(
    frame_label_row, 
    text="(Quét link → Chọn video → Tải)", 
    font=("Arial", 9), 
    fg="#27ae60", 
    bg="#ecf0f1"
).pack(side=tk.LEFT, padx=88)

tk.Label(
    frame_label_row, 
    text="(Tải ngay 1 video, không quét)", 
    font=("Arial", 9), 
    fg="#2874a6", 
    bg="#ecf0f1"
).pack(side=tk.LEFT, padx=88)

# --- PHẦN 4: DANH SÁCH VIDEO ---
frame_list_section = tk.LabelFrame(
    window, 
    text="📋 DANH SÁCH VIDEO (Sau khi Quét)", 
    font=("Arial", 11, "bold"), 
    bg="#ecf0f1",
    fg="#34495e",
    padx=10,
    pady=5
)
frame_list_section.pack(fill="both", expand=True, padx=15, pady=5)

frame_list = tk.Frame(frame_list_section, bg="#ecf0f1")
frame_list.pack(fill="both", expand=True)

scrollbar_y = tk.Scrollbar(frame_list)
scrollbar_y.pack(side=tk.RIGHT, fill="y")
scrollbar_x = tk.Scrollbar(frame_list, orient="horizontal")
scrollbar_x.pack(side=tk.BOTTOM, fill="x")

columns = ("check", "idx", "title", "status")
tree = ttk.Treeview(frame_list, columns=columns, show="headings", yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)

tree.heading("check", text="✓")
tree.column("check", width=40, anchor="center")

tree.heading("idx", text="#")
tree.column("idx", width=50, anchor="center")

tree.heading("title", text="Tiêu Đề Video")
tree.column("title", width=550)

tree.heading("status", text="Trạng Thái / Tiến Độ")
tree.column("status", width=200, anchor="center")

tree.pack(fill="both", expand=True)

scrollbar_y.config(command=tree.yview)
scrollbar_x.config(command=tree.xview)

# Toggle checkbox khi click
def toggle_checkbox(event):
    """Toggle checkbox khi user click vào row"""
    region = tree.identify("region", event.x, event.y)
    if region == "cell":
        item = tree.identify_row(event.y)
        if item:
            current = tree.set(item, "check")
            new_state = "☑" if current == "☐" else "☐"
            tree.set(item, "check", new_state)

tree.bind("<Button-1>", toggle_checkbox)

# Selection helpers
def select_all():
    for item in tree.get_children():
        tree.set(item, "check", "☑")

def deselect_all():
    for item in tree.get_children():
        tree.set(item, "check", "☐")

frame_select_btns = tk.Frame(frame_list_section, bg="#ecf0f1")
frame_select_btns.pack(fill="x", pady=5)

tk.Button(
    frame_select_btns, 
    text="✅ Chọn Tất Cả", 
    command=select_all, 
    font=("Arial", 10, "bold"), 
    bg="#d5dbdb",  # Xám sáng
    fg="#1c2833",  # Chữ đen
    activebackground="#aeb6bf",
    activeforeground="#1c2833",
    relief="raised",
    borderwidth=2,
    cursor="hand2"
).pack(side=tk.LEFT, padx=8)

tk.Button(
    frame_select_btns, 
    text="❌ Bỏ Chọn", 
    command=deselect_all, 
    font=("Arial", 10, "bold"), 
    bg="#d5dbdb",  # Xám sáng
    fg="#1c2833",  # Chữ đen
    activebackground="#aeb6bf",
    activeforeground="#1c2833",
    relief="raised",
    borderwidth=2,
    cursor="hand2"
).pack(side=tk.LEFT, padx=8)

# --- PHẦN 5: ĐIỀU KHIỂN TẢI ---
frame_download_section = tk.LabelFrame(
    window, 
    text="🎯 ĐIỀU KHIỂN TẢI", 
    font=("Arial", 11, "bold"), 
    bg="#ecf0f1",
    fg="#34495e",
    padx=10,
    pady=10
)
frame_download_section.pack(fill="x", padx=15, pady=5)

frame_dl_btns = tk.Frame(frame_download_section, bg="#ecf0f1")
frame_dl_btns.pack(pady=5)

btn_download = tk.Button(
    frame_dl_btns, 
    text="🚀 Tải Đã Chọn", 
    font=("Arial", 13, "bold"), 
    bg="#f39c12",  # Màu cam
    fg="#000000",  # Chữ đen
    activebackground="#e67e22",
    activeforeground="#000000",  # Chữ đen khi hover
    relief="raised",
    borderwidth=3,
    cursor="hand2",
    highlightthickness=0,
    height=2, 
    width=18, 
    command=tai_video_thread
)
btn_download.pack(side=tk.LEFT, padx=10)

btn_stop = tk.Button(
    frame_dl_btns, 
    text="⏹️ Dừng Lại", 
    font=("Arial", 13, "bold"), 
    bg="#e74c3c",  # Màu đỏ
    fg="#000000",  # Chữ đen
    activebackground="#c0392b",
    activeforeground="#000000",  # Chữ đen khi hover
    relief="raised",
    borderwidth=3,
    cursor="hand2",
    highlightthickness=0,
    height=2, 
    width=18, 
    command=stop_download, 
    state=tk.DISABLED
)
btn_stop.pack(side=tk.LEFT, padx=12)

# --- STATUS BAR ---
status_label = tk.Label(
    window, 
    text="✅ Sẵn sàng - Hỗ trợ TikTok ✅ | YouTube ✅ | Facebook ⚠️ (cần login)", 
    bd=1, 
    relief=tk.SUNKEN, 
    anchor="w",
    font=("Arial", 9),
    bg="#34495e",
    fg="white"
)
status_label.pack(side=tk.BOTTOM, fill="x")

window.mainloop()
