# backend/downloader.py
import os
import subprocess
import requests
import time
import re
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# المجلد المؤقت
TEMP_DIR = "temp_videos"
os.makedirs(TEMP_DIR, exist_ok=True)

# قاموس لتخزين حالة المهام (سيتم تمريره من app.py)
tasks = {}

def download_and_compress(episode_id, download_url, task_id):
    """
    تحميل الفيديو وضغطه مع تحديث التقدم في قاموس tasks
    """
    try:
        # تحديث الحالة: بدء التحميل
        tasks[task_id]['status'] = 'downloading'
        tasks[task_id]['progress'] = 5

        # مسارات الملفات
        temp_input = os.path.join(TEMP_DIR, f"{task_id}_input.mp4")
        temp_output = os.path.join(TEMP_DIR, f"{task_id}_144p.mp4")

        # إعداد جلسة مع إعادة المحاولة التلقائية وزيادة المهلة
        session = requests.Session()
        retries = Retry(
            total=5,
            backoff_factor=1,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET"]
        )
        adapter = HTTPAdapter(max_retries=retries)
        session.mount('http://', adapter)
        session.mount('https://', adapter)

        # 1. تحميل الفيديو باستخدام Stream مع مهلة أطول
        tasks[task_id]['status'] = 'downloading'
        tasks[task_id]['progress'] = 5

        response = session.get(
            download_url,
            stream=True,
            timeout=(15, 60)  # (اتصال, قراءة) مهلة
        )
        response.raise_for_status()

        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        chunk_size = 8192

        with open(temp_input, 'wb') as f:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        # تحديث التقدم: 5% إلى 30% للتحميل
                        percent = int((downloaded / total_size) * 25) + 5
                        tasks[task_id]['progress'] = min(percent, 30)
                    else:
                        # إذا لم نعرف الحجم، نزيد تدريجياً حتى 30%
                        current = tasks[task_id]['progress']
                        if current < 30:
                            tasks[task_id]['progress'] = min(current + 0.5, 30)

        tasks[task_id]['status'] = 'converting'
        tasks[task_id]['progress'] = 35

        # 2. ضغط الفيديو إلى 144p باستخدام ffmpeg
        # نستخدم -y لتجاوز التأكيد
        cmd = [
            'ffmpeg', '-i', temp_input,
            '-vf', 'scale=-2:144',
            '-c:v', 'libx264', '-preset', 'fast', '-crf', '28',
            '-c:a', 'aac', '-b:a', '64k',
            temp_output, '-y'
        ]

        process = subprocess.Popen(cmd, stderr=subprocess.PIPE, universal_newlines=True)

        # قراءة تقدم ffmpeg من stderr وتحديثه من 35% إلى 95%
        for line in process.stderr:
            if 'time=' in line:
                # استخراج الوقت المحدد (مثل time=00:00:05.12)
                time_match = re.search(r'time=(\d+):(\d+):(\d+\.\d+)', line)
                if time_match:
                    # تقدير النسبة بناءً على الوقت، لكننا سنكتفي بزيادة تدريجية
                    current_progress = tasks[task_id]['progress']
                    if current_progress < 95:
                        tasks[task_id]['progress'] = min(current_progress + 0.5, 95)

        process.wait()

        if process.returncode != 0:
            raise Exception("فشل في ضغط الفيديو بواسطة ffmpeg")

        # حذف الملف المؤقت الأصلي (المرفوع)
        if os.path.exists(temp_input):
            os.remove(temp_input)

        # تحديث الحالة: اكتمل
        tasks[task_id]['status'] = 'completed'
        tasks[task_id]['progress'] = 100
        tasks[task_id]['file_path'] = temp_output

        # تنظيف الملفات القديمة (اختياري) - يمكن استدعاء cleaner هنا
        # لكننا نفضل تركه للمجدول

    except requests.exceptions.Timeout as e:
        tasks[task_id]['status'] = 'error'
        tasks[task_id]['error'] = f"انتهت مهلة الاتصال: {str(e)}"
        print(f"Timeout error for episode {episode_id}: {e}")

    except requests.exceptions.RequestException as e:
        tasks[task_id]['status'] = 'error'
        tasks[task_id]['error'] = f"خطأ في التحميل: {str(e)}"
        print(f"Request error for episode {episode_id}: {e}")

    except subprocess.CalledProcessError as e:
        tasks[task_id]['status'] = 'error'
        tasks[task_id]['error'] = f"خطأ في ffmpeg: {str(e)}"
        print(f"FFmpeg error for episode {episode_id}: {e}")

    except Exception as e:
        tasks[task_id]['status'] = 'error'
        tasks[task_id]['error'] = f"خطأ غير متوقع: {str(e)}"
        print(f"Unexpected error for episode {episode_id}: {e}")

    finally:
        # تنظيف الملف المؤقت إذا بقي
        if os.path.exists(temp_input):
            try:
                os.remove(temp_input)
            except:
                pass
