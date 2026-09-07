import os
import subprocess
import requests
import time
import re
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

TEMP_DIR = "temp_videos"
os.makedirs(TEMP_DIR, exist_ok=True)

def download_and_compress(video_url, task_id, progress_callback=None):
    """تحميل الفيديو وضغطه إلى 144p"""
    try:
        temp_input = os.path.join(TEMP_DIR, f"{task_id}_input.mp4")
        temp_output = os.path.join(TEMP_DIR, f"{task_id}_144p.mp4")

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://esheq1.store/',
            'Origin': 'https://esheq1.store',
        }

        if progress_callback:
            progress_callback("بدء التحميل...", 40)

        # استخدام yt-dlp للتحميل (يدعم m3u8 بشكل أفضل)
        import yt_dlp
        ydl_opts = {
            'format': 'best[height<=720]/best',
            'outtmpl': temp_input,
            'quiet': False,
            'retries': 10,
            'fragment_retries': 10,
            'socket_timeout': 30,
            'http_headers': headers,
            'extractor_args': {'generic': ['impersonate']},
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])

        if not os.path.exists(temp_input) or os.path.getsize(temp_input) == 0:
            raise Exception("فشل التحميل: الملف فارغ")

        if progress_callback:
            progress_callback("اكتمل التحميل، جارٍ الضغط...", 65)

        # ضغط الفيديو إلى 144p
        cmd_compress = [
            'ffmpeg', '-i', temp_input,
            '-vf', 'scale=-2:144',
            '-c:v', 'libx264', '-preset', 'fast', '-crf', '28',
            '-c:a', 'aac', '-b:a', '64k',
            temp_output, '-y'
        ]
        process = subprocess.Popen(cmd_compress, stderr=subprocess.PIPE, universal_newlines=True)

        for line in process.stderr:
            if 'time=' in line:
                if progress_callback:
                    current = 65
                    if current < 95:
                        current += 0.3
                        progress_callback("ضغط الفيديو...", min(current, 95))

        process.wait()
        if process.returncode != 0:
            raise Exception("فشل في الضغط")

        if os.path.exists(temp_input):
            os.remove(temp_input)

        if progress_callback:
            progress_callback("اكتمل! جاهز للمشاهدة.", 100)

        return temp_output

    except Exception as e:
        if progress_callback:
            progress_callback(f"خطأ: {str(e)}", -1)
        raise
