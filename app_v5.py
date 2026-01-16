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
import ssl

# Error Mapping
ERROR_MAP = {
    "HTTP Error": "Lỗi kết nối mạng/Server",
    "403": "Bị chặn (403) - Cần cập nhật Cookie",
    "Sign in": "Cần đăng nhập (Video hạn chế)",
    "Video unavailable": "Video đã bị xóa/ẩn",
    "This video is private": "Video riêng tư",
    "No video formats": "Không tìm thấy video (Chỉ có ảnh?)",
    "requested format": "Định dạng không hỗ trợ",
    "Fragment": "Lỗi ghép file video"
}

class ToolTip(object):
    def __init__(self, widget):
        self.widget = widget
        self.tipwindow = None
        self.id = None
        self.x = self.y = 0

    def showtip(self, text):
        "Display text in tooltip window"
        self.text = text
        if self.tipwindow or not self.text:
            return
        x, y, cx, cy = self.widget.bbox("insert")
        x = x + self.widget.winfo_rootx() + 25
        y = y + cy + self.widget.winfo_rooty() + 25
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(1)
        tw.wm_geometry("+%d+%d" % (x, y))
        label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                      background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                      font=("tahoma", "8", "normal"))
        label.pack(ipadx=1)

    def hidetip(self):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()

def CreateToolTip(widget, text):
    toolTip = ToolTip(widget)
    def enter(event):
        toolTip.showtip(text)
    def leave(event):
        toolTip.hidetip()
    widget.bind('<Enter>', enter)
    widget.bind('<Leave>', leave)

# Selenium Imports (Lazy Loaded in methods to speed up App Launch)
# Removed top-level imports


