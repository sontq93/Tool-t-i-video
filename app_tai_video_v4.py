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

# Constant for hiding console window on Windows
if platform.system() == "Windows":
    SUBPROCESS_FLAGS = subprocess.CREATE_NO_WINDOW
else:
    SUBPROCESS_FLAGS = 0

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

# UX/UI Design System - Premium Desktop Theme
COLORS = {
    'bg_main': '#F8FAFC',       # Slate-50: Background
    'card_bg': '#FFFFFF',       # White: Card background
    'text_primary': '#1E293B',  # Slate-800: Main text
    'text_secondary': '#64748B',# Slate-500: Subtext
    'step_title': '#3B82F6',    # Blue-500: Highlight for Steps
    'primary': '#3B82F6',       # Blue-500: Primary Action
    'primary_hover': '#2563EB', # Blue-600: Primary Hover
    'secondary': '#F1F5F9',     # Slate-100: Secondary Button/Bg
    'secondary_hover': '#E2E8F0', # Slate-200: Secondary Hover
    'border': '#E2E8F0',        # Slate-200: Subtle borders
    'input_bg': '#FFFFFF',
    'input_focus': '#3B82F6',   # Focus ring
    'success': '#10B981',
    'warning': '#F59E0B',
    'error': '#EF4444',
    'white': '#FFFFFF',
    'shadow': '#E2E8F0'         # Simulated shadow color
}

# Typography
SYSTEM_FONT = "Segoe UI" if platform.system() == "Windows" else "Helvetica Neue"
FONTS = {
    'heading': (SYSTEM_FONT, 18, 'bold'),
    'step_title': (SYSTEM_FONT, 15, 'bold'), # Slightly smaller, refined
    'body': (SYSTEM_FONT, 13),
    'body_bold': (SYSTEM_FONT, 13, 'bold'),
    'small': (SYSTEM_FONT, 11),
    'button': (SYSTEM_FONT, 13, 'bold')
} 

# --- UI HELPERS ---
def add_hover(widget, bg_normal, bg_hover):
    """Add simple hover effect to widgets"""
    widget.bind("<Enter>", lambda e: widget.config(bg=bg_hover))
    widget.bind("<Leave>", lambda e: widget.config(bg=bg_normal))

def style_input(entry):
    """Style input fields with focus effect"""
    entry.config(relief="flat", highlightthickness=1, highlightbackground=COLORS['border'], highlightcolor=COLORS['input_focus'], bg=COLORS['input_bg'])

