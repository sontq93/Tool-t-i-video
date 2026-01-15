import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image
import threading
import queue
import time
import os
import sys
import subprocess
import json
import platform
import re
import urllib.request

# --- CONSTANTS & CONFIG ---
ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")

# Colors from Mockup (Tailwind approximations)
COLORS = {
    "bg_main": "#F8FAFC",       # slate-50
    "bg_sidebar": "#FFFFFF",    # white
    "text_primary": "#1E293B",  # slate-800
    "text_secondary": "#64748B",# slate-500
    "blue_primary": "#2563EB",  # blue-600
    "blue_hover": "#1D4ED8",    # blue-700
    "blue_light_bg": "#EFF6FF", # blue-50
    "green_success": "#16A34A", # green-600
    "green_hover": "#15803D",   # green-700
    "green_light_bg": "#DCFCE7",# green-100
    "border": "#E2E8F0",        # slate-200
    "input_bg": "#F8FAFC",      # Input background
    "white": "#FFFFFF",
    "red_error": "#EF4444",
}


# Determine tool path (yt-dlp)
if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
else:
    base_path = os.path.dirname(__file__)

tool_name = "yt-dlp.exe" if platform.system() == "Windows" else "yt-dlp"
TOOL_PATH = os.path.join(base_path, tool_name)
SUBPROCESS_FLAGS = subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0

class VideoDownloaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Window Config
        self.title("Video Downloader Pro v5.0")
        self.geometry("1100x700")
        self.configure(fg_color=COLORS["bg_main"])  # App background

        # Data & State
        self.gui_queue = queue.Queue()
        self.video_data_map = {}
        self.stop_flag = False
        self.download_thread_running = False

        # --- LAYOUT GRID ---
        self.grid_columnconfigure(0, weight=0, minsize=400) # Sidebar Fixed
        self.grid_columnconfigure(1, weight=1)              # Main Content Flexible
        self.grid_rowconfigure(0, weight=1)

        # --- LEFT SIDEBAR ---
        self.sidebar = ctk.CTkFrame(self, fg_color=COLORS["bg_sidebar"], corner_radius=0, width=400)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False) # Strict width

        self.setup_sidebar()

        # --- RIGHT CONTENT ---
        self.main_area = ctk.CTkFrame(self, fg_color=COLORS["bg_main"], corner_radius=0)
        self.main_area.grid(row=0, column=1, sticky="nsew")
        self.main_area.grid_rowconfigure(1, weight=1) # List area expands
        self.main_area.grid_columnconfigure(0, weight=1)

        self.setup_main_area()

        # Check Queue Loop
        self.check_queue()

    def setup_sidebar(self):
        # 1. Header
        header_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent", height=100)
        header_frame.pack(fill="x", padx=24, pady=24)
        
        # Icon (Blue Box)
        icon_box = ctk.CTkButton(header_frame, text="⬇", width=48, height=48, 
                                 fg_color=COLORS["blue_primary"], 
                                 hover_color=COLORS["blue_primary"],
                                 font=("Arial", 20, "bold"),
                                 corner_radius=10, state="disabled", text_color_disabled="white")
        icon_box.pack(side="left")
        
        title_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_frame.pack(side="left", padx=(12, 0))
        
        ctk.CTkLabel(title_frame, text="Video Downloader", 
                     font=("Segoe UI" if platform.system() == "Windows" else "Helvetica Neue", 18, "bold"), 
                     text_color=COLORS["text_primary"]).pack(anchor="w")
        ctk.CTkLabel(title_frame, text="Pro Version 5.0", 
                     font=("Arial", 12), text_color=COLORS["text_secondary"]).pack(anchor="w")

        # 2. Controls Area (Scrollable to fit inputs + options)
        controls = ctk.CTkScrollableFrame(self.sidebar, fg_color="transparent")
        controls.pack(fill="both", expand=True, padx=0, pady=0)
        self.controls_scroll = controls

        controls_inner = ctk.CTkFrame(controls, fg_color="transparent")
        controls_inner.pack(fill="both", expand=True, padx=24, pady=12)

        # --- INPUT: URL ---
        ctk.CTkLabel(controls_inner, text="Nguồn Video / Kênh", 
                     font=("Arial", 13, "bold"), text_color=COLORS["text_primary"]).pack(anchor="w", pady=(0, 8))
        
        # Input Group
        url_group = ctk.CTkFrame(controls_inner, fg_color=COLORS["bg_main"], 
                                 border_color=COLORS["border"], border_width=1, corner_radius=12)
        url_group.pack(fill="x", pady=(0, 4))
        
        self.entry_link = ctk.CTkEntry(url_group, placeholder_text="Dán link video hoặc kênh vào đây...",
                                       height=45, corner_radius=12, border_width=0,
                                       fg_color="transparent", text_color=COLORS["text_primary"])
        self.entry_link.pack(fill="x", padx=10, pady=2)
        
        ctk.CTkLabel(controls_inner, text="Hỗ trợ: YouTube, TikTok, Facebook", 
                     font=("Arial", 11), text_color=COLORS["text_secondary"]).pack(anchor="w", pady=(0, 20))


        # --- INPUT: FOLDER ---
        ctk.CTkLabel(controls_inner, text="Lưu tại", 
                     font=("Arial", 13, "bold"), text_color=COLORS["text_primary"]).pack(anchor="w", pady=(0, 8))
        
        folder_group = ctk.CTkFrame(controls_inner, fg_color="transparent")
        folder_group.pack(fill="x", pady=(0, 20))
        
        self.entry_folder = ctk.CTkEntry(folder_group, height=42, corner_radius=10, 
                                         border_color=COLORS["border"], fg_color=COLORS["bg_main"],
                                         text_color=COLORS["text_secondary"])
        self.entry_folder.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.entry_folder.insert(0, os.getcwd())
        
        btn_browse = ctk.CTkButton(folder_group, text="Chọn", width=70, height=42,
                                   fg_color=COLORS["white"], text_color=COLORS["text_secondary"],
                                   border_width=1, border_color=COLORS["border"], corner_radius=10,
                                   hover_color=COLORS["bg_main"], command=self.choose_folder)
        btn_browse.pack(side="right")
        
        # --- SEPARATOR ---
        ctk.CTkFrame(controls_inner, height=1, fg_color=COLORS["border"]).pack(fill="x", pady=(0, 20))

        # --- OPTIONS (CARDS) ---
        ctk.CTkLabel(controls_inner, text="Tùy chọn tải về", 
                     font=("Arial", 13, "bold"), text_color=COLORS["text_primary"]).pack(anchor="w", pady=(0, 12))
        
        def create_option_card(parent, title, subtitle, variable, checked=False):
            # Card Frame
            card = ctk.CTkFrame(parent, fg_color="transparent", border_width=1, border_color=COLORS["border"], corner_radius=12)
            card.pack(fill="x", pady=(0, 10))
            
            chk = ctk.CTkCheckBox(card, text="", variable=variable, 
                                  checkbox_width=20, checkbox_height=20, border_width=2,
                                  fg_color=COLORS["blue_primary"], hover_color=COLORS["blue_primary"],
                                  corner_radius=4, width=30)
            chk.pack(side="left", padx=(12, 0), pady=12)
            
            if checked: variable.set(True)

            text_frame = ctk.CTkFrame(card, fg_color="transparent")
            text_frame.pack(side="left", fill="both", expand=True, pady=10)
            
            ctk.CTkLabel(text_frame, text=title, font=("Arial", 13, "bold"), text_color=COLORS["text_primary"]).pack(anchor="w")
            ctk.CTkLabel(text_frame, text=subtitle, font=("Arial", 11), text_color=COLORS["text_secondary"]).pack(anchor="w")
            
            # Hover effects
            def on_enter(e): card.configure(border_color=COLORS["blue_primary"], fg_color=COLORS["blue_light_bg"])
            def on_leave(e): card.configure(border_color=COLORS["border"], fg_color="transparent")
            card.bind("<Enter>", on_enter)
            card.bind("<Leave>", on_leave)
            
            return chk
        
        self.var_mp3 = ctk.BooleanVar(value=False)
        self.chk_mp3 = create_option_card(controls_inner, "Chỉ tải âm thanh (MP3)", "Convert video sang file audio", self.var_mp3)
        
        self.var_thumb = ctk.BooleanVar(value=True)
        self.chk_thumb = create_option_card(controls_inner, "Tải Thumbnail", "Lưu ảnh bìa chất lượng cao", self.var_thumb, checked=True)
        
        self.var_cookies = ctk.BooleanVar(value=False)
        self.chk_cookies = create_option_card(controls_inner, "Sử dụng Cookies", "Dùng cho video riêng tư/hạn chế", self.var_cookies)

        # 3. Footer Actions (Scan & Fast DL)
        # We pack this into self.sidebar BOTTOM so it stays fixed
        actions_panel = ctk.CTkFrame(self.sidebar, fg_color=COLORS["blue_light_bg"], height=140, corner_radius=0)
        # Separator top
        ctk.CTkFrame(actions_panel, height=1, fg_color=COLORS["border"]).pack(fill="x", side="top")
        actions_panel.pack(fill="x", side="bottom")

        actions_inner = ctk.CTkFrame(actions_panel, fg_color="transparent")
        actions_inner.pack(padx=24, pady=24, fill="both", expand=True)

        self.btn_scan = ctk.CTkButton(actions_inner, text="Quét & Lấy Danh Sách", 
                                      height=50, corner_radius=12,
                                      fg_color=COLORS["blue_primary"], hover_color=COLORS["blue_hover"],
                                      font=("Arial", 15, "bold"), command=self.start_scan_thread)
        self.btn_scan.pack(fill="x", pady=(0, 12))

        self.btn_fast_dl = ctk.CTkButton(actions_inner, text="Tải Nhanh (Bỏ qua list)", 
                                         height=48, corner_radius=12,
                                         fg_color=COLORS["white"], text_color=COLORS["text_secondary"],
                                         border_width=1, border_color=COLORS["border"],
                                         hover_color=COLORS["bg_main"], font=("Arial", 14, "bold"),
                                         command=self.start_direct_download)
        self.btn_fast_dl.pack(fill="x")

    def create_checkbox(self, parent, title, subtitle, variable):
        # Simulated Card Checkbox
        card = ctk.CTkFrame(parent, fg_color="transparent", border_width=1, border_color=COLORS["border"], corner_radius=8)
        
        chk = ctk.CTkCheckBox(card, text="", variable=variable, 
                              width=24, height=24, checkbox_width=24, checkbox_height=24,
                              border_width=2, corner_radius=4,
                              fg_color=COLORS["blue_primary"], hover_color=COLORS["blue_primary"])
        chk.pack(side="left", padx=12, pady=12)
        
        info = ctk.CTkFrame(card, fg_color="transparent")
        info.pack(side="left", fill="both", expand=True, pady=10)
        
        ctk.CTkLabel(info, text=title, font=("Arial", 13, "bold"), text_color=COLORS["text_primary"]).pack(anchor="w")
        ctk.CTkLabel(info, text=subtitle, font=("Arial", 11), text_color=COLORS["text_secondary"]).pack(anchor="w")
        
        return card

    def setup_main_area(self):
        # 1. Top Bar
        top_bar = ctk.CTkFrame(self.main_area, fg_color=COLORS["white"], height=88, corner_radius=0)
        top_bar.grid(row=0, column=0, sticky="ew")
        top_bar.pack_propagate(False)
        
        ctk.CTkFrame(self.main_area, height=1, fg_color=COLORS["border"]).grid(row=0, column=0, sticky="sew")

        info_frame = ctk.CTkFrame(top_bar, fg_color="transparent")
        info_frame.pack(side="left", padx=32, pady=20)
        
        ctk.CTkLabel(info_frame, text="Danh sách Video", 
                     font=("Arial", 20, "bold"), text_color=COLORS["text_primary"]).pack(anchor="w")
        
        self.lbl_count = ctk.CTkLabel(info_frame, text="Đã tìm thấy 0 video từ liên kết", 
                                      font=("Arial", 13), text_color=COLORS["text_secondary"])
        self.lbl_count.pack(anchor="w")

        # Status Pill
        status_frame = ctk.CTkFrame(top_bar, fg_color=COLORS["green_light_bg"], corner_radius=20)
        status_frame.pack(side="right", padx=32)
        ctk.CTkLabel(status_frame, text="●  Sẵn sàng sử dụng", 
                     font=("Arial", 12, "bold"), text_color=COLORS["green_success"], padx=16, pady=6).pack()


        # 2. Table Header
        header_row = ctk.CTkFrame(self.main_area, fg_color=COLORS["bg_main"], height=50, corner_radius=0)
        header_row.grid(row=1, column=0, sticky="ew")
        header_row.pack_propagate(False)
        
        h_chk_frame = ctk.CTkFrame(header_row, width=60, fg_color="transparent")
        h_chk_frame.pack(side="left", fill="y")
        
        self.var_select_all = ctk.BooleanVar(value=True)
        self.chk_select_all = ctk.CTkCheckBox(h_chk_frame, text="", variable=self.var_select_all, width=20, height=20, border_width=2,
                                              fg_color=COLORS["blue_primary"], hover_color=COLORS["blue_primary"],
                                              command=self.toggle_select_all_header)
        self.chk_select_all.place(relx=0.5, rely=0.5, anchor="center")

        def create_header_label(parent, text, width=None):
            f = ctk.CTkFrame(parent, fg_color="transparent", width=width if width else 0)
            f.pack(side="left", fill="y" if width else "both", expand=not width)
            f.pack_propagate(False) if width else None
            ctk.CTkLabel(f, text=text.upper(), font=("Arial", 11, "bold"), text_color=COLORS["text_secondary"]).pack(side="left", padx=10, fill="y")
            
        create_header_label(header_row, "Tên Video")
        create_header_label(header_row, "Thời lượng", width=120)
        create_header_label(header_row, "Chất lượng", width=120)
        create_header_label(header_row, "Trạng thái", width=150)
        
        ctk.CTkFrame(self.main_area, height=1, fg_color=COLORS["border"]).grid(row=1, column=0, sticky="sew")


        # 3. Scrollable List
        self.scroll_frame = ctk.CTkScrollableFrame(self.main_area, fg_color="transparent", corner_radius=0)
        self.scroll_frame.grid(row=2, column=0, sticky="nsew", padx=0, pady=0)
        
        # Adjust Grid Row Weights
        self.main_area.grid_rowconfigure(0, weight=0)
        self.main_area.grid_rowconfigure(1, weight=0)
        self.main_area.grid_rowconfigure(2, weight=1)
        self.main_area.grid_rowconfigure(3, weight=0)
        
        # Scroll Fix (macOS)
        def _on_mousewheel(event):
            try:
                target_canvas = None
                if self.winfo_pointerx() - self.winfo_rootx() < 400:
                     if hasattr(self, 'controls_scroll'): target_canvas = self.controls_scroll._parent_canvas
                else: target_canvas = self.scroll_frame._parent_canvas
                
                if target_canvas:
                    if platform.system() == "Darwin": target_canvas.yview_scroll(int(-1 * event.delta), "units")
                    else: target_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            except: pass
        self.bind_all("<MouseWheel>", _on_mousewheel)
        if platform.system() == "Linux":
            self.bind_all("<Button-4>", lambda e: self.scroll_frame._parent_canvas.yview_scroll(-1, "units"))
            self.bind_all("<Button-5>", lambda e: self.scroll_frame._parent_canvas.yview_scroll(1, "units"))
        
        self.lbl_empty = ctk.CTkLabel(self.scroll_frame, text="Chưa có video nào.\nHãy dán link và quét.",
                                      font=("Arial", 14), text_color=COLORS["text_secondary"])
        self.lbl_empty.pack(pady=100)


        # 4. Bottom Footer
        bottom_bar = ctk.CTkFrame(self.main_area, fg_color=COLORS["white"], height=80, corner_radius=0)
        bottom_bar.grid(row=3, column=0, sticky="ew")
        bottom_bar.pack_propagate(False)
        
        ctk.CTkFrame(bottom_bar, height=1, fg_color=COLORS["border"]).pack(fill="x", side="top")

        content = ctk.CTkFrame(bottom_bar, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=32)
        
        self.lbl_selected = ctk.CTkLabel(content, text="Đã chọn: 0 video", 
                                         font=("Arial", 14), text_color=COLORS["text_secondary"])
        self.lbl_selected.pack(side="left")
        
        buttons = ctk.CTkFrame(content, fg_color="transparent")
        buttons.pack(side="right", pady=16)

        self.btn_cancel = ctk.CTkButton(buttons, text="Hủy bỏ", 
                                        fg_color="transparent", text_color=COLORS["text_secondary"],
                                        border_width=1, border_color=COLORS["border"], hover_color=COLORS["bg_main"],
                                        height=45, width=100, corner_radius=12,
                                        command=self.clear_list)
        self.btn_cancel.pack(side="left", padx=(0, 12))

        self.btn_download = ctk.CTkButton(buttons, text="Tải Xuống Ngay", 
                                          fg_color=COLORS["green_success"], hover_color=COLORS["green_hover"],
                                          text_color=COLORS["white"], font=("Arial", 14, "bold"),
                                          height=45, width=160, corner_radius=12,
                                          command=self.start_download_thread)
        self.btn_download.pack(side="left")

    def toggle_select_all_header(self):
        state = self.var_select_all.get()
        self.toggle_all_checkboxes(state)
        
    def clear_list(self):
        # Maps to "Hủy bỏ" which mainly deselects all or clears
        self.toggle_all_checkboxes(False)

    # --- LOGIC IMPLEMENTATION ---



    def choose_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.entry_folder.delete(0, 'end')
            self.entry_folder.insert(0, folder)
            self.entry_folder.xview_moveto(1) # Scroll to end

    def log_msg(self, msg):
        print(msg) # For now print to console, could add a status label later
        # Could update the lbl_count or a toast
        # self.gui_queue.put(lambda: self.lbl_count.configure(text=msg))

    def start_scan_thread(self):
        link = self.entry_link.get().strip()
        if not link:
            messagebox.showinfo("Nhắc nhở", "Vui lòng nhập link video hoặc kênh.")
            return

        self.btn_scan.configure(state="disabled", text="⏳ Đang quét...")
        
        # Clear existing
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
        if hasattr(self, 'lbl_empty'): self.lbl_empty.destroy() # Re-create if empty later
        
        self.video_data_map.clear()
        
        threading.Thread(target=self.run_scan_logic, args=(link,), daemon=True).start()

    def run_scan_logic(self, link):
        try:
             # Auto fix Facebook link
            if "facebook.com" in link or "fb.watch" in link:
                if "videos" not in link and "reels" not in link and "watch" not in link:
                    if link.endswith("/"): link = link[:-1]
                    link += "/videos"
            
            # 1. Check Channel vs Video
            is_youtube_channel = ("youtube.com" in link) and ("youtu.be" not in link)
            is_channel_scan = False
            
            if is_youtube_channel and ("/videos" not in link and "/shorts" not in link and "watch?v=" not in link):
                 # Dual Scan Logic
                 is_channel_scan = True
                 self.scan_youtube_channel(link)
            else:
                 # Standard Scan
                 self.scan_standard(link)

        except Exception as e:
            self.gui_queue.put(lambda: messagebox.showerror("Lỗi", f"Có lỗi xảy ra: {e}"))
        finally:
            self.gui_queue.put(lambda: self.btn_scan.configure(state="normal", text="Quét & Lấy Danh Sách"))

    def scan_standard(self, link):
        cmd = [TOOL_PATH, "--dump-single-json", "--no-check-certificate", "--ignore-errors", link]
        
        # UA Fix
        if "facebook.com" in link or "fb.watch" in link:
             cmd.extend(["--user-agent", "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1"])
        else:
             cmd.extend(["--user-agent", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15"])
        
        if self.var_cookies.get():
             cmd.extend(["--cookies-from-browser", "chrome"])

        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='ignore', creationflags=SUBPROCESS_FLAGS)
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
             # Try Flat Playlist for non-channel lists? Or just report error
             self.gui_queue.put(lambda: messagebox.showerror("Lỗi Quét", f"Không tìm thấy video.\nChi tiết: {stderr[:200]}"))
             return

        try:
            data = json.loads(stdout)
            entries = []
            if 'entries' in data: entries = list(data['entries'])
            else: entries = [data]
            
            entries = [e for e in entries if e]
            self.process_entries(entries, link)
            
        except  Exception as e:
             self.gui_queue.put(lambda: messagebox.showerror("Lỗi Data", "Không đọc được dữ liệu JSON."))

    def scan_youtube_channel(self, link):
        # 1. Videos
        link_videos = link.rstrip("/") + "/videos"
        cmd_v = [TOOL_PATH, "--flat-playlist", "--dump-single-json", "--no-check-certificate", "--ignore-errors", link_videos]
        # Standard UA
        cmd_v.extend(["--user-agent", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15"])
        
        proc_v = subprocess.Popen(cmd_v, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='ignore', creationflags=SUBPROCESS_FLAGS)
        out_v, _ = proc_v.communicate()

        # 2. Shorts
        link_shorts = link.rstrip("/") + "/shorts"
        cmd_s = cmd_v.copy()
        cmd_s[-2] = link_shorts # Replace link
        
        proc_s = subprocess.Popen(cmd_s, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='ignore', creationflags=SUBPROCESS_FLAGS)
        out_s, _ = proc_s.communicate()

        entries = []
        # Parse V
        try:
            if out_v.strip():
                d = json.loads(out_v)
                if 'entries' in d: entries.extend(d['entries'])
        except: pass
        
        # Parse S
        try:
            if out_s.strip():
                d = json.loads(out_s)
                if 'entries' in d: 
                    shorts = d['entries']
                    for s in shorts: s['_is_short'] = True
                    entries.extend(shorts)
        except: pass

        if not entries:
             # Fallback to standard
             self.scan_standard(link)
        else:
             self.process_entries(entries, link)

    def process_entries(self, entries, original_url):
        def update_ui():
            self.lbl_count.configure(text=f"Đã tìm thấy {len(entries)} video")
            
            if not entries:
                 self.lbl_empty = ctk.CTkLabel(self.scroll_frame, text="Không tìm thấy video nào.", font=("Arial", 14), text_color=COLORS["text_secondary"])
                 self.lbl_empty.pack(pady=50)
                 return

            for idx, entry in enumerate(entries, 1):
                title = entry.get('title', 'No Title')
                vid_id = entry.get('id', 'Unknown')
                duration = entry.get('duration_string') or str(entry.get('duration', 'N/A'))
                
                # Url
                web_url = entry.get('webpage_url') or entry.get('url')
                thumb_url = entry.get('thumbnail')
                
                # Check Short
                is_short = entry.get('_is_short', False)
                if "/shorts/" in (web_url or ""): is_short = True
                
                display_type = "[Shorts]" if is_short else "[Video]"
                display_title = f"{display_type} {title}"
                
                # Add to UI
                self.add_video_item(idx, display_title, vid_id, duration, "Best", thumb_url)
                
                # Store data
                self.video_data_map[idx] = {
                    "url": web_url or original_url,
                    "title": title,
                    "id": vid_id
                }
        
        self.gui_queue.put(update_ui)

    def load_thumbnail_async(self, url, label_widget):
        if not url: return
        try:
             print(f"DEBUG: Downloading thumb: {url}")
             # SSL Bypass context
             ctx = ssl.create_default_context()
             ctx.check_hostname = False
             ctx.verify_mode = ssl.CERT_NONE

             req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
             with urllib.request.urlopen(req, context=ctx, timeout=10) as response:
                 data = response.read()
            
             print(f"DEBUG: Thumb data len: {len(data)}")
             import io
             image_data = io.BytesIO(data)
             pil_image = Image.open(image_data)
             
             # Resize to fit 80x50 (approx)
             pil_image.thumbnail((120, 90)) 
             
             # Create CTkImage
             ctk_img = ctk.CTkImage(light_image=pil_image, size=(80, 50))
             
             def update_label():
                 if label_widget.winfo_exists():
                     label_widget.configure(image=ctk_img, text="") 
                     print("DEBUG: Thumbnail updated on UI")
             
             self.gui_queue.put(update_label)
        except Exception as e:
            print(f"ERROR loading thumb {url}: {e}")

    def add_video_item(self, idx, title, vid_id, duration, quality, thumb_url=None):
        # Row Frame (White bg, defaults to white but hover changes it)
        row = ctk.CTkFrame(self.scroll_frame, fg_color=COLORS["white"], corner_radius=0)
        row.pack(fill="x")
        
        # Grid inside Row: [Chk] [VideoInfo] [Duration] [Quality] [Status]
        # Main Grid is NOT used, we use Packing of frames with fixed widths to simulate columns
        
        inner = ctk.CTkFrame(row, fg_color="transparent")
        inner.pack(fill="both", expand=True, pady=0)
        
        # 1. Checkbox (60px)
        f_chk = ctk.CTkFrame(inner, width=60, fg_color="transparent")
        f_chk.pack(side="left", fill="y")
        f_chk.pack_propagate(False)
        
        var_chk = ctk.BooleanVar(value=True)
        # Store
        if idx in self.video_data_map: self.video_data_map[idx]['var_chk'] = var_chk
        
        def on_toggle(): self.update_selection_count()
        
        chk = ctk.CTkCheckBox(f_chk, text="", variable=var_chk, width=20, height=20, corner_radius=4,
                              fg_color=COLORS["blue_primary"], hover_color=COLORS["blue_primary"], border_width=2,
                              command=on_toggle)
        chk.place(relx=0.5, rely=0.5, anchor="center")
        
        # 2. Video Info (Flexible)
        f_vid = ctk.CTkFrame(inner, fg_color="transparent")
        f_vid.pack(side="left", fill="both", expand=True, padx=10, pady=12)
        
        # Thumb
        thumb_label = ctk.CTkLabel(f_vid, text="", width=96, height=54, fg_color=COLORS["border"], corner_radius=6)
        thumb_label.pack(side="left", padx=(0, 12))
        
        if thumb_url:
             threading.Thread(target=self.load_thumbnail_async, args=(thumb_url, thumb_label), daemon=True).start()
        
        # Text
        f_text = ctk.CTkFrame(f_vid, fg_color="transparent")
        f_text.pack(side="left", fill="both", expand=True) # Fill both to center vertically?
        # Actually standard pack is top.
        
        # Title
        lbl_title = ctk.CTkLabel(f_text, text=title, font=("Arial", 13, "bold"), text_color=COLORS["text_primary"], anchor="w")
        lbl_title.pack(fill="x", pady=(4, 0))
        # ID
        ctk.CTkLabel(f_text, text=f"ID: {vid_id}", font=("Arial", 11), text_color=COLORS["text_secondary"], anchor="w").pack(fill="x")
        
        # 3. Duration (120px)
        f_dur = ctk.CTkFrame(inner, width=120, fg_color="transparent")
        f_dur.pack(side="left", fill="y")
        f_dur.pack_propagate(False)
        ctk.CTkLabel(f_dur, text=duration, font=("Arial", 13), text_color=COLORS["text_secondary"]).place(relx=0.5, rely=0.5, anchor="center")
        
        # 4. Quality (120px)
        f_qual = ctk.CTkFrame(inner, width=120, fg_color="transparent")
        f_qual.pack(side="left", fill="y")
        f_qual.pack_propagate(False)
        
        q_badge = ctk.CTkLabel(f_qual, text=quality, fg_color=COLORS["bg_main"], text_color=COLORS["text_secondary"],
                               corner_radius=6, font=("Arial", 11, "bold"), width=60, height=24)
        q_badge.place(relx=0.5, rely=0.5, anchor="center")
        
        # 5. Status (150px)
        f_stat = ctk.CTkFrame(inner, width=150, fg_color="transparent")
        f_stat.pack(side="left", fill="y")
        f_stat.pack_propagate(False)
        
        stat_lbl = ctk.CTkLabel(f_stat, text="Chờ tải...", font=("Arial", 12), text_color=COLORS["text_secondary"])
        stat_lbl.place(relx=0.5, rely=0.5, anchor="center")
        
        if idx in self.video_data_map:
             self.video_data_map[idx]['status_label'] = stat_lbl
        
        # Border Bottom (Separator)
        ctk.CTkFrame(row, height=1, fg_color=COLORS["bg_main"]).pack(side="bottom", fill="x") # bg_main is basically invisible on white, use border color
        
        # Hover
        def on_enter(e): row.configure(fg_color=COLORS["blue_light_bg"])
        def on_leave(e): row.configure(fg_color=COLORS["white"])
        row.bind("<Enter>", on_enter)
        row.bind("<Leave>", on_leave)
        
        self.update_selection_count()

    def update_selection_count(self):
        selected_count = 0
        total_count = len(self.video_data_map)
        
        for data in self.video_data_map.values():
            if data.get('var_chk') and data['var_chk'].get():
                selected_count += 1
                
        if total_count == 0:
            self.lbl_selected.configure(text="Chưa có video")
        else:
            self.lbl_selected.configure(text=f"Đã chọn {selected_count}/{total_count} video")
            
        # Update Header Checkbox (Select All)
        if hasattr(self, 'var_select_all'):
            if total_count > 0 and selected_count == total_count:
                self.var_select_all.set(True)
            elif selected_count < total_count:
                self.var_select_all.set(False)

    def toggle_all_checkboxes(self, select_all):
        for data in self.video_data_map.values():
            if data.get('var_chk'):
                data['var_chk'].set(select_all)
        self.update_selection_count()

    def toggle_select_all(self):
        # This is now handled by the dynamic command in update_selection_count
        # But we keep it as a fallback entry point if needed, simply calling update to check state
        self.update_selection_count()




    def start_direct_download(self):
        # Quick download without list
        link = self.entry_link.get().strip()
        if not link:
             messagebox.showinfo("Lỗi", "Vui lòng nhập link.")
             return
        threading.Thread(target=self.run_download_logic, args=([{'url': link, 'title': 'Quick Download', 'id': 'quick'}], True), daemon=True).start()

    def start_download_thread(self):
        # Filter selected
        selected_items = []
        for idx, data in self.video_data_map.items():
            if data.get('var_chk') and data['var_chk'].get():
                selected_items.append(data)
        
        if not selected_items:
             messagebox.showinfo("Chọn Video", "Bạn chưa chọn video nào để tải.")
             return

        self.btn_download.configure(state="disabled", text="Đang Tải...")
        threading.Thread(target=self.run_download_logic, args=(selected_items,), daemon=True).start()

    def run_download_logic(self, items, is_direct=False):
        save_folder = self.entry_folder.get()
        if not os.path.exists(save_folder):
             os.makedirs(save_folder, exist_ok=True)
        
        is_mp3 = self.var_mp3.get()
        use_cookies = self.var_cookies.get()
        
        total = len(items)
        success_count = 0

        for i, item in enumerate(items, 1):
             url = item.get('url')
             title = item.get('title', 'Video')
             idx_map = None 
             
             # Locate global index for status update
             for k, v in self.video_data_map.items():
                 if v == item: idx_map = k

             def update_status(msg, color=COLORS["text_secondary"]):
                 if idx_map and self.video_data_map.get(idx_map):
                     lbl = self.video_data_map[idx_map].get('status_label')
                     if lbl: lbl.configure(text=msg, text_color=color)
                 print(f"[{i}/{total}] {title}: {msg}")

             update_status("⬇ Đang tải...", COLORS["blue_primary"])
             
             # Build CMD
             cmd = [TOOL_PATH, "--no-check-certificate", "--ignore-errors"]
             
             # Name template
             out_tmpl = os.path.join(save_folder, "%(title)s.%(ext)s")
             cmd.extend(["-o", out_tmpl])
             
             # MP3
             if is_mp3:
                 cmd.extend(["-x", "--audio-format", "mp3"])
             else:
                 cmd.extend(["-f", "bestvideo+bestaudio/best", "--merge-output-format", "mp4"])

             # Thumb
             if self.var_thumb.get():
                cmd.append("--write-thumbnail")

             # Cookies
             if use_cookies:
                 cmd.extend(["--cookies-from-browser", "chrome"])

             cmd.extend(["--no-part", url])
             
             # Run
             process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='ignore', creationflags=SUBPROCESS_FLAGS)
             stdout, stderr = process.communicate()
             
             if process.returncode == 0:
                 update_status("✅ Hoàn tất", COLORS["green_success"])
                 success_count += 1
             else:
                 update_status("❌ Lỗi", COLORS["border"]) # Redish?
        
        # Done
        self.gui_queue.put(lambda: messagebox.showinfo("Hoàn tất", f"Đã tải {success_count}/{total} video."))
        self.gui_queue.put(lambda: self.btn_download.configure(state="normal", text="Tải Xuống Ngay"))

    def check_queue(self):
        try:
            while True:
                task = self.gui_queue.get_nowait()
                if callable(task): task()
        except queue.Empty:
            pass
        finally:
            self.after(100, self.check_queue)

if __name__ == "__main__":
    app = VideoDownloaderApp()
    app.mainloop()