class FacebookScanner:
    def __init__(self):
        pass # Imports are handled in scan() for speed
            
    def scan(self, url, status_callback=None):
        """
        Scans a Facebook URL. If a root profile is given, scans both /videos and /reels.
        """
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.common.by import By
            from selenium.webdriver.common.keys import Keys
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from webdriver_manager.chrome import ChromeDriverManager
            from selenium.webdriver.chrome.service import Service
        except ImportError as e:
            if status_callback: status_callback(f"Lỗi thiếu thư viện: {e}")
            return []

        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-notifications")
        options.add_argument("--mute-audio")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
        
        driver = None
        unique_links = set()
        results = []
        
        # Determine Scan Targets
        targets = [url]
        clean_input = url.split('?')[0].rstrip('/')
        
        # Heuristic: If URL is just a profile/page (no /videos, /reels, /posts, /watch)
        # We auto-expand to scan BOTH '/videos' and '/reels'
        if "facebook.com" in clean_input:
            if not any(x in clean_input for x in ["/videos", "/reels", "/watch", "/posts", "/photo", "/groups"]):
                print("Detected Root URL -> Smart Scan: Videos + Reels")
                targets = [f"{clean_input}/videos", f"{clean_input}/reels"]
        
        try:
            if status_callback: status_callback("Đang khởi động Robot thông minh...")
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            
            # Iterate through all targets (e.g. Videos then Reels)
            for idx, target_url in enumerate(targets):
                tab_name = "Reels" if "/reels" in target_url else "Videos"
                if status_callback: status_callback(f"Đang quét mục {tab_name} ({idx+1}/{len(targets)})...")
                
                try:
                    driver.get(target_url)
                    time.sleep(3)
                    
                    # Zoom out
                    try: driver.execute_script("document.body.style.zoom='50%'")
                    except: pass
                    
                    
                    # Popup Handling
                    # Keys imported above

                    
                    last_height = driver.execute_script("return document.body.scrollHeight")
                    scroll_count = 0
                    max_scrolls = 100 
                    retry_scrolls = 0
                    

                    while scroll_count < max_scrolls:
                        if status_callback: status_callback(f"Quét {tab_name}: Cuộn {scroll_count}...")
                        
                        try: driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                        except: pass

                        # Scroll
                        driver.execute_script("window.scrollBy(0, 1500);")
                        time.sleep(1)
                        
                        # Extract
                        elements = driver.find_elements(By.TAG_NAME, "a")
                        for elem in elements:
                            try:
                                href = elem.get_attribute("href")
                                if href and any(x in href for x in ["/videos/", "/reel/", "/watch/", "video.php"]):
                                    clean_link = href.split("?")[0]
                                    if clean_link not in unique_links:
                                        unique_links.add(clean_link)
                                        
                                        # Metadata
                                        thumb_url = None
                                        duration_text = None
                                        try:
                                            imgs = elem.find_elements(By.TAG_NAME, "img")
                                            if imgs: thumb_url = imgs[0].get_attribute("src")
                                            
                                            text_content = elem.get_attribute("innerText") or ""
                                            aria = elem.get_attribute("aria-label") or ""
                                            full_text = text_content + " " + aria
                                            
                                            dur_match = re.search(r'(\d+:\d+)', full_text)
                                            if dur_match: duration_text = dur_match.group(1)
                                        except: pass
                                        
                                        results.append({
                                            'url': clean_link,
                                            'thumbnail': thumb_url,
                                            'duration': duration_text 
                                        })
                            except: pass
                        
                        # Check progress
                        new_height = driver.execute_script("return document.body.scrollHeight")
                        
                        if scroll_count % 5 == 0:
                             driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                             time.sleep(2)

                        if new_height == last_height:
                            retry_scrolls += 1
                            if status_callback: status_callback(f"Đang tìm thêm {tab_name} ({retry_scrolls}/5)...")
                            if retry_scrolls >= 5: break 
                            time.sleep(2)
                        else:
                            retry_scrolls = 0
                            
                        last_height = new_height
                        scroll_count += 1
                        last_height = new_height
                        scroll_count += 1
                        
                except Exception as sub_e:
                    print(f"Error scanning tab {target_url}: {sub_e}")
                
                # Notify switch
                if idx < len(targets) - 1:
                     next_tab = "Reels" if "reels" in targets[idx+1] else "Videos"
                     if status_callback: status_callback(f"✅ Xong {tab_name}. Đang chuyển sang {next_tab}...")
                     time.sleep(2)
                    
            if status_callback: status_callback(f"Đã quét xong! Tổng: {len(results)} video.")
                
        except Exception as e:
            print(f"Selenium Scan Error: {e}")
            if status_callback: status_callback(f"Lỗi hệ thống: {e}")
        finally:
            if driver: driver.quit()
            
        return results


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
        self.title("Video Downloader Pro v6.2")
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
        
        # Batch Import Link
        btn_batch = ctk.CTkButton(url_group, text="📋 Nhập nhiều Link", width=100, height=24,
                                  fg_color="transparent", text_color=COLORS["blue_primary"],
                                  font=("Arial", 11, "bold"), hover=False,
                                  command=self.open_batch_import)
        btn_batch.pack(fill="x", pady=(0, 5))
        
        ctk.CTkLabel(controls_inner, text="Hỗ trợ: YouTube, TikTok, FB & 1000+ web khác", 
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
        
        self.var_thumb = ctk.BooleanVar(value=False)
        self.chk_thumb = create_option_card(controls_inner, "Tải Thumbnail", "Lưu ảnh bìa chất lượng cao", self.var_thumb, checked=False)
        
        self.var_cookies = ctk.BooleanVar(value=False)
        self.chk_cookies = create_option_card(controls_inner, "Sử dụng Cookies", "Dùng cho video riêng tư/hạn chế", self.var_cookies)
        
        # Cookie Source Selection
        self.cookie_source_var = ctk.StringVar(value="File cookies.txt")
        self.combo_cookie_source = ctk.CTkComboBox(controls_inner, 
                                                   values=["File cookies.txt", "Chrome", "Safari", "Edge", "Firefox", "Opera", "Brave", "Vivaldi", "Chromium"],
                                                   variable=self.cookie_source_var,
                                                   command=self.on_cookie_source_change)
        self.combo_cookie_source.pack(fill="x", pady=(0, 6))

        # Cookie File Selection Button (Dynamic)
        self.cookie_file_path = None
        self.btn_cookie_file = ctk.CTkButton(controls_inner, text="Chọn file cookies.txt", 
                                             height=30, fg_color=COLORS["bg_sidebar"], text_color=COLORS["blue_primary"],
                                             border_width=1, border_color=COLORS["blue_primary"],
                                             command=self.select_cookie_file)
        self.btn_cookie_file.pack(fill="x", pady=(0, 10))

        # Initial State
        self.on_cookie_source_change("File cookies.txt")
        
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
        
        # Grid Configuration for alignment (0:Chk, 1:Name, 2:Dur, 3:Qual, 4:Status)
        header_row.grid_columnconfigure(0, weight=0, minsize=50) # Checkbox
        header_row.grid_columnconfigure(1, weight=1)             # Name (Flexible)
        header_row.grid_columnconfigure(2, weight=0, minsize=100) # Duration
        header_row.grid_columnconfigure(3, weight=0, minsize=80)  # Quality
        header_row.grid_columnconfigure(4, weight=0, minsize=120) # Status

        # Header Columns
        # Col 0: Checkbox
        h_chk_frame = ctk.CTkFrame(header_row, fg_color="transparent", width=50, height=50)
        h_chk_frame.grid(row=0, column=0, sticky="nsew")
        
        self.var_select_all = ctk.BooleanVar(value=True)
        self.chk_select_all = ctk.CTkCheckBox(h_chk_frame, text="", variable=self.var_select_all, width=20, height=20, border_width=2,
                                              fg_color=COLORS["blue_primary"], hover_color=COLORS["blue_primary"],
                                              command=self.toggle_select_all_header)
        self.chk_select_all.place(relx=0.5, rely=0.5, anchor="center")

        def create_header_label(col_idx, text, anchor="center"):
            lbl = ctk.CTkLabel(header_row, text=text.upper(), font=("Arial", 11, "bold"), text_color=COLORS["text_secondary"])
            lbl.grid(row=0, column=col_idx, sticky="nsew", padx=5)
            # if anchor != "center": lbl.configure(anchor=anchor) # CTkLabel grid treats sticky as fill, explicit anchor sometimes needed

        create_header_label(1, "Tên Video", anchor="w")
        create_header_label(2, "Thời lượng")
        create_header_label(3, "Chất lượng")
        create_header_label(4, "Trạng thái")
        
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
        self.var_select_all.set(False) # Uncheck header

    def open_batch_import(self):
        # Create a Toplevel window
        dialog = ctk.CTkToplevel(self)
        dialog.title("Nhập danh sách Link")
        dialog.geometry("500x400")
        dialog.transient(self) # Make it modal-like
        
        ctk.CTkLabel(dialog, text="Dán danh sách link (mỗi dòng 1 link):", font=("Arial", 14, "bold")).pack(pady=10)
        
        txt_input = ctk.CTkTextbox(dialog, width=450, height=250)
        txt_input.pack(pady=10)
        txt_input.focus()
        
        def on_confirm():
            content = txt_input.get("1.0", "end").strip()
            if not content: return
            lines = [l.strip() for l in content.split('\n') if l.strip()]
            dialog.destroy()
            self.process_batch_links(lines)
            
        btn_confirm = ctk.CTkButton(dialog, text="Xác nhận & Thêm vào list", command=on_confirm, fg_color=COLORS["blue_primary"])
        btn_confirm.pack(pady=10)

    def process_batch_links(self, links):
        if not links: return
        
        # Clear existing? Maybe not, allow appending
        # self.video_data_map.clear()
        
        entries = []
        for i, link in enumerate(links):
            # Create dummy entry
            entries.append({
                'id': f'batch_{int(time.time())}_{i}',
                'title': f'Video Link {i+1}', # Will be updated if possible or just use link
                'url': link,
                'webpage_url': link,
                'duration': 0,
                'thumbnail': None
            })
            
        self.process_entries(entries, "Batch Import")
        
        # Optionally trigger a quick metadata fetch in background?
        # For now, just listing them is enough to let user download. 
        # The download process will verify them.
        self.log_msg(f"Added {len(entries)} links from batch import.")

    # --- LOGIC IMPLEMENTATION ---



    def choose_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.entry_folder.delete(0, 'end')
            self.entry_folder.insert(0, folder)
            self.entry_folder.xview_moveto(1) # Scroll to end

    def select_cookie_file(self):
        filename = filedialog.askopenfilename(title="Chọn file cookies.txt (Netscape format)", filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")])
        if filename:
            self.cookie_file_path = filename
            self.var_cookies.set(True) # Auto check
            self.btn_cookie_file.configure(text=f"File: {os.path.basename(filename)}", fg_color=COLORS["blue_light_bg"])
            messagebox.showinfo("Cookies", "Đã chọn file cookies.\nLưu ý: File phải đúng định dạng Netscape/Mozilla cookies.")

    def on_cookie_source_change(self, choice):
        if choice == "File cookies.txt":
            self.btn_cookie_file.pack(fill="x", pady=(0, 10)) # Show button
        else:
            self.btn_cookie_file.pack_forget() # Hide button
            self.var_cookies.set(True) # Auto enable cookies if browser selected

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
        
        # Facebook Cookie Warning
        if ("facebook.com" in link or "fb.watch" in link) and not self.var_cookies.get():
             resp = messagebox.askyesno("Cảnh báo Facebook", "Facebook thường yêu cầu Cookies để quét được đầy đủ danh sách video.\n\nBạn chưa chọn 'Sử dụng Cookies'.\nBạn có chắc chắn muốn tiếp tục không?\n(Chọn 'No' để quay lại thêm Cookies)")
             if not resp: return

        threading.Thread(target=self.run_scan_logic, args=(link,), daemon=True).start()

    def run_scan_logic(self, link):
        try:
            # Auto fix Facebook link
            if "facebook.com" in link or "fb.watch" in link:
                # Don't modify if it looks like a specific video, reel, or playlist/album
                keywords = ["/videos", "/reels", "watch", "playlist", "set=", "media", "/posts/", "/story"]
                if not any(k in link for k in keywords):
                    # It's likely a profile or page URL (e.g. facebook.com/pageName)
                    # We prefer scanning the /videos tab
                    base_link = link.rstrip("/")
                    link = base_link + "/videos"
                    print(f"DEBUG: Auto-converted to video tab: {link}")
                    
                    # Update UI to reflect change
                    self.gui_queue.put(lambda: self.entry_link.delete(0, 'end') or self.entry_link.insert(0, link))
            
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

    def _scan_facebook_selenium(self, link):
        # Lazy check
        try:
            import selenium
        except ImportError:
            return False
             
        self.gui_queue.put(lambda: self.log_msg("⚠ Đang kích hoạt robot quét sâu (Selenium)..."))
        
        scanner = FacebookScanner()
        
        def status_cb(msg):
             self.gui_queue.put(lambda: self.log_msg(msg))
             print(msg)
             
        try:
            video_urls = scanner.scan(link, status_cb)
        except Exception as e:
            print(f"Selenium Error: {e}")
            return False
            
        if not video_urls:
             return False

        entries = []
        for v_item in video_urls:
            v_url = v_item['url']
            v_thumb = v_item['thumbnail']
            v_dur = v_item['duration']
            
            entries.append({
                'id': v_url,
                'title': f"Facebook Video {v_url[-15:]}...", 
                'url': v_url,
                'webpage_url': v_url,
                'thumbnail': v_thumb,
                'duration': None, # Raw seconds
                'duration_string': v_dur, # Display string
                'resolution': 'Unknown'
            })
            
        self.process_entries(entries, link)
        # Auto Select All
        self.gui_queue.put(lambda: self.toggle_all_checkboxes(True))
        return True

    def scan_standard(self, link):
        # List of candidate URLs to try
        candidates = [link]
        
        if "facebook.com" in link or "fb.watch" in link:
            # Generate variants
            
            # 1. Handle /videos vs /reels
            if "/videos" in link:
                # Try removing videos, or swapping to reels
                base = link.replace("/videos", "")
                candidates.append(base)
                if base.endswith("/"): candidates.append(base + "reels")
                else: candidates.append(base + "/reels")
                
            elif "/reels" in link:
                # Try removing reels, or swapping to videos
                base = link.replace("/reels", "")
                candidates.append(base)
                if base.endswith("/"): candidates.append(base + "videos")
                else: candidates.append(base + "/videos")
                
            else:
                # Neither present, try adding both
                if link.endswith("/"): 
                    candidates.append(link + "videos")
                    candidates.append(link + "reels")
                else: 
                    candidates.append(link + "/videos")
                    candidates.append(link + "/reels")
            
            # 2. Mobile variants for all above
            mobile_candidates = []
            for c in candidates:
                if "www.facebook.com" in c:
                    mobile_candidates.append(c.replace("www.facebook.com", "m.facebook.com"))
                elif "facebook.com" in c and "m.facebook.com" not in c:
                    mobile_candidates.append(c.replace("facebook.com", "m.facebook.com"))
            
            candidates.extend(mobile_candidates)
            
            # Deduplicate preserving order
            seen = set()
            unique_candidates = []
            for c in candidates:
                if c not in seen:
                    unique_candidates.append(c)
                    seen.add(c)
            candidates = unique_candidates

        print(f"DEBUG: Scanning candidates: {candidates}")
        
        success = False
        for c_link in candidates:
            print(f"Trying: {c_link}")
            if self._try_scan(c_link):
                success = True
                break

        if not success and not self.stop_flag: 
             # Try Selenium Fallback for Facebook
             if ("facebook.com" in link or "fb.watch" in link) and HAS_SELENIUM:
                 if self._scan_facebook_selenium(link):
                     return # Success with Selenium

             # Only show error if all retries failed
             self.gui_queue.put(lambda: messagebox.showerror("Lỗi Quét", f"Không tìm thấy video từ link này.\nĐã thử {len(candidates)} kiểu link khác nhau nhưng đều thất bại.\n\nGợi ý: Thử link của từng video lẻ thay vì link danh sách."))

    def _try_scan(self, link):
        cmd = [TOOL_PATH, "--dump-single-json", "--no-check-certificate", "--ignore-errors", link]
        
        # UA Fix - Use Desktop UA for Facebook to match Cookies better
        if "facebook.com" in link or "fb.watch" in link:
             # Use Standard Windows 10 Chrome UA - safest for most cookies
             cmd.extend(["--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"])
        else:
             cmd.extend(["--user-agent", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15"])
        
        if self.var_cookies.get():
             source = self.cookie_source_var.get()
             if source == "File cookies.txt":
                 if hasattr(self, 'cookie_file_path') and self.cookie_file_path and os.path.exists(self.cookie_file_path):
                     print(f"Using cookie file: {self.cookie_file_path}")
                     cmd.extend(["--cookies", self.cookie_file_path])
             else:
                 # Browser source
                 print(f"Using cookies from browser: {source}")
                 cmd.extend(["--cookies-from-browser", source.lower()])

        try:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='ignore', creationflags=SUBPROCESS_FLAGS)
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                 print(f"Scan failed for {link}: {stderr[:100]}")
                 return False

            data = json.loads(stdout)
            entries = []
            if 'entries' in data: entries = list(data['entries'])
            else: entries = [data]
            
            entries = [e for e in entries if e]
            if not entries: return False
            
            self.process_entries(entries, link)
            return True
            
        except Exception as e:
             print(f"Error parsing JSON for {link}: {e}")
             return False

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
        self.gui_queue.put(lambda: self.toggle_all_checkboxes(True))

    def format_duration(self, seconds):
        if not seconds: return "N/A"
        try:
            seconds = int(seconds)
            h = seconds // 3600
            m = (seconds % 3600) // 60
            s = seconds % 60
            if h > 0:
                return f"{h}:{m:02}:{s:02}"
            else:
                return f"{m}:{s:02}"
        except: return str(seconds)

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
                
                # Format Duration
                raw_duration = entry.get('duration')
                duration_str = entry.get('duration_string')
                if raw_duration:
                    duration = self.format_duration(raw_duration)
                else: 
                     duration = duration_str or "N/A"
                
                # Url
                web_url = entry.get('webpage_url') or entry.get('url')
                thumb_url = entry.get('thumbnail')
                
                # Check Short
                is_short = entry.get('_is_short', False)
                if "/shorts/" in (web_url or ""): is_short = True
                
                display_type = "[Shorts]" if is_short else "[Video]"
                display_title = f"{display_type} {title}"
                
                # Add to UI
                # FIX: Must populate data BEFORE adding item because add_video_item tries to access video_data_map[idx]
                
                # Check history
                is_downloaded = self.check_history(vid_id)
                if is_downloaded:
                     display_title = f"[Đã Tải] {display_title}"

                # Store data first
                self.video_data_map[idx] = {
                    "url": web_url or original_url,
                    "title": title,
                    "id": vid_id,
                    "is_downloaded": is_downloaded
                }

                self.add_video_item(idx, display_title, vid_id, duration, "Best", thumb_url, is_downloaded)

        
        self.gui_queue.put(update_ui)

    def load_thumbnail_async(self, url, label_widget):
        if not url: return
        
        # Set placeholder while loading
        self.gui_queue.put(lambda: label_widget.configure(text="Loading...", text_color=COLORS["text_secondary"]))

        def task():
            try:
                 print(f"DEBUG: Downloading thumb: {url}")
                 # SSL Bypass context
                 ctx = ssl.create_default_context()
                 ctx.check_hostname = False
                 ctx.verify_mode = ssl.CERT_NONE

                 req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})
                 with urllib.request.urlopen(req, context=ctx, timeout=5) as response:
                     data = response.read()
                
                 if not data: return

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
                         label_widget.image = ctk_img # FIX: Keep reference to avoid GC
                         print("DEBUG: Thumbnail updated on UI")
                 
                 self.gui_queue.put(update_label)
            except Exception as e:
                print(f"ERROR loading thumb {url}: {e}")
                self.gui_queue.put(lambda: label_widget.configure(text="No Image"))

        threading.Thread(target=task, daemon=True).start()

    def check_history(self, vid_id):
        try:
            if not os.path.exists("history.txt"): return False
            with open("history.txt", "r", encoding="utf-8") as f:
                lines = f.read().splitlines()
            return vid_id in lines
        except: return False

    def add_to_history(self, vid_id):
        try:
            with open("history.txt", "a", encoding="utf-8") as f:
                f.write(vid_id + "\n")
        except: pass

    def add_video_item(self, idx, title, vid_id, duration, quality, thumb_url=None, is_downloaded=False):
        # Row Frame (Use Grid to match header)
        row = ctk.CTkFrame(self.scroll_frame, fg_color=COLORS["white"], corner_radius=0)
        row.pack(fill="x", pady=(0, 1)) # 1px gap for border effect

        # Grid Config
        row.grid_columnconfigure(0, weight=0, minsize=50) # Checkbox
        row.grid_columnconfigure(1, weight=1)             # Name (Flexible)
        row.grid_columnconfigure(2, weight=0, minsize=100) # Duration
        row.grid_columnconfigure(3, weight=0, minsize=80)  # Quality
        row.grid_columnconfigure(4, weight=0, minsize=120) # Status

        # 1. Checkbox
        f_chk = ctk.CTkFrame(row, fg_color="transparent", width=50, height=50)
        f_chk.grid(row=0, column=0, sticky="nsew")
        
        var_chk = ctk.BooleanVar(value=not is_downloaded) 
        if idx in self.video_data_map: self.video_data_map[idx]['var_chk'] = var_chk
        
        def on_toggle(): 
             self.update_selection_count()
        
        chk = ctk.CTkCheckBox(f_chk, text="", variable=var_chk, width=20, height=20, corner_radius=4,
                              fg_color=COLORS["blue_primary"], hover_color=COLORS["blue_primary"], border_width=2,
                              command=on_toggle)
        chk.place(relx=0.5, rely=0.5, anchor="center")

        # 2. Thumbnail + Title (Horizontal)
        f_info = ctk.CTkFrame(row, fg_color="transparent")
        f_info.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        
        # Thumbnail Label
        lbl_thumb = ctk.CTkLabel(f_info, text="", width=80, height=50, fg_color="#eee", corner_radius=6)
        lbl_thumb.pack(side="left", padx=(0, 10))
        
        # Text Info
        f_text = ctk.CTkFrame(f_info, fg_color="transparent")
        f_text.pack(side="left", fill="both", expand=True) # expand to take remaining width in f_info
        
        lbl_title = ctk.CTkLabel(f_text, text=title, font=("Arial", 13, "bold"), text_color=COLORS["text_primary"], 
                                 anchor="w", justify="left")
        lbl_title.pack(fill="x", anchor="w")
        
        lbl_id = ctk.CTkLabel(f_text, text=f"ID: {vid_id}", font=("Arial", 11), text_color=COLORS["text_secondary"], anchor="w")
        lbl_id.pack(fill="x", anchor="w")

        # Load Thumb
        if thumb_url:
            self.load_thumbnail_async(thumb_url, lbl_thumb)

        # 3. Duration
        ctk.CTkLabel(row, text=str(duration), font=("Arial", 13), text_color=COLORS["text_secondary"]).grid(row=0, column=2, sticky="nsew")

        # 4. Quality
        ctk.CTkButton(row, text=quality, width=60, height=24, fg_color=COLORS["bg_main"], 
                      text_color=COLORS["text_primary"], hover=False, font=("Arial", 11, "bold")).grid(row=0, column=3)

        # 5. Status
        lbl_status = ctk.CTkLabel(row, text="Chờ tải...", font=("Arial", 13), text_color=COLORS["text_secondary"], width=120, anchor="e")
        lbl_status.grid(row=0, column=4, sticky="nsew", padx=(0, 10))
        
        # Store for updates
        if idx in self.video_data_map:
             self.video_data_map[idx]['status_label'] = lbl_status
        
        # Hover Effect
        def on_enter(e): 
             if row.winfo_exists(): row.configure(fg_color=COLORS["blue_light_bg"])
        def on_leave(e): 
             if row.winfo_exists(): row.configure(fg_color=COLORS["white"])
        
        row.bind("<Enter>", on_enter)
        row.bind("<Leave>", on_leave)
        
        # Propagate click to checkbox (optional, but nice UX)
        # row.bind("<Button-1>", lambda e: chk.toggle() or on_toggle())
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

    def stop_download_process(self):
        self.stop_download_flag = True
        self.btn_download.configure(state="disabled", text="Đang Hủy...")

    def run_download_logic(self, items, is_direct=False):
        self.stop_download_flag = False
        
        # Connect Cancel Button (Hủy bỏ) 
        # Note: The "Hủy bỏ" button in UI (btn_cancel) usually clears selection, 
        # but during download we want it to stop. 
        # Ideally we should have a dedicated Stop button, or toggle the Main Download button.
        # For now, let's retarget the "Hủy bỏ" button temporarily
        
        original_cancel_cmd = self.btn_cancel.cget("command")
        self.gui_queue.put(lambda: self.btn_cancel.configure(text="Dừng Tải (Stop)", command=self.stop_download_process, fg_color="red", hover_color="#991b1b"))

        save_folder = self.entry_folder.get()
        if not os.path.exists(save_folder):
             os.makedirs(save_folder, exist_ok=True)
        
        is_mp3 = self.var_mp3.get()
        use_cookies = self.var_cookies.get()
        
        total = len(items)
        success_count = 0

        for i, item in enumerate(items, 1):
             if self.stop_download_flag:
                 break

             url = item.get('url')
             title = item.get('title', 'Video')
             idx_map = None 
             
             # Locate global index for status update
             for k, v in self.video_data_map.items():
                 if v == item: idx_map = k

             def update_status(msg, color=COLORS["text_secondary"]):
                 # Truncate strictly
                 if len(msg) > 18: msg = msg[:15] + "..."
                 
                 if idx_map and self.video_data_map.get(idx_map):
                     lbl = self.video_data_map[idx_map].get('status_label')
                     if lbl and lbl.winfo_exists(): lbl.configure(text=msg, text_color=color)
                 print(f"[{i}/{total}] {title}: {msg}")

             update_status("⬇ Đang kết nối...", COLORS["blue_primary"])
             
             # Build CMD
             cmd = [TOOL_PATH, "--no-check-certificate", "--ignore-errors", "--newline"]
             
             # Name template
             out_tmpl = os.path.join(save_folder, "%(title)s.%(ext)s")
             cmd.extend(["-o", out_tmpl])
             
             # MP3
             if is_mp3:
                 cmd.extend(["-x", "--audio-format", "mp3"])
             else:
                 # Strict MP4 preference
                 cmd.extend(["-f", "best[ext=mp4]/best", "--merge-output-format", "mp4"])

             # Thumb
             if self.var_thumb.get():
                cmd.append("--write-thumbnail")

             # Cookies
             if use_cookies:
                 source = self.cookie_source_var.get()
                 if source == "File cookies.txt":
                     if hasattr(self, 'cookie_file_path') and self.cookie_file_path and os.path.exists(self.cookie_file_path):
                         cmd.extend(["--cookies", self.cookie_file_path])
                 else:
                     cmd.extend(["--cookies-from-browser", source.lower()])

             cmd.extend(["--no-part", url])
             
             # Run & Parse Output Realtime
             try:
                 process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='ignore', creationflags=SUBPROCESS_FLAGS)
                 
                 found_error = None
                 while True:
                     if self.stop_download_flag:
                         process.terminate()
                         update_status("⏹ Đã dừng", "red")
                         break
                         
                     line = process.stdout.readline()
                     if not line and process.poll() is not None:
                         break
                     if line:
                         line = line.strip()
                         # Relaxed Regex Progress (Look for any % number)
                         perc = re.search(r'(\d+(?:\.\d+)?)%', line)
                         if perc:
                             update_status(f"⬇ {perc.group(1)}%", COLORS["blue_primary"])
                             
                         # Regex Error
                         if "ERROR:" in line:
                             print(f"CMD Error: {line}")
                             err_match = re.search(r'ERROR:\s+(.*)', line)
                             if err_match:
                                 found_error = err_match.group(1).split(';')[0]
                             else:
                                 found_error = "Lỗi không xác định"

                 rc = process.poll()
                 
                 if self.stop_download_flag:
                     break
                 
                 # Strict Validation
                 # Check if any video file exists with matching title pattern or recent file
                 # Since filename is dynamic, simple success check: rc==0 AND found_error is None
                 status_ok = (rc == 0 and not found_error)
                 
                 # Extra Check: Did it download a video file?
                 # Warning: hard to know exact filename. But we can trust rc=0 usually.
                 # User reported "Still JPG". This means download finished but was not a video.
                 # If -f best[ext=mp4] failed, it might have done nothing?
                 
                 if status_ok:
                     update_status("✅ Hoàn tất", COLORS["green_success"])
                     success_count += 1
                     if item.get('id'): self.add_to_history(item.get('id')) 
                 else:
                     # Translate Error
                     fail_msg = found_error if found_error else "Lỗi tải"
                     viet_msg = fail_msg
                     
                     for key, val in ERROR_MAP.items():
                         if key.lower() in fail_msg.lower():
                             viet_msg = val
                             break
                             
                     # Display short
                     display_msg = viet_msg
                     if len(display_msg) > 20: display_msg = display_msg[:17] + "..."
                     
                     # Update with Tooltip
                     def update_err_gui():
                         if idx_map and self.video_data_map.get(idx_map):
                             lbl = self.video_data_map[idx_map].get('status_label')
                             if lbl:
                                 lbl.configure(text=display_msg, text_color="red")
                                 CreateToolTip(lbl, viet_msg) # Add Hover
                                 
                     self.gui_queue.put(update_err_gui)
                     print(f"Fail: {viet_msg}")

             except Exception as e:
                 print(f"Exec Error: {e}")
                 err_str = str(e)
                 if len(err_str) > 25: err_str = err_str[:22] + "..."
                 update_status(f"❌ {err_str}", "red")
        # Restore Cancel Button
        self.gui_queue.put(lambda: self.btn_cancel.configure(text="Hủy bỏ", command=original_cancel_cmd, fg_color="transparent", hover_color="#e5e7eb"))
        self.gui_queue.put(lambda: self.btn_download.configure(state="normal", text=f"Tải Xuống ({success_count}/{total})")) 
        
        if getattr(self, 'stop_download_flag', False):
             self.gui_queue.put(lambda: messagebox.showinfo("Đã dừng tải", f"🛑 Bạn đã dừng quá trình tải.\n\n✅ Đã tải: {success_count} video\n❌ Lỗi/Bỏ qua: {(i if 'i' in locals() else processed_count) - success_count}"))
        else:
             self.gui_queue.put(lambda: messagebox.showinfo("Hoàn tất", f"✅ Tải xuống hoàn tất!\n\nTổng cộng: {total}\nThành công: {success_count}\nLỗi: {total - success_count}"))
        
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