def create_card(parent):
    """Create a standard container card without heavy borders"""
    frame = tk.Frame(parent, bg=COLORS['card_bg'])
    # Optional: Add simulated shadow line at bottom if needed, or just clean white
    return frame 

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
        messagebox.showinfo("Nhắc nhở", "Vui lòng dán link video hoặc kênh vào ô bên dưới trước khi tiếp tục.")
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
            # Check if YouTube Channel to scan both Videos and Shorts
            # Exclude youtu.be (short links for single videos)
            is_youtube_channel = ("youtube.com" in link) and ("youtu.be" not in link)
            
            # Simple heuristic: if it has @username or /channel/ or /c/ AND is not a specific video
            if is_youtube_channel and ("/videos" not in link and "/shorts" not in link and "watch?v=" not in link):
                log_msg(f"🔍 Phát hiện kênh YouTube, đang quét cả Video và Shorts...")
                
                # 1. Scan Videos
                log_msg(f"⏳ Đang quét danh sách Videos dài...")
                link_videos = link.rstrip("/") + "/videos"
                cmd_v = cmd.copy()
                cmd_v[-1] = link_videos
                
                print(f"DEBUG: Executing {cmd_v}")
                process_v = subprocess.Popen(cmd_v, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='ignore', creationflags=SUBPROCESS_FLAGS)
                stdout_v, stderr_v = process_v.communicate()
                print(f"DEBUG: Videos stdout len={len(stdout_v)}, stderr={stderr_v[:100]}")
                
                # 2. Scan Shorts
                log_msg(f"⏳ Đang quét danh sách Shorts...")
                link_shorts = link.rstrip("/") + "/shorts"
                cmd_s = cmd.copy()
                cmd_s[-1] = link_shorts
                
                print(f"DEBUG: Executing {cmd_s}")
                process_s = subprocess.Popen(cmd_s, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='ignore', creationflags=SUBPROCESS_FLAGS)
                stdout_s, stderr_s = process_s.communicate()
                print(f"DEBUG: Shorts stdout len={len(stdout_s)}, stderr={stderr_s[:100]}")

                # Parse & Merge
                entries = []
                try:
                    if stdout_v.strip():
                        data_v = json.loads(stdout_v)
                        if 'entries' in data_v: 
                            ev = list(data_v['entries'])
                            entries.extend(ev)
                            log_msg(f"   + Tìm thấy {len(ev)} videos dài")
                        else: entries.append(data_v)
                except Exception as e:
                    print(f"DEBUG: Error parsing Videos: {e}")

                try:
                    if stdout_s.strip():
                        data_s = json.loads(stdout_s)
                        if 'entries' in data_s: 
                            shorts = list(data_s['entries'])
                            for s in shorts: s['_is_short'] = True # Tag as short
                            entries.extend(shorts)
                            log_msg(f"   + Tìm thấy {len(shorts)} shorts")
                        else: 
                            data_s['_is_short'] = True
                            entries.append(data_s)
                except Exception as e:
                    print(f"DEBUG: Error parsing Shorts: {e}")
                
                # Fallback if both failed
                if not entries:
                     log_msg("⚠️ Không tìm thấy video/short nào, đang thử quét link gốc...")
                     # entries is empty, so it will trigger the fallback block below
            
            else:
                 entries = [] # Placeholder

            # --- STANDARD SCAN / FALLBACK --- 
            if not entries:
                 log_msg("⏳ Đang quét chi tiết (fallback)...")
                 # Standard execution (re-run for non-channel logic or failed channel logic)
                 process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='ignore', creationflags=SUBPROCESS_FLAGS)
                 stdout, stderr = process.communicate()
                 print(f"DEBUG: Fallback stdout len={len(stdout)}, stderr={stderr[:100]}")
                 
                 # FB Fallback Check
                 if (process.returncode != 0 or not stdout.strip()) and ("facebook.com" in link or "fb.watch" in link):
                     log_msg(f"⚠️ Quét nhanh thất bại, thử quét kỹ (FB)...")
                     cmd_full = [TOOL_PATH, "--dump-single-json", "--no-check-certificate", "--ignore-errors", link]
                     cmd_full.extend(["--user-agent", "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1"])
                     if var_cookies.get(): cmd_full.extend(["--cookies-from-browser", "chrome"])
                     
                     process = subprocess.Popen(cmd_full, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='ignore', creationflags=SUBPROCESS_FLAGS)
                     stdout, stderr = process.communicate()

                 if process.returncode != 0:
                      errMsg = stderr if stderr else "Unknown error"
                      gui_queue.put(lambda: messagebox.showerror("Không quét được", f"Không tìm thấy video.\nLink: {link}\nLỗi: {errMsg[:200]}"))
                      return

                 try:
                    data = json.loads(stdout)
                    if 'entries' in data: entries = list(data['entries'])
                    else: entries = [data]
                 except json.JSONDecodeError:
                     gui_queue.put(lambda: messagebox.showerror("Lỗi dữ liệu", "Không thể đọc thông tin video. Vui lòng kiểm tra lại link."))
                     return

            # Filter empty
            entries = [e for e in entries if e]
            
            if not entries:
                gui_queue.put(lambda: messagebox.showinfo("Thông báo", "Chưa tìm thấy video nào ở link này. Bạn hãy thử link khác nhé!"))
                return

            def update_ui_tree():
                for idx, entry in enumerate(entries, 1):
                    title = entry.get('title', 'No Title')
                    # Check for Shorts tag
                    is_short = entry.get('_is_short', False)
                    # Also check title/url for 'shorts' if not tagged
                    entry_url = entry.get('webpage_url') or entry.get('url') or link
                    if "/shorts/" in entry_url: is_short = True
                    
                    type_str = "[Shorts]" if is_short else "[Video]"
                    display_title = f"{type_str} {title}"
                    
                    # Thêm checkbox vào cột đầu tiên
                    item_id = tree.insert("", "end", values=("☐", idx, display_title, "⏸️ Chưa tải"))
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
            gui_queue.put(lambda: messagebox.showerror("Sự cố", f"Hệ thống gặp vấn đề khi xử lý: {e}"))
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
            messagebox.showinfo("Chưa chọn video", "Bạn chưa chọn video nào. Vui lòng tick chọn ít nhất 1 video trong danh sách.")
            return
        
        if messagebox.askyesno("Tải tất cả?", "Bạn chưa chọn video nào.\nBạn có muốn tải TOÀN BỘ danh sách video này không?"):
            selected_items = all_items
        else:
            return

    save_folder = entry_folder.get().strip()
    if not save_folder:
        save_folder = os.getcwd()

    is_mp3 = var_mp3.get()
    quality = "Best" # Default to best since UI option was removed
    use_cookies = var_cookies.get()
    
    try:
        delay_sec = 0 # Default delay
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
            
        # Quality logic simplified
        # if quality == "Tiết kiệm (480p)": ... 
        
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
                    cwd=save_folder,
                    creationflags=SUBPROCESS_FLAGS
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
             gui_queue.put(lambda: messagebox.showinfo("Tuyệt vời", f"Đã tải xong {success_count}/{total} video! Kiểm tra thư mục lưu nhé."))

    threading.Thread(target=run_download_scheduler, daemon=True).start()

