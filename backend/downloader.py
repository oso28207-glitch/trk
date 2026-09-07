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
    """
    تحميل الفيديو وضغطه مع تحديث التقدم عبر progress_callback(text, percent)
    """
    try:
        temp_input = os.path.join(TEMP_DIR, f"{task_id}_input.mp4")
        temp_output = os.path.join(TEMP_DIR, f"{task_id}_144p.mp4")

        # إعداد جلسة مع إعادة المحاولة
        session = requests.Session()
        retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retries)
        session.mount('http://', adapter)
        session.mount('https://', adapter)

        # 1. تحميل الفيديو
        if progress_callback:
            progress_callback("بدء التحميل...", 40)
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
                    else:
                        # إذا لم نعرف الحجم، نزيد تدريجياً
                        current = 40
                        if progress_callback:
                            progress_callback("تحميل...", min(current, 60))

        if progress_callback:
            progress_callback("اكتمل التحميل، جارٍ الضغط...", 65)

        # 2. ضغط الفيديو إلى 144p
        cmd = [
            'ffmpeg', '-i', temp_input,
            '-vf', 'scale=-2:144',
            '-c:v', 'libx264', '-preset', 'fast', '-crf', '28',
            '-c:a', 'aac', '-b:a', '64k',
            temp_output, '-y'
        ]
        process = subprocess.Popen(cmd, stderr=subprocess.PIPE, universal_newlines=True)

        # قراءة تقدم ffmpeg من stderr وتحديثه من 65% إلى 95%
        for line in process.stderr:
            if 'time=' in line:
                # تقدير النسبة (يمكن تحسينه باستخراج الوقت الفعلي)
                if progress_callback:
                    current_progress = 65
                    if current_progress < 95:
                        # نزيد تدريجياً
                        progress_callback("ضغط الفيديو...", min(current_progress + 0.5, 95))

        process.wait()
        if process.returncode != 0:
            raise Exception("فشل في ضغط الفيديو بواسطة ffmpeg")

        # حذف الملف المؤقت
        if os.path.exists(temp_input):
            os.remove(temp_input)

        if progress_callback:
            progress_callback("اكتمل الضغط! جاهز للمشاهدة.", 100)

        return temp_output

    except Exception as e:
        if progress_callback:
            progress_callback(f"خطأ: {str(e)}", -1)
        raise
