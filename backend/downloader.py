import os
import subprocess
import requests
import time
import re
import json
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

TEMP_DIR = "temp_videos"
os.makedirs(TEMP_DIR, exist_ok=True)

def download_and_compress(video_url, task_id, progress_callback=None):
    """
    تحميل الفيديو باستخدام yt-dlp (أو ffmpeg كخيار احتياطي) وضغطه إلى 144p.
    """
    try:
        temp_input = os.path.join(TEMP_DIR, f"{task_id}_input.mp4")
        temp_output = os.path.join(TEMP_DIR, f"{task_id}_144p.mp4")

        if progress_callback:
            progress_callback("جارٍ تحليل الرابط...", 30)

        # ✅ استخدام yt-dlp للتحميل (يدعم m3u8 و 403 bypass)
        if video_url.endswith('.m3u8'):
            if progress_callback:
                progress_callback("تحميل تدفق HLS باستخدام yt-dlp...", 40)

            # إعداد أمر yt-dlp مع الرؤوس المطلوبة
            cmd = [
                'yt-dlp',
                '-o', temp_input,
                '--no-progress',
                '--hls-prefer-native',  # استخدام المحلل الأصلي لـ HLS
                '--add-header', 'Referer:https://esheq1.store/',
                '--add-header', 'Origin:https://esheq1.store',
                '--add-header', 'User-Agent:Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                '--retries', '10',
                '--fragment-retries', '10',
                '--no-check-certificate',
                video_url
            ]
            subprocess.run(cmd, check=True, capture_output=True, timeout=300)

        else:
            # تحميل مباشر باستخدام requests (للملفات العادية)
            if progress_callback:
                progress_callback("تحميل ملف مباشر...", 40)

            session = requests.Session()
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://esheq1.store/',
                'Origin': 'https://esheq1.store',
            })
            retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
            adapter = HTTPAdapter(max_retries=retries)
            session.mount('http://', adapter)
            session.mount('https://', adapter)

            response = session.get(video_url, stream=True, timeout=(15, 60))
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            with open(temp_input, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            percent = int((downloaded / total_size) * 20) + 40
                            if progress_callback:
                                progress_callback(f"تحميل: {percent-40}%", min(percent, 60))

        if not os.path.exists(temp_input) or os.path.getsize(temp_input) == 0:
            raise Exception("فشل التحميل: الملف الناتج فارغ أو غير موجود")

        if progress_callback:
            progress_callback("اكتمل التحميل، جارٍ الضغط إلى 144p...", 65)

        # ✅ ضغط الفيديو إلى 144p (نفس الخطوات السابقة)
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
                    # نزيد تدريجياً من 65 إلى 95
                    current = 65
                    if current < 95:
                        current += 0.3
                        progress_callback("ضغط الفيديو...", min(current, 95))

        process.wait()
        if process.returncode != 0:
            raise Exception("فشل في ضغط الفيديو بواسطة ffmpeg")

        # حذف الملف المؤقت
        if os.path.exists(temp_input):
            os.remove(temp_input)

        if progress_callback:
            progress_callback("اكتمل! جاهز للمشاهدة.", 100)

        return temp_output

    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode('utf-8') if e.stderr else str(e)
        if '403' in error_msg or 'Forbidden' in error_msg:
            raise Exception("الخادم يرفض الاتصال (403). قد يكون الرابط منتهي الصلاحية.")
        raise Exception(f"فشل تحميل m3u8: {error_msg[:200]}")
    except Exception as e:
        raise Exception(f"خطأ في التحميل أو الضغط: {str(e)}")