def direct_download_thread():
    """Tải trực tiếp link nhập vào (Bỏ qua bước Quét)"""
    link = entry_link.get().strip()
    if not link:
        messagebox.showinfo("Nhắc nhở", "Vui lòng dán link video cần tải.")
        entry_link.focus()
        return

    if not messagebox.askyesno("Xác nhận", "Chế độ này sẽ tải ngay video từ link (không cần quét danh sách).\n\nBạn có muốn tiếp tục?"):
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
                cwd=save_folder,
                creationflags=SUBPROCESS_FLAGS
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
window.configure(bg=COLORS['bg_main'])

window.after(100, check_queue)

# --- HEADER: CLEAN & SIMPLE ---
frame_header = tk.Frame(window, bg=COLORS['card_bg'], height=60)
frame_header.pack(fill="x")
frame_header.pack_propagate(False)

# Separator Logic (Simulated by a bottom frame)
tk.Frame(window, bg=COLORS['border'], height=1).pack(fill="x")

# Title Left
tk.Label(
    frame_header, 
    text="Video Downloader Pro", 
    font=FONTS['heading'], 
    fg=COLORS['primary'], # Blue Accent
    bg=COLORS['card_bg']
).pack(side=tk.LEFT, padx=30, pady=15)

# Status Right
lbl_status_right = tk.Label(
    frame_header, 
    text="✅ Sẵn sàng sử dụng", 
    font=FONTS['small'], 
    fg=COLORS['success'], 
    bg=COLORS['card_bg']
)
lbl_status_right.pack(side=tk.RIGHT, padx=30, pady=15)

# --- SCROLLABLE CONTAINER CHO TOÀN BỘ APP ---
# Tạo Canvas với scrollbar để có thể scroll toàn bộ nội dung
main_canvas = tk.Canvas(window, bg=COLORS['bg_main'], highlightthickness=0)
main_scrollbar = tk.Scrollbar(window, orient="vertical", command=main_canvas.yview)
scrollable_frame = tk.Frame(main_canvas, bg=COLORS['bg_main'])

# Update scroll region khi frame thay đổi kích thước
def _configure_scroll_region(event):
    main_canvas.configure(scrollregion=main_canvas.bbox("all"))

