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

def convert_media(input_file, output_ext, log_callback, status_callback):
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
        status_callback("변환 완료!")
        messagebox.showinfo("완료", f"변환 완료: {output_file}")
    except subprocess.CalledProcessError as e:
        log_callback(f"변환 실패: {e}")
        status_callback("변환 오류")
        messagebox.showerror("오류", str(e))
    finally:
        status_callback("대기 중...")

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
        self.input_file_entry = ttk.Entry(self.tab2, width=50)
        self.input_file_entry.grid(row=0, column=1, pady=5)
        ttk.Button(self.tab2, text="찾아보기", command=self.browse_input_file).grid(row=0, column=2, padx=5)
        ttk.Button(self.tab2, text="폴더 열기", command=self.open_input_file_folder).grid(row=0, column=3, padx=5)

        ttk.Label(self.tab2, text="변환할 확장자:").grid(row=1, column=0, sticky=tk.W, pady=5, padx=5)
        self.output_ext_var = tk.StringVar(value="mp3")
        self.output_ext_combo = ttk.Combobox(self.tab2, textvariable=self.output_ext_var, width=10)
        self.output_ext_combo['values'] = ('mp4', 'mp3', 'mov', 'wav')
        self.output_ext_combo.grid(row=1, column=1, sticky=tk.W, pady=5)

        self.convert_btn = ttk.Button(self.tab2, text="변환", command=self.start_convert)
        self.convert_btn.grid(row=2, column=0, columnspan=3, pady=10)

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
        self.tab1.rowconfigure(10, weight=1)

    def browse_save_path(self):
        folder = filedialog.askdirectory(initialdir=str(Path.home() / "Downloads"))
        if folder:
            self.save_path_entry.delete(0, tk.END)
            self.save_path_entry.insert(0, folder)

    def browse_input_file(self):
        file = filedialog.askopenfilename()
        if file:
            self.input_file_entry.delete(0, tk.END)
            self.input_file_entry.insert(0, file)

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
        input_file = self.input_file_entry.get().strip()
        output_ext = self.output_ext_var.get().strip().lower()
        if not input_file or not os.path.exists(input_file):
            messagebox.showerror("오류", "입력 파일을 선택하세요.")
            return
        self.set_status("변환 중...")
        threading.Thread(target=convert_media, args=(input_file, output_ext, self.log_message, self.set_status), daemon=True).start()

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
