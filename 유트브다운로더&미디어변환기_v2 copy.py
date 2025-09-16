import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import yt_dlp
import os
import sys
import subprocess
from pathlib import Path
import threading

def download_youtube(url, output_dir, format_type, log_callback, status_callback):
    """
    Download YouTube video as mp4 or mp3.
    """
    ydl_opts = {
        'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
    }
    if format_type == 'mp3':
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        })
    else:  # mp4
        ydl_opts['format'] = 'best[ext=mp4]'
    try:
        log_callback(f"다운로드 시작: {url}")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        log_callback("다운로드 완료!")
        status_callback("다운로드 완료!")
        messagebox.showinfo("완료", "다운로드가 완료되었습니다!")
    except Exception as e:
        log_callback(f"다운로드 오류: {e}")
        status_callback("다운로드 오류")
        messagebox.showerror("오류", str(e))
    finally:
        status_callback("대기 중...")

def convert_media(input_file, output_ext, log_callback):
    """
    Convert media file to another format using ffmpeg.
    """
    base = os.path.splitext(input_file)[0]
    output_file = f"{base}.{output_ext}"
    cmd = [
        'ffmpeg',
        '-y',  # overwrite
        '-i', input_file,
        output_file
    ]
    try:
        log_callback(f"변환 시작: {input_file} → {output_file}")
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        log_callback(f"변환 완료: {output_file}")
        return True, output_file
    except subprocess.CalledProcessError as e:
        log_callback(f"변환 실패: {e}")
        return False, str(e)

def convert_media_batch(input_files, output_ext, log_callback, status_callback, progress_callback=None):
    """
    Convert multiple media files to another format using ffmpeg.
    """
    total_files = len(input_files)
    successful = 0
    failed = 0
    
    for i, input_file in enumerate(input_files, 1):
        if progress_callback:
            progress_callback(i, total_files)
        
        status_callback(f"변환 중 ({i}/{total_files})...")
        success, result = convert_media(input_file, output_ext, log_callback)
        
        if success:
            successful += 1
            log_callback(f"[{i}/{total_files}] 성공: {result}")
        else:
            failed += 1
            log_callback(f"[{i}/{total_files}] 실패: {input_file} - {result}")
    
    log_callback(f"\n배치 변환 완료! 성공: {successful}, 실패: {failed}")
    status_callback(f"배치 변환 완료! (성공: {successful}, 실패: {failed})")
    
    if failed == 0:
        messagebox.showinfo("완료", f"모든 파일 변환 완료!\n성공: {successful}개")
    else:
        messagebox.showwarning("완료", f"배치 변환 완료\n성공: {successful}개, 실패: {failed}개")

class MediaDownloaderConverterGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube 다운로더 & 미디어 변환기")
        self.root.geometry("800x520")
        self.root.minsize(800, 520)
        self.setup_ui()

    def setup_ui(self):
        tab_control = ttk.Notebook(self.root)
        self.tab1 = ttk.Frame(tab_control)
        self.tab2 = ttk.Frame(tab_control)
        tab_control.add(self.tab1, text='YouTube 다운로드')
        tab_control.add(self.tab2, text='미디어 변환')
        tab_control.pack(expand=1, fill='both')

        # --- Tab 1: YouTube 다운로드 ---
        ttk.Label(self.tab1, text="YouTube URL:").grid(row=0, column=0, sticky=tk.W, pady=5, padx=5)
        self.url_entry = ttk.Entry(self.tab1, width=60)
        self.url_entry.grid(row=0, column=1, columnspan=3, sticky=(tk.W, tk.E), pady=5)

        ttk.Label(self.tab1, text="형식:").grid(row=1, column=0, sticky=tk.W, pady=5, padx=5)
        self.format_var = tk.StringVar(value="mp4")
        ttk.Radiobutton(self.tab1, text="MP4", variable=self.format_var, value="mp4").grid(row=1, column=1, sticky=tk.W)
        ttk.Radiobutton(self.tab1, text="MP3", variable=self.format_var, value="mp3").grid(row=1, column=2, sticky=tk.W)

        ttk.Label(self.tab1, text="저장 경로:").grid(row=2, column=0, sticky=tk.W, pady=5, padx=5)
        self.save_path_entry = ttk.Entry(self.tab1, width=50)
        self.save_path_entry.insert(0, str(Path.home() / "Downloads"))
        self.save_path_entry.grid(row=2, column=1, pady=5, sticky=(tk.W, tk.E))
        ttk.Button(self.tab1, text="찾아보기", command=self.browse_save_path).grid(row=2, column=2, padx=5, sticky=tk.W)
        ttk.Button(self.tab1, text="폴더 열기", command=self.open_download_folder).grid(row=2, column=3, padx=5, sticky=tk.W)

        self.download_btn = ttk.Button(self.tab1, text="다운로드", command=self.start_download)
        self.download_btn.grid(row=3, column=0, columnspan=4, pady=10)

        # --- Tab 2: 미디어 변환 ---
        ttk.Label(self.tab2, text="입력 파일:").grid(row=0, column=0, sticky=tk.W, pady=5, padx=5)
        
        # 파일 선택 모드 라디오 버튼
        self.file_mode_var = tk.StringVar(value="single")
        ttk.Radiobutton(self.tab2, text="단일 파일", variable=self.file_mode_var, value="single", command=self.toggle_file_mode).grid(row=0, column=1, sticky=tk.W)
        ttk.Radiobutton(self.tab2, text="여러 파일", variable=self.file_mode_var, value="multiple", command=self.toggle_file_mode).grid(row=0, column=2, sticky=tk.W)
        
        # 단일 파일 선택 UI
        self.single_file_frame = ttk.Frame(self.tab2)
        self.single_file_frame.grid(row=1, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=5)
        
        self.input_file_entry = ttk.Entry(self.single_file_frame, width=50)
        self.input_file_entry.grid(row=0, column=0, pady=5, sticky=(tk.W, tk.E))
        ttk.Button(self.single_file_frame, text="찾아보기", command=self.browse_input_file).grid(row=0, column=1, padx=5)
        ttk.Button(self.single_file_frame, text="폴더 열기", command=self.open_input_file_folder).grid(row=0, column=2, padx=5)
        
        # 여러 파일 선택 UI
        self.multiple_files_frame = ttk.Frame(self.tab2)
        self.multiple_files_frame.grid(row=2, column=0, columnspan=4, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        files_control_frame = ttk.Frame(self.multiple_files_frame)
        files_control_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Button(files_control_frame, text="파일 추가", command=self.add_files).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(files_control_frame, text="파일 제거", command=self.remove_selected_files).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(files_control_frame, text="모두 제거", command=self.clear_all_files).pack(side=tk.LEFT, padx=(0, 5))
        
        # 파일 리스트박스
        list_frame = ttk.Frame(self.multiple_files_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        self.files_listbox = tk.Listbox(list_frame, height=6, selectmode=tk.EXTENDED)
        files_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.files_listbox.yview)
        self.files_listbox.configure(yscrollcommand=files_scrollbar.set)
        self.files_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        files_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.selected_files = []

        # 변환 옵션 및 버튼
        options_frame = ttk.Frame(self.tab2)
        options_frame.grid(row=3, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=10)
        
        ttk.Label(options_frame, text="변환할 확장자:").grid(row=0, column=0, sticky=tk.W, pady=5, padx=5)
        self.output_ext_var = tk.StringVar(value="mp3")
        self.output_ext_combo = ttk.Combobox(options_frame, textvariable=self.output_ext_var, width=10)
        self.output_ext_combo['values'] = ('mp4', 'mp3', 'mov', 'wav')
        self.output_ext_combo.grid(row=0, column=1, sticky=tk.W, pady=5)
        
        # 진행률 표시바
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(options_frame, variable=self.progress_var, maximum=100, length=200)
        self.progress_bar.grid(row=0, column=2, padx=10, sticky=(tk.W, tk.E))
        
        self.convert_btn = ttk.Button(options_frame, text="변환", command=self.start_convert)
        self.convert_btn.grid(row=0, column=3, padx=5)
        
        # 초기 모드 설정
        self.toggle_file_mode()

        # --- Status & Log ---
        self.status_label = ttk.Label(self.root, text="대기 중...", relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)

        log_frame = ttk.LabelFrame(self.root, text="로그", padding="5")
        log_frame.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.log_text = tk.Text(log_frame, height=8, width=80)
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Grid column/row weights for resizing
        for i in range(4):
            self.tab1.columnconfigure(i, weight=1)
            self.tab2.columnconfigure(i, weight=1)
        self.tab1.rowconfigure(10, weight=1)
        self.tab2.rowconfigure(2, weight=1)
        self.single_file_frame.columnconfigure(0, weight=1)
        options_frame.columnconfigure(2, weight=1)

    def browse_save_path(self):
        folder = filedialog.askdirectory(initialdir=str(Path.home() / "Downloads"))
        if folder:
            self.save_path_entry.delete(0, tk.END)
            self.save_path_entry.insert(0, folder)

    def toggle_file_mode(self):
        mode = self.file_mode_var.get()
        if mode == "single":
            self.single_file_frame.grid()
            self.multiple_files_frame.grid_remove()
        else:
            self.single_file_frame.grid_remove()
            self.multiple_files_frame.grid()
    
    def browse_input_file(self):
        file = filedialog.askopenfilename(
            title="변환할 파일 선택",
            filetypes=[("미디어 파일", "*.mp4 *.mp3 *.mov *.avi *.wav *.flv *.mkv"), ("모든 파일", "*.*")]
        )
        if file:
            self.input_file_entry.delete(0, tk.END)
            self.input_file_entry.insert(0, file)
    
    def add_files(self):
        files = filedialog.askopenfilenames(
            title="변환할 파일들 선택",
            filetypes=[("미디어 파일", "*.mp4 *.mp3 *.mov *.avi *.wav *.flv *.mkv"), ("모든 파일", "*.*")]
        )
        for file in files:
            if file not in self.selected_files:
                self.selected_files.append(file)
                self.files_listbox.insert(tk.END, os.path.basename(file))
    
    def remove_selected_files(self):
        selected_indices = list(self.files_listbox.curselection())
        selected_indices.reverse()
        for index in selected_indices:
            del self.selected_files[index]
            self.files_listbox.delete(index)
    
    def clear_all_files(self):
        self.selected_files.clear()
        self.files_listbox.delete(0, tk.END)
    
    def update_progress(self, current, total):
        progress = (current / total) * 100
        self.progress_var.set(progress)
        self.root.update()

    def log_message(self, message):
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.root.update()

    def set_status(self, message):
        self.status_label.config(text=message)
        self.root.update()

    def start_download(self):
        url = self.url_entry.get().strip()
        output_dir = self.save_path_entry.get().strip()
        format_type = self.format_var.get()
        if not url:
            messagebox.showerror("오류", "YouTube URL을 입력하세요.")
            return
        if not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir)
            except Exception as e:
                messagebox.showerror("오류", f"폴더 생성 실패: {str(e)}")
                return
        self.set_status("다운로드 중...")
        threading.Thread(target=download_youtube, args=(url, output_dir, format_type, self.log_message, self.set_status), daemon=True).start()

    def start_convert(self):
        output_ext = self.output_ext_var.get().strip().lower()
        mode = self.file_mode_var.get()
        
        if mode == "single":
            input_file = self.input_file_entry.get().strip()
            if not input_file or not os.path.exists(input_file):
                messagebox.showerror("오류", "입력 파일을 선택하세요.")
                return
            self.progress_var.set(0)
            self.set_status("변환 중...")
            threading.Thread(target=self._convert_single_file, args=(input_file, output_ext), daemon=True).start()
        else:
            if not self.selected_files:
                messagebox.showerror("오류", "변환할 파일을 선택하세요.")
                return
            
            valid_files = [f for f in self.selected_files if os.path.exists(f)]
            if not valid_files:
                messagebox.showerror("오류", "유효한 파일이 없습니다.")
                return
                
            self.progress_var.set(0)
            self.set_status(f"배치 변환 중... (0/{len(valid_files)})")
            threading.Thread(target=convert_media_batch, args=(valid_files, output_ext, self.log_message, self.set_status, self.update_progress), daemon=True).start()
    
    def _convert_single_file(self, input_file, output_ext):
        success, result = convert_media(input_file, output_ext, self.log_message)
        if success:
            self.progress_var.set(100)
            self.set_status("변환 완료!")
            messagebox.showinfo("완료", f"변환 완료: {result}")
        else:
            self.set_status("변환 오류")
            messagebox.showerror("오류", result)
        self.set_status("대기 중...")

    def open_download_folder(self):
        folder = self.save_path_entry.get().strip()
        if not os.path.exists(folder):
            messagebox.showerror("오류", "폴더가 존재하지 않습니다.")
            return
        try:
            if sys.platform == "win32":
                os.startfile(folder)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", folder])
            else:
                subprocess.Popen(["xdg-open", folder])
        except Exception as e:
            messagebox.showerror("오류", f"폴더를 열 수 없습니다: {e}")

    def open_input_file_folder(self):
        file_path = self.input_file_entry.get().strip()
        if not file_path or not os.path.exists(file_path):
            messagebox.showerror("오류", "입력 파일을 먼저 선택하세요.")
            return
        folder = os.path.dirname(file_path)
        if not os.path.exists(folder):
            messagebox.showerror("오류", "폴더가 존재하지 않습니다.")
            return
        try:
            if sys.platform == "win32":
                os.startfile(folder)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", folder])
            else:
                subprocess.Popen(["xdg-open", folder])
        except Exception as e:
            messagebox.showerror("오류", f"폴더를 열 수 없습니다: {e}")

def main():
    root = tk.Tk()
    app = MediaDownloaderConverterGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
