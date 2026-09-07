import os
import subprocess
import requests
import time
import re
import threading

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

        # 1. تحميل الفيديو باستخدام Stream (لتحديث التقدم)
        response = requests.get(download_url, stream=True, timeout=30)
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0

        with open(temp_input, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        percent = int((downloaded / total_size) * 20) + 5  # من 5% إلى 25%
                        tasks[task_id]['progress'] = min(percent, 25)

        tasks[task_id]['status'] = 'converting'
        tasks[task_id]['progress'] = 30

        # 2. ضغط الفيديو إلى 144p باستخدام ffmpeg
        # نتتبع تقدم ffmpeg عبر تحليل stderr
        cmd = [
            'ffmpeg', '-i', temp_input,
            '-vf', 'scale=-2:144',
            '-c:v', 'libx264', '-preset', 'fast', '-crf', '28',
            '-c:a', 'aac', '-b:a', '64k',
            temp_output, '-y'
        ]

        process = subprocess.Popen(cmd, stderr=subprocess.PIPE, universal_newlines=True)

        # قراءة تقدم ffmpeg من stderr
        for line in process.stderr:
            if 'time=' in line:
                # استخراج الوقت المحدد (مثل time=00:00:05.12)
                time_match = re.search(r'time=(\d+):(\d+):(\d+\.\d+)', line)
                if time_match:
                    # يمكننا تقدير النسبة بناءً على مدة الفيديو، لكننا سنحاكي تقدماً ثابتاً
                    # بدلاً من التحليل المعقد، سنرفع النسبة تدريجياً من 30% إلى 95%
                    current_progress = tasks[task_id]['progress']
                    if current_progress < 90:
                        tasks[task_id]['progress'] = min(current_progress + 0.5, 90)

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

    except Exception as e:
        tasks[task_id]['status'] = 'error'
        tasks[task_id]['error'] = str(e)
        print(f"خطأ في معالجة الحلقة {episode_id}: {e}")