# Set width của scrollable_frame bằng width của canvas (trừ đi scrollbar)
def _configure_canvas_width(event):
    # Trừ đi bề rộng của scrollbar (khoảng 20px) để tránh hiện scrollbar ngang
    canvas_width = event.width - 4
    main_canvas.itemconfig(canvas_window, width=canvas_width)

scrollable_frame.bind("<Configure>", _configure_scroll_region)
main_canvas.bind("<Configure>", _configure_canvas_width)

canvas_window = main_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
main_canvas.configure(yscrollcommand=main_scrollbar.set)

main_canvas.pack(side="left", fill="both", expand=True)
main_scrollbar.pack(side="right", fill="y")

# Enable mouse wheel scrolling
def _on_mousewheel(event):
    if platform.system() == "Windows":
        main_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    elif platform.system() == "Darwin": # macOS
        # macOS delta is usually smaller/inverted differently. 
        # Often simply -1 * delta works well for 'natural' scrolling perception or just standard units
        main_canvas.yview_scroll(int(-1 * event.delta), "units")
    else:
        # Linux / other
        pass

# Bind global scroll
if platform.system() == "Linux":
    main_canvas.bind_all("<Button-4>", lambda e: main_canvas.yview_scroll(-1, "units"))
    main_canvas.bind_all("<Button-5>", lambda e: main_canvas.yview_scroll(1, "units"))
else:
    main_canvas.bind_all("<MouseWheel>", _on_mousewheel)

# --- HƯỚNG DẪN NHANH ---
# Container Padding Wrapper
frame_guide_container = tk.Frame(scrollable_frame, bg=COLORS['bg_main'])
frame_guide_container.pack(fill="x", padx=30, pady=(24, 0))

frame_guide = create_card(frame_guide_container)
frame_guide.pack(fill="x")

tk.Label(
    frame_guide,
    text="💡 Hướng dẫn nhanh",
    font=FONTS['step_title'],
    bg=COLORS['card_bg'],
    fg=COLORS['text_primary']
).pack(anchor="w", padx=24, pady=(20, 5))

guide_text = """• Bước 1: Dán link video vào ô bên dưới.
• Bước 2: Bấm "Quét & tải video" để xem danh sách.
• Tải nhanh: Bấm nút "Tải nhanh" để bỏ qua bước quét."""

tk.Label(
    frame_guide,
    text=guide_text,
    font=FONTS['body'],
    bg=COLORS['card_bg'],
    fg=COLORS['text_secondary'],
    justify="left",
    anchor="w"
).pack(fill="x", padx=24, pady=(0, 20))

# --- BƯỚC 1: NHẬP LINK ---
frame_input_container = tk.Frame(scrollable_frame, bg=COLORS['bg_main'])
frame_input_container.pack(fill="x", padx=30, pady=20)

frame_input_section = create_card(frame_input_container)
frame_input_section.pack(fill="x")

# Step Title
tk.Label(
    frame_input_section,
    text="Bước 1: Dán link video hoặc kênh",
    font=FONTS['step_title'],
    bg=COLORS['card_bg'],
    fg=COLORS['step_title'] # BLUE
).pack(anchor="w", padx=24, pady=(24, 12))

# Link Input
frame_link_container = tk.Frame(frame_input_section, bg=COLORS['card_bg'])
frame_link_container.pack(fill="x", padx=24, pady=(0, 12))

entry_link = tk.Entry(frame_link_container, font=FONTS['body'], fg=COLORS['text_secondary'])
style_input(entry_link) # New Styling
entry_link.pack(fill="x", ipady=10)

# Placeholder logic
def on_entry_click(event):
    if entry_link.get() == "Dán link TikTok / YouTube / Facebook vào đây…":
        entry_link.delete(0, "end")
        entry_link.config(fg=COLORS['text_primary'])

def on_focusout(event):
    if entry_link.get() == "":
        entry_link.insert(0, "Dán link TikTok / YouTube / Facebook vào đây…")
        entry_link.config(fg=COLORS['text_secondary'])

