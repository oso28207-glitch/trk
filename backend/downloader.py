import os
import subprocess
import requests
import time
import re
import m3u8
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import json

TEMP_DIR = "temp_videos"
os.makedirs(TEMP_DIR, exist_ok=True)

def download_with_ytdlp(video_url, output_path, progress_callback=None):
    """محاولة التحميل باستخدام yt-dlp"""
    try:
        cmd = [
            'yt-dlp',
            '-o', output_path,
            '--no-progress',
            '--hls-prefer-native',
            '--add-header', 'Referer: https://esheq1.store/',
            '--add-header', 'Origin: https://esheq1.store',
            '--add-header', 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            '--retries', '10',
            '--fragment-retries', '10',
            '--no-check-certificate',
            video_url
        ]
        subprocess.run(cmd, check=True, capture_output=True, timeout=300)
        return True
    except Exception as e:
        print(f"yt-dlp فشل: {e}")
        return False

def download_with_ffmpeg_headers(video_url, output_path, progress_callback=None):
    """محاولة التحميل باستخدام ffmpeg مع -headers"""
    try:
        headers = "Referer: https://esheq1.store/\r\nOrigin: https://esheq1.store\r\nUser-Agent: Mozilla/5.0"
        cmd = [
            'ffmpeg',
            '-headers', headers,
            '-i', video_url,
            '-c', 'copy',
            '-bsf:a', 'aac_adtstoasc',
            output_path,
            '-y'
        ]
        subprocess.run(cmd, check=True, capture_output=True, timeout=300)
        return True
    except Exception as e:
        print(f"ffmpeg with headers فشل: {e}")
        return False

def download_with_requests_and_ffmpeg(video_url, output_path, progress_callback=None):
    """تنزيل m3u8 باستخدام requests ثم تحويله ب ffmpeg"""
    try:
        # نضبط الرؤوس
        headers = {
            'Referer': 'https://esheq1.store/',
            'Origin': 'https://esheq1.store',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        session = requests.Session()
        session.headers.update(headers)
        
        # نحصل على محتوى m3u8
        resp = session.get(video_url, timeout=30)
        resp.raise_for_status()
        m3u8_content = resp.text
        
        # نبحث عن روابط المقاطع
        # نقوم بتنزيل كل مقطع ثم دمجها (معقد) لذا نفضل استخدام ffmpeg مع -i
        # لكن يمكننا حفظ الملف m3u8 محلياً واستخدامه
        m3u8_path = output_path + ".m3u8"
        with open(m3u8_path, 'w') as f:
            f.write(m3u8_content)
        
        # استخدام ffmpeg لتحويل الملف
        cmd = [
            'ffmpeg',
            '-headers', f'Referer: https://esheq1.store/\r\n',
            '-i', m3u8_path,
            '-c', 'copy',
            output_path,
            '-y'
        ]
        subprocess.run(cmd, check=True, capture_output=True, timeout=300)
        os.remove(m3u8_path)
        return True
    except Exception as e:
        print(f"Requests + ffmpeg فشل: {e}")
        return False

def download_video(video_url, output_path, progress_callback=None):
    """محاولة التحميل بعدة طرق"""
    # الطريقة 1: yt-dlp
    if download_with_ytdlp(video_url, output_path, progress_callback):
        return True
    
    # الطريقة 2: ffmpeg مع headers
    if download_with_ffmpeg_headers(video_url, output_path, progress_callback):
        return True
    
    # الطريقة 3: requests + ffmpeg
    if download_with_requests_and_ffmpeg(video_url, output_path, progress_callback):
        return True
    
    return False

def download_and_compress(video_url, task_id, progress_callback=None):
    try:
        temp_input = os.path.join(TEMP_DIR, f"{task_id}_input.mp4")
        temp_output = os.path.join(TEMP_DIR, f"{task_id}_144p.mp4")

        if progress_callback:
            progress_callback("جارٍ محاولة التحميل...", 30)

        # تحميل الفيديو
        success = download_video(video_url, temp_input, progress_callback)
        if not success:
            raise Exception("فشلت جميع طرق التحميل")

        if not os.path.exists(temp_input) or os.path.getsize(temp_input) == 0:
            raise Exception("الملف المحمل فارغ")

        if progress_callback:
            progress_callback("اكتمل التحميل، جارٍ الضغط...", 65)

        # ضغط الفيديو
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
            raise Exception("فشل الضغط")

        if os.path.exists(temp_input):
            os.remove(temp_input)

        if progress_callback:
            progress_callback("اكتمل! جاهز للمشاهدة.", 100)

        return temp_output

    except Exception as e:
        raise Exception(f"خطأ: {str(e)}")
