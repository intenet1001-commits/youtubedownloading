import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import yt_dlp
import os
import sys
import subprocess
from pathlib import Path
import threading
import re

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

def get_media_duration(input_file):
    """
    Get media file duration in seconds using ffprobe.
    """
    cmd = [
        'ffprobe',
        '-v', 'quiet',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        input_file
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        duration = float(result.stdout.strip())
        return duration
    except (subprocess.CalledProcessError, ValueError):
        return None

def parse_time_to_seconds(hours, minutes, seconds):
    """
    Convert hours, minutes, seconds to total seconds.
    """
    try:
        h = int(hours) if hours else 0
        m = int(minutes) if minutes else 0
        s = int(seconds) if seconds else 0
        return h * 3600 + m * 60 + s
    except ValueError:
        return None

def split_media_by_segments(input_file, num_segments, output_dir, log_callback, status_callback, progress_callback=None):
    """
    Split media file into specified number of segments using ffmpeg.
    """
    if not os.path.exists(input_file):
        log_callback(f"입력 파일이 존재하지 않습니다: {input_file}")
        return False, "입력 파일이 존재하지 않습니다"
    
    # Get total duration
    total_duration = get_media_duration(input_file)
    if total_duration is None:
        log_callback(f"미디어 파일의 길이를 가져올 수 없습니다: {input_file}")
        return False, "미디어 파일의 길이를 가져올 수 없습니다"
    
    # Calculate segment duration
    segment_duration = total_duration / num_segments
    log_callback(f"총 길이: {total_duration:.2f}초, {num_segments}개 구간으로 분할")
    log_callback(f"각 구간 길이: {segment_duration:.2f}초")
    
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Get file info for naming
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    file_ext = os.path.splitext(input_file)[1]
    
    successful = 0
    failed = 0
    
    for i in range(num_segments):
        start_time = i * segment_duration
        # For the last segment, use remaining duration to avoid cutting off
        if i == num_segments - 1:
            duration = total_duration - start_time
        else:
            duration = segment_duration
            
        output_file = os.path.join(output_dir, f"{base_name}_part{i+1:03d}{file_ext}")
        
        cmd = [
            'ffmpeg',
            '-y',  # overwrite
            '-i', input_file,
            '-ss', str(start_time),
            '-t', str(duration),
            '-c', 'copy',  # copy codec for faster processing
            output_file
        ]
        
        try:
            log_callback(f"구간 {i+1}/{num_segments} 분할 중... ({start_time:.1f}s ~ {start_time + duration:.1f}s)")
            status_callback(f"분할 중 ({i+1}/{num_segments})...")
            
            if progress_callback:
                progress_callback(i+1, num_segments)
            
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            log_callback(f"구간 {i+1} 완료: {output_file}")
            successful += 1
            
        except subprocess.CalledProcessError as e:
            log_callback(f"구간 {i+1} 분할 실패: {e}")
            failed += 1
    
    log_callback(f"\n분할 완료! 성공: {successful}, 실패: {failed}")
    status_callback(f"분할 완료! (성공: {successful}, 실패: {failed})")
    
    return failed == 0, f"성공: {successful}, 실패: {failed}"

def split_media_by_duration(input_file, segment_duration, output_dir, log_callback, status_callback, progress_callback=None):
    """
    Split media file into segments of specified duration using ffmpeg.
    """
    if not os.path.exists(input_file):
        log_callback(f"입력 파일이 존재하지 않습니다: {input_file}")
        return False, "입력 파일이 존재하지 않습니다"
    
    # Get total duration
    total_duration = get_media_duration(input_file)
    if total_duration is None:
        log_callback(f"미디어 파일의 길이를 가져올 수 없습니다: {input_file}")
        return False, "미디어 파일의 길이를 가져올 수 없습니다"
    
    # Calculate number of segments
    num_segments = int((total_duration + segment_duration - 1) // segment_duration)
    log_callback(f"총 길이: {total_duration:.2f}초, 분할 길이: {segment_duration}초")
    log_callback(f"총 {num_segments}개 구간으로 분할됩니다.")
    
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Get file info for naming
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    file_ext = os.path.splitext(input_file)[1]
    
    successful = 0
    failed = 0
    
    for i in range(num_segments):
        start_time = i * segment_duration
        output_file = os.path.join(output_dir, f"{base_name}_part{i+1:03d}{file_ext}")
        
        cmd = [
            'ffmpeg',
            '-y',  # overwrite
            '-i', input_file,
            '-ss', str(start_time),
            '-t', str(segment_duration),
            '-c', 'copy',  # copy codec for faster processing
            output_file
        ]
        
        try:
            log_callback(f"구간 {i+1}/{num_segments} 분할 중... ({start_time:.1f}s ~ {start_time + segment_duration:.1f}s)")
            status_callback(f"분할 중 ({i+1}/{num_segments})...")
            
            if progress_callback:
                progress_callback(i+1, num_segments)
            
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            log_callback(f"구간 {i+1} 완료: {output_file}")
            successful += 1
            
        except subprocess.CalledProcessError as e:
            log_callback(f"구간 {i+1} 분할 실패: {e}")
            failed += 1
    
    log_callback(f"\n분할 완료! 성공: {successful}, 실패: {failed}")
    status_callback(f"분할 완료! (성공: {successful}, 실패: {failed})")
    
    return failed == 0, f"성공: {successful}, 실패: {failed}"

def merge_media_files(input_files, output_file, log_callback, status_callback, progress_callback=None):
    """
    Merge multiple media files into one using ffmpeg.
    """
    if len(input_files) < 2:
        log_callback("합칠 파일이 최소 2개 이상 필요합니다.")
        return False, "합칠 파일이 최소 2개 이상 필요합니다."
    
    # Create a text file listing all input files
    temp_list_file = "temp_merge_list.txt"
    try:
        with open(temp_list_file, 'w', encoding='utf-8') as f:
            for input_file in input_files:
                if not os.path.exists(input_file):
                    log_callback(f"파일이 존재하지 않습니다: {input_file}")
                    return False, f"파일이 존재하지 않습니다: {input_file}"
                # Escape single quotes for ffmpeg
                escaped_path = input_file.replace("'", "'\"'\"'")
                f.write(f"file '{escaped_path}'\n")
        
        log_callback(f"총 {len(input_files)}개 파일을 합칩니다.")
        log_callback(f"출력 파일: {output_file}")
        
        # FFmpeg command to concatenate files
        cmd = [
            'ffmpeg',
            '-y',  # overwrite output file
            '-f', 'concat',
            '-safe', '0',
            '-i', temp_list_file,
            '-c', 'copy',  # copy streams without re-encoding for speed
            output_file
        ]
        
        status_callback("미디어 파일 합치는 중...")
        if progress_callback:
            progress_callback(1, 1)
        
        log_callback("합치기 시작...")
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        log_callback(f"합치기 완료: {output_file}")
        status_callback("합치기 완료!")
        
        if progress_callback:
            progress_callback(1, 1)
        
        return True, output_file
        
    except subprocess.CalledProcessError as e:
        error_msg = f"합치기 실패: {e.stderr if e.stderr else str(e)}"
        log_callback(error_msg)
        return False, error_msg
    except Exception as e:
        error_msg = f"합치기 중 오류 발생: {str(e)}"
        log_callback(error_msg)
        return False, error_msg
    finally:
        # Clean up temporary file
        if os.path.exists(temp_list_file):
            try:
                os.remove(temp_list_file)
            except:
                pass

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
        self.tab3 = ttk.Frame(tab_control)
        self.tab4 = ttk.Frame(tab_control)
        tab_control.add(self.tab1, text='YouTube 다운로드')
        tab_control.add(self.tab2, text='미디어 변환')
        tab_control.add(self.tab3, text='영상 분할')
        tab_control.add(self.tab4, text='미디어 합치기')
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

        # --- Tab 3: 영상 분할 ---
        ttk.Label(self.tab3, text="입력 파일:").grid(row=0, column=0, sticky=tk.W, pady=5, padx=5)
        self.split_input_entry = ttk.Entry(self.tab3, width=50)
        self.split_input_entry.grid(row=0, column=1, pady=5, sticky=(tk.W, tk.E))
        ttk.Button(self.tab3, text="찾아보기", command=self.browse_split_input).grid(row=0, column=2, padx=5)
        ttk.Button(self.tab3, text="폴더 열기", command=self.open_split_input_folder).grid(row=0, column=3, padx=5)

        # 분할 방식 선택
        ttk.Label(self.tab3, text="분할 방식:").grid(row=1, column=0, sticky=tk.W, pady=5, padx=5)
        self.split_mode_var = tk.StringVar(value="duration")
        ttk.Radiobutton(self.tab3, text="시간 간격", variable=self.split_mode_var, value="duration", command=self.toggle_split_mode).grid(row=1, column=1, sticky=tk.W)
        ttk.Radiobutton(self.tab3, text="구간 수", variable=self.split_mode_var, value="segments", command=self.toggle_split_mode).grid(row=1, column=2, sticky=tk.W)

        # 시간 간격 입력 프레임
        self.duration_frame = ttk.Frame(self.tab3)
        self.duration_frame.grid(row=2, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(self.duration_frame, text="분할 시간:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.hours_var = tk.StringVar(value="0")
        self.minutes_var = tk.StringVar(value="1")
        self.seconds_var = tk.StringVar(value="0")
        
        ttk.Entry(self.duration_frame, textvariable=self.hours_var, width=3).grid(row=0, column=1, padx=2)
        ttk.Label(self.duration_frame, text="시").grid(row=0, column=2, padx=2)
        ttk.Entry(self.duration_frame, textvariable=self.minutes_var, width=3).grid(row=0, column=3, padx=2)
        ttk.Label(self.duration_frame, text="분").grid(row=0, column=4, padx=2)
        ttk.Entry(self.duration_frame, textvariable=self.seconds_var, width=3).grid(row=0, column=5, padx=2)
        ttk.Label(self.duration_frame, text="초").grid(row=0, column=6, padx=2)

        # 구간 수 입력 프레임
        self.segments_frame = ttk.Frame(self.tab3)
        self.segments_frame.grid(row=3, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(self.segments_frame, text="구간 수:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.num_segments_var = tk.StringVar(value="5")
        ttk.Entry(self.segments_frame, textvariable=self.num_segments_var, width=10).grid(row=0, column=1, sticky=tk.W, padx=5)
        ttk.Label(self.segments_frame, text="개").grid(row=0, column=2, sticky=tk.W, padx=2)

        ttk.Label(self.tab3, text="출력 폴더:").grid(row=4, column=0, sticky=tk.W, pady=5, padx=5)
        self.split_output_entry = ttk.Entry(self.tab3, width=50)
        self.split_output_entry.insert(0, str(Path.home() / "Downloads" / "split"))
        self.split_output_entry.grid(row=4, column=1, pady=5, sticky=(tk.W, tk.E))
        ttk.Button(self.tab3, text="찾아보기", command=self.browse_split_output).grid(row=4, column=2, padx=5)
        ttk.Button(self.tab3, text="폴더 열기", command=self.open_split_output_folder).grid(row=4, column=3, padx=5)

        # 분할 진행률 표시바
        self.split_progress_var = tk.DoubleVar()
        self.split_progress_bar = ttk.Progressbar(self.tab3, variable=self.split_progress_var, maximum=100, length=300)
        self.split_progress_bar.grid(row=5, column=0, columnspan=3, pady=10, sticky=(tk.W, tk.E))

        self.split_btn = ttk.Button(self.tab3, text="분할", command=self.start_split)
        self.split_btn.grid(row=5, column=3, padx=5)

        # 초기 모드 설정
        self.toggle_split_mode()

        # --- Tab 4: 미디어 합치기 ---
        # 파일 목록 선택
        ttk.Label(self.tab4, text="합칠 파일들:").grid(row=0, column=0, sticky=(tk.W, tk.N), pady=5, padx=5)
        
        merge_files_frame = ttk.Frame(self.tab4)
        merge_files_frame.grid(row=0, column=1, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5, padx=5)
        
        # 파일 관리 버튼들
        merge_control_frame = ttk.Frame(merge_files_frame)
        merge_control_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Button(merge_control_frame, text="파일 추가", command=self.add_merge_files).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(merge_control_frame, text="파일 제거", command=self.remove_merge_files).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(merge_control_frame, text="모두 제거", command=self.clear_merge_files).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(merge_control_frame, text="위로", command=self.move_merge_file_up).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(merge_control_frame, text="아래로", command=self.move_merge_file_down).pack(side=tk.LEFT, padx=(0, 5))
        
        # 파일 리스트박스 (순서 조정 가능)
        merge_list_frame = ttk.Frame(merge_files_frame)
        merge_list_frame.pack(fill=tk.BOTH, expand=True)
        
        self.merge_files_listbox = tk.Listbox(merge_list_frame, height=8, selectmode=tk.EXTENDED)
        merge_scrollbar = ttk.Scrollbar(merge_list_frame, orient=tk.VERTICAL, command=self.merge_files_listbox.yview)
        self.merge_files_listbox.configure(yscrollcommand=merge_scrollbar.set)
        self.merge_files_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        merge_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.merge_file_list = []  # 합칠 파일 목록 저장
        
        # 출력 파일 설정
        ttk.Label(self.tab4, text="출력 파일:").grid(row=1, column=0, sticky=tk.W, pady=5, padx=5)
        self.merge_output_entry = ttk.Entry(self.tab4, width=50)
        self.merge_output_entry.grid(row=1, column=1, pady=5, sticky=(tk.W, tk.E))
        ttk.Button(self.tab4, text="찾아보기", command=self.browse_merge_output).grid(row=1, column=2, padx=5)
        ttk.Button(self.tab4, text="폴더 열기", command=self.open_merge_output_folder).grid(row=1, column=3, padx=5)
        
        # 합치기 진행률 표시바
        self.merge_progress_var = tk.DoubleVar()
        self.merge_progress_bar = ttk.Progressbar(self.tab4, variable=self.merge_progress_var, maximum=100, length=300)
        self.merge_progress_bar.grid(row=2, column=0, columnspan=3, pady=10, sticky=(tk.W, tk.E))
        
        self.merge_btn = ttk.Button(self.tab4, text="합치기", command=self.start_merge)
        self.merge_btn.grid(row=2, column=3, padx=5)

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
            self.tab3.columnconfigure(i, weight=1)
            self.tab4.columnconfigure(i, weight=1)
        self.tab1.rowconfigure(10, weight=1)
        self.tab2.rowconfigure(2, weight=1)
        self.tab3.rowconfigure(4, weight=1)
        self.tab4.rowconfigure(0, weight=1)
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

    def browse_split_input(self):
        file = filedialog.askopenfilename(
            title="분할할 영상 파일 선택",
            filetypes=[("비디오 파일", "*.mp4 *.mov *.avi *.mkv *.flv"), ("모든 파일", "*.*")]
        )
        if file:
            self.split_input_entry.delete(0, tk.END)
            self.split_input_entry.insert(0, file)

    def browse_split_output(self):
        folder = filedialog.askdirectory(initialdir=str(Path.home() / "Downloads"))
        if folder:
            self.split_output_entry.delete(0, tk.END)
            self.split_output_entry.insert(0, folder)

    def open_split_input_folder(self):
        file_path = self.split_input_entry.get().strip()
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

    def open_split_output_folder(self):
        folder = self.split_output_entry.get().strip()
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

    def toggle_split_mode(self):
        mode = self.split_mode_var.get()
        if mode == "duration":
            self.duration_frame.grid()
            self.segments_frame.grid_remove()
        else:
            self.duration_frame.grid_remove()
            self.segments_frame.grid()

    def update_split_progress(self, current, total):
        progress = (current / total) * 100
        self.split_progress_var.set(progress)
        self.root.update()

    def start_split(self):
        input_file = self.split_input_entry.get().strip()
        output_dir = self.split_output_entry.get().strip()
        mode = self.split_mode_var.get()
        
        if not input_file or not os.path.exists(input_file):
            messagebox.showerror("오류", "입력 파일을 선택하세요.")
            return
        
        if not output_dir:
            messagebox.showerror("오류", "출력 폴더를 선택하세요.")
            return
        
        if mode == "duration":
            # 시간 간격 모드
            total_seconds = parse_time_to_seconds(
                self.hours_var.get().strip(),
                self.minutes_var.get().strip(),
                self.seconds_var.get().strip()
            )
            
            if total_seconds is None or total_seconds <= 0:
                messagebox.showerror("오류", "올바른 시간을 입력하세요 (예: 0시 1분 30초)")
                return
            
            self.split_progress_var.set(0)
            self.set_status("영상 분할 중...")
            threading.Thread(target=self._split_video_by_duration, args=(input_file, total_seconds, output_dir), daemon=True).start()
            
        else:
            # 구간 수 모드
            try:
                num_segments = int(self.num_segments_var.get().strip())
                if num_segments <= 0:
                    raise ValueError("구간 수는 1 이상이어야 합니다.")
            except ValueError:
                messagebox.showerror("오류", "올바른 구간 수를 입력하세요 (예: 5)")
                return
            
            self.split_progress_var.set(0)
            self.set_status("영상 분할 중...")
            threading.Thread(target=self._split_video_by_segments, args=(input_file, num_segments, output_dir), daemon=True).start()

    def _split_video_by_duration(self, input_file, segment_duration, output_dir):
        success, result = split_media_by_duration(input_file, segment_duration, output_dir, self.log_message, self.set_status, self.update_split_progress)
        if success:
            self.split_progress_var.set(100)
            self.set_status("분할 완료!")
            messagebox.showinfo("완료", f"영상 분할 완료!\n{result}")
        else:
            self.set_status("분할 오류")
            messagebox.showerror("오류", result)
        self.set_status("대기 중...")

    def _split_video_by_segments(self, input_file, num_segments, output_dir):
        success, result = split_media_by_segments(input_file, num_segments, output_dir, self.log_message, self.set_status, self.update_split_progress)
        if success:
            self.split_progress_var.set(100)
            self.set_status("분할 완료!")
            messagebox.showinfo("완료", f"영상 분할 완료!\n{result}")
        else:
            self.set_status("분할 오류")
            messagebox.showerror("오류", result)
        self.set_status("대기 중...")

    # 미디어 합치기 관련 메서드들
    def add_merge_files(self):
        files = filedialog.askopenfilenames(
            title="합칠 파일들 선택",
            filetypes=[("미디어 파일", "*.mp4 *.mp3 *.mov *.avi *.wav *.flv *.mkv"), ("모든 파일", "*.*")]
        )
        for file in files:
            if file not in self.merge_file_list:
                self.merge_file_list.append(file)
                self.merge_files_listbox.insert(tk.END, os.path.basename(file))
    
    def remove_merge_files(self):
        selected_indices = list(self.merge_files_listbox.curselection())
        selected_indices.reverse()
        for index in selected_indices:
            del self.merge_file_list[index]
            self.merge_files_listbox.delete(index)
    
    def clear_merge_files(self):
        self.merge_file_list.clear()
        self.merge_files_listbox.delete(0, tk.END)
    
    def move_merge_file_up(self):
        selected_indices = list(self.merge_files_listbox.curselection())
        if not selected_indices:
            messagebox.showinfo("안내", "이동할 파일을 선택하세요.")
            return
        
        for index in selected_indices:
            if index > 0:
                # 리스트에서 항목 교체
                self.merge_file_list[index], self.merge_file_list[index-1] = self.merge_file_list[index-1], self.merge_file_list[index]
                
                # 리스트박스에서 항목 교체
                item = self.merge_files_listbox.get(index)
                self.merge_files_listbox.delete(index)
                self.merge_files_listbox.insert(index-1, item)
                
                # 선택 상태 유지
                self.merge_files_listbox.selection_clear(index)
                self.merge_files_listbox.selection_set(index-1)
    
    def move_merge_file_down(self):
        selected_indices = list(self.merge_files_listbox.curselection())
        if not selected_indices:
            messagebox.showinfo("안내", "이동할 파일을 선택하세요.")
            return
        
        # 아래로 이동할 때는 역순으로 처리
        selected_indices.reverse()
        for index in selected_indices:
            if index < len(self.merge_file_list) - 1:
                # 리스트에서 항목 교체
                self.merge_file_list[index], self.merge_file_list[index+1] = self.merge_file_list[index+1], self.merge_file_list[index]
                
                # 리스트박스에서 항목 교체
                item = self.merge_files_listbox.get(index)
                self.merge_files_listbox.delete(index)
                self.merge_files_listbox.insert(index+1, item)
                
                # 선택 상태 유지
                self.merge_files_listbox.selection_clear(index)
                self.merge_files_listbox.selection_set(index+1)
    
    def browse_merge_output(self):
        file = filedialog.asksaveasfilename(
            title="출력 파일 저장",
            defaultextension=".mp4",
            filetypes=[
                ("MP4 파일", "*.mp4"),
                ("MP3 파일", "*.mp3"),
                ("MOV 파일", "*.mov"),
                ("AVI 파일", "*.avi"),
                ("모든 파일", "*.*")
            ]
        )
        if file:
            self.merge_output_entry.delete(0, tk.END)
            self.merge_output_entry.insert(0, file)
    
    def open_merge_output_folder(self):
        output_path = self.merge_output_entry.get().strip()
        if not output_path:
            messagebox.showerror("오류", "출력 파일 경로를 먼저 설정하세요.")
            return
        
        folder = os.path.dirname(output_path)
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
    
    def update_merge_progress(self, current, total):
        progress = (current / total) * 100
        self.merge_progress_var.set(progress)
        self.root.update()
    
    def start_merge(self):
        if len(self.merge_file_list) < 2:
            messagebox.showerror("오류", "합칠 파일을 최소 2개 이상 선택하세요.")
            return
        
        output_file = self.merge_output_entry.get().strip()
        if not output_file:
            messagebox.showerror("오류", "출력 파일 경로를 설정하세요.")
            return
        
        # 출력 디렉토리 생성
        output_dir = os.path.dirname(output_file)
        if not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir)
            except Exception as e:
                messagebox.showerror("오류", f"출력 폴더 생성 실패: {str(e)}")
                return
        
        # 파일 존재 확인
        valid_files = []
        for file_path in self.merge_file_list:
            if os.path.exists(file_path):
                valid_files.append(file_path)
            else:
                self.log_message(f"파일을 찾을 수 없습니다: {file_path}")
        
        if len(valid_files) < 2:
            messagebox.showerror("오류", "유효한 파일이 2개 미만입니다.")
            return
        
        self.merge_progress_var.set(0)
        self.set_status("미디어 합치는 중...")
        threading.Thread(target=self._merge_files, args=(valid_files, output_file), daemon=True).start()
    
    def _merge_files(self, input_files, output_file):
        success, result = merge_media_files(input_files, output_file, self.log_message, self.set_status, self.update_merge_progress)
        if success:
            self.merge_progress_var.set(100)
            self.set_status("합치기 완료!")
            messagebox.showinfo("완료", f"미디어 합치기 완료!\n출력: {result}")
        else:
            self.set_status("합치기 오류")
            messagebox.showerror("오류", result)
        self.set_status("대기 중...")

def main():
    root = tk.Tk()
    app = MediaDownloaderConverterGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