entry_link.insert(0, "Dán link TikTok / YouTube / Facebook vào đây…")
entry_link.bind('<FocusIn>', on_entry_click)
entry_link.bind('<FocusOut>', on_focusout)

# Folder Input
frame_folder_container = tk.Frame(frame_input_section, bg=COLORS['card_bg'])
frame_folder_container.pack(fill="x", padx=24, pady=(0, 24))

tk.Label(frame_folder_container, text="Thư mục:", font=FONTS['body'], bg=COLORS['card_bg'], fg=COLORS['text_primary']).pack(side=tk.LEFT)

entry_folder = tk.Entry(frame_folder_container, font=FONTS['body'], width=30, fg=COLORS['text_primary'])
style_input(entry_folder)
entry_folder.insert(0, os.getcwd())
entry_folder.pack(side=tk.LEFT, fill="x", expand=True, padx=12, ipady=5)

btn_browse = tk.Button(
    frame_folder_container,
    text="Chọn...",
    font=FONTS['small'],
    bg=COLORS['secondary'],
    fg=COLORS['text_primary'],
    relief="flat",
    padx=16, pady=5,
    command=chon_thu_muc,
    cursor="hand2"
)
style_input(btn_browse) # Gives it similar rounding/border if needed, or just hover
add_hover(btn_browse, COLORS['secondary'], COLORS['secondary_hover'])
btn_browse.pack(side=tk.LEFT)

# --- BƯỚC 2: TUỲ CHỌN ---
frame_options_container = tk.Frame(scrollable_frame, bg=COLORS['bg_main'])
frame_options_container.pack(fill="x", padx=30, pady=0)

frame_options_section = create_card(frame_options_container)
frame_options_section.pack(fill="x")

tk.Label(
    frame_options_section,
    text="Bước 2: Tuỳ chọn tải",
    font=FONTS['step_title'],
    bg=COLORS['card_bg'],
    fg=COLORS['step_title'] # BLUE
).pack(anchor="w", padx=24, pady=(24, 12))

frame_opts = tk.Frame(frame_options_section, bg=COLORS['card_bg'])
frame_opts.pack(fill="x", padx=24, pady=(0, 24))

var_mp3 = tk.BooleanVar()
chk_mp3 = tk.Checkbutton(
    frame_opts, text="Chỉ tải âm thanh (MP3)", variable=var_mp3,
    font=FONTS['body'], bg=COLORS['card_bg'], fg=COLORS['text_primary'],
    selectcolor=COLORS['card_bg'], activebackground=COLORS['card_bg'],
    cursor="hand2"
)
chk_mp3.pack(side=tk.LEFT, padx=(0, 24))

var_thumbnail = tk.BooleanVar()
chk_thumbnail = tk.Checkbutton(
    frame_opts, text="Tải ảnh thumbnail", variable=var_thumbnail,
    font=FONTS['body'], bg=COLORS['card_bg'], fg=COLORS['text_primary'],
    selectcolor=COLORS['card_bg'], activebackground=COLORS['card_bg'],
    cursor="hand2"
)
chk_thumbnail.pack(side=tk.LEFT, padx=24)

var_cookies = tk.BooleanVar()
chk_cookies = tk.Checkbutton(
    frame_opts, text="Dùng Cookies", variable=var_cookies,
    font=FONTS['body'], bg=COLORS['card_bg'], fg=COLORS['text_primary'],
    selectcolor=COLORS['card_bg'], activebackground=COLORS['card_bg'],
    cursor="hand2"
)
chk_cookies.pack(side=tk.LEFT, padx=24)


# --- BƯỚC 3: HÀNH ĐỘNG ---
# --- BƯỚC 3: HÀNH ĐỘNG ---
frame_action_container = tk.Frame(scrollable_frame, bg=COLORS['bg_main'])
frame_action_container.pack(fill="x", padx=30, pady=20)

frame_action_section = create_card(frame_action_container)
frame_action_section.pack(fill="x")

