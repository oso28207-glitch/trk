import os
import subprocess
import requests
import json
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

TEMP_DIR = "temp_videos"
os.makedirs(TEMP_DIR, exist_ok=True)

def download_and_compress(video_url, task_id, progress_callback=None):
    """
    تحميل الفيديو باستخدام yt-dlp (يدعم m3u8 والتواقيت) وضغطه إلى 144p.
    """
    try:
        temp_input = os.path.join(TEMP_DIR, f"{task_id}_input.mp4")
        temp_output = os.path.join(TEMP_DIR, f"{task_id}_144p.mp4")

        if progress_callback:
            progress_callback("جارٍ تحليل الرابط...", 30)

        # ✅ استخدام yt-dlp للتحميل (يتعامل مع 403 والتواقيت)
        if progress_callback:
            progress_callback("تحميل الفيديو عبر yt-dlp...", 40)

        # تحضير أمر yt-dlp مع رؤوس إضافية
        cmd = [
            'yt-dlp',
            '-o', temp_input,
            '--no-progress',
            '--hls-prefer-native',
            '--add-header', f'Referer: https://esheq1.store/',
            '--add-header', f'Origin: https://esheq1.store',
            '--add-header', 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            '--retries', '5',
            '--fragment-retries', '5',
            '--no-check-certificate',
            video_url
        ]

        # تشغيل الأمر مع وقت كافي (5 دقائق)
        subprocess.run(cmd, check=True, capture_output=True, timeout=300)

        # التحقق من وجود الملف
        if not os.path.exists(temp_input) or os.path.getsize(temp_input) == 0:
            raise Exception("فشل التحميل: الملف الناتج فارغ أو غير موجود")

        if progress_callback:
            progress_callback("اكتمل التحميل، جارٍ الضغط إلى 144p...", 65)

        # ✅ ضغط الفيديو إلى 144p
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
            raise Exception("الخادم يرفض الاتصال (403). قد يكون الرابط منتهي الصلاحية أو يتطلب مصادقة.")
        raise Exception(f"فشل تحميل الفيديو: {error_msg[:200]}")
    except subprocess.TimeoutExpired:
        raise Exception("انتهت مهلة التحميل (أكثر من 5 دقائق).")
    except Exception as e:
        raise Exception(f"خطأ غير متوقع: {str(e)}")