tk.Label(
    frame_action_section,
    text="Bước 3: Hành động",
    font=FONTS['step_title'],
    bg=COLORS['card_bg'],
    fg=COLORS['step_title'] # BLUE
).pack(anchor="w", padx=24, pady=(24, 12))

frame_buttons = tk.Frame(frame_action_section, bg=COLORS['card_bg'])
frame_buttons.pack(pady=(0, 24), padx=24, fill="x")

# Buttons Container
frame_btn_row = tk.Frame(frame_buttons, bg=COLORS['card_bg'])
frame_btn_row.pack(anchor="w")

# Primary Button (Blue)
btn_scan = tk.Button(
    frame_btn_row,
    text="🚀 Quét & tải video",
    font=FONTS['button'],
    bg=COLORS['primary'],
    fg=COLORS['white'],
    activebackground=COLORS['primary_hover'],
    activeforeground=COLORS['white'],
    relief="flat",
    borderwidth=0,
    cursor="hand2",
    highlightthickness=0,
    padx=28, pady=12
)
btn_scan.config(command=scan_videos_thread)
add_hover(btn_scan, COLORS['primary'], COLORS['primary_hover'])
btn_scan.pack(side=tk.LEFT, padx=(0, 16))

# Secondary Button
btn_direct_dl = tk.Button(
    frame_btn_row,
    text="⚡ Tải nhanh 1 video",
    font=FONTS['button'],
    bg=COLORS['secondary'],
    fg=COLORS['text_primary'],
    activebackground=COLORS['secondary_hover'],
    activeforeground=COLORS['text_primary'],
    relief="flat",
    borderwidth=0,
    cursor="hand2",
    highlightthickness=0,
    padx=20, pady=12
)
btn_direct_dl.config(command=direct_download_thread)
add_hover(btn_direct_dl, COLORS['secondary'], COLORS['secondary_hover'])
btn_direct_dl.pack(side=tk.LEFT)

# Helper Labels
frame_label_row = tk.Frame(frame_buttons, bg=COLORS['card_bg'])
frame_label_row.pack(pady=5)

# --- DANH SÁCH VIDEO ---
# --- DANH SÁCH VIDEO ---
frame_list_container = tk.Frame(scrollable_frame, bg=COLORS['bg_main'])
frame_list_container.pack(fill="both", expand=True, padx=30, pady=20)

frame_list_section = create_card(frame_list_container)
frame_list_section.pack(fill="both", expand=True)

tk.Label(
    frame_list_section,
    text="Danh sách video",
    font=FONTS['step_title'],
    bg=COLORS['card_bg'],
    fg=COLORS['step_title']
).pack(anchor="w", padx=24, pady=(20, 5))

# Empty State Label
lbl_list_empty = tk.Label(
    frame_list_section,
    text="Chưa có video nào. Dán link và bấm Quét & tải video để bắt đầu.",
    font=FONTS['body'],
    fg=COLORS['text_secondary'],
    bg=COLORS['card_bg']
)
lbl_list_empty.pack(pady=40)

frame_list = tk.Frame(frame_list_section, bg=COLORS['card_bg'])
# Initially hide functionality until data (logic handled in scan fn, but pack here)
frame_list.pack(fill="both", expand=True, padx=24)

# Treeview Styling
style = ttk.Style()
style.theme_use("clam")
style.configure("Treeview",
    background="white",
    foreground=COLORS['text_primary'],
    fieldbackground="white",
    font=FONTS['body'],
    rowheight=40, # Taller rows
    borderwidth=0
)
style.configure("Treeview.Heading",
    background=COLORS['bg_main'],
    foreground=COLORS['text_primary'],
    font=FONTS['body_bold'],
    relief="flat"
)
style.map("Treeview", background=[('selected', COLORS['primary'])])

# Scrollbar dọc - Modern looking if possible, otherwise standard
scrollbar_y = tk.Scrollbar(frame_list, orient="vertical")
scrollbar_y.pack(side=tk.RIGHT, fill="y")

# Scrollbar ngang
scrollbar_x = tk.Scrollbar(frame_list, orient="horizontal")
scrollbar_x.pack(side=tk.BOTTOM, fill="x")

columns = ("check", "idx", "title", "status")
tree = ttk.Treeview(
    frame_list,
    columns=columns,
    show="headings",
    height=12,
    yscrollcommand=scrollbar_y.set,
    xscrollcommand=scrollbar_x.set
)

tree.heading("check", text="Chọn")
tree.column("check", width=60, anchor="center")

tree.heading("idx", text="STT")
tree.column("idx", width=50, anchor="center")

tree.heading("title", text="Tiêu đề Video")
tree.column("title", width=500)

tree.heading("status", text="Trạng thái")
tree.column("status", width=200, anchor="center")

tree.pack(fill="both", expand=True) # Full width inside frame_list

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

# Selection Action Bar
frame_select_btns = tk.Frame(frame_list_section, bg=COLORS['card_bg'])
frame_select_btns.pack(fill="x", pady=(10, 24), padx=24)

btn_sel_all = tk.Button(
    frame_select_btns,
    text="Chọn tất cả",
    command=select_all,
    font=FONTS['small'],
    bg=COLORS['secondary'],
    fg=COLORS['text_primary'],
    relief="flat",
    padx=16, pady=6,
    cursor="hand2"
)
add_hover(btn_sel_all, COLORS['secondary'], COLORS['secondary_hover'])
btn_sel_all.pack(side=tk.LEFT, padx=(0, 10))

btn_desel = tk.Button(
    frame_select_btns,
    text="Bỏ chọn",
    command=deselect_all,
    font=FONTS['small'],
    bg=COLORS['secondary'],
    fg=COLORS['text_primary'],
    relief="flat",
    padx=16, pady=6,
    cursor="hand2"
)
add_hover(btn_desel, COLORS['secondary'], COLORS['secondary_hover'])
btn_desel.pack(side=tk.LEFT, padx=10)

# --- PHẦN 5: ĐIỀU KHIỂN TẢI ---
# --- BƯỚC 4: TIẾN HÀNH TẢI ---
frame_download_container = tk.Frame(scrollable_frame, bg=COLORS['bg_main'])
frame_download_container.pack(fill="x", padx=30, pady=(0, 40))

frame_download_section = create_card(frame_download_container)
frame_download_section.pack(fill="x")

frame_dl_btns = tk.Frame(frame_download_section, bg=COLORS['card_bg'])
frame_dl_btns.pack(pady=24, padx=24, fill="x")

# Main Download Trigger
btn_download = tk.Button(
    frame_dl_btns,
    text="Bắt đầu tải video đã chọn",
    font=FONTS['button'],
    bg=COLORS['success'],
    fg=COLORS['white'],
    activebackground="#059669",
    activeforeground=COLORS['white'],
    relief="flat",
    borderwidth=0,
    cursor="hand2",
    highlightthickness=0,
    padx=25, pady=12,
    command=tai_video_thread
)
add_hover(btn_download, COLORS['success'], "#059669")
btn_download.pack(side=tk.LEFT, expand=True, fill="x", padx=(0, 10))

btn_stop = tk.Button(
    frame_dl_btns,
    text="Dừng lại",
    font=FONTS['button'],
    bg=COLORS['error'],
    fg=COLORS['white'],
    activebackground="#DC2626",
    activeforeground=COLORS['white'],
    relief="flat",
    borderwidth=0,
    cursor="hand2",
    highlightthickness=0,
    padx=25, pady=12,
    command=stop_download,
    state=tk.DISABLED
)
add_hover(btn_stop, COLORS['error'], "#DC2626")
btn_stop.pack(side=tk.LEFT, padx=(10, 0))

# --- STATUS BAR ---
# --- STATUS BAR ---
status_label = tk.Label(
    window,
    text="Sẵn sàng sử dụng",
    font=FONTS['small'],
    bg="#F1F5F9",
    fg=COLORS['text_secondary'],
    bd=0,
    padx=15,
    pady=8,
    anchor="w"
)
status_label.pack(side=tk.BOTTOM, fill="x")

window.mainloop()
