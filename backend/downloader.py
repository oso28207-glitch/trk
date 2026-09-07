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
    تحميل الفيديو وضغطه مع دعم .mp4 و .m3u8، مع تجاوز 403.
    """
    try:
        temp_input = os.path.join(TEMP_DIR, f"{task_id}_input.mp4")
        temp_output = os.path.join(TEMP_DIR, f"{task_id}_144p.mp4")

        # رؤوس أساسية
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://esheq1.store/',
            'Origin': 'https://esheq1.store',
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        }

        if progress_callback:
            progress_callback("بدء التحميل...", 40)

        # إذا كان الرابط بصيغة m3u8، نستخدم ffmpeg مع رؤوس مخصصة
        if video_url.endswith('.m3u8'):
            if progress_callback:
                progress_callback("تحميل تدفق HLS (m3u8)...", 45)
            
            # بناء رؤوس ffmpeg بصيغة مطلوبة
            ff_headers = f"Referer: https://esheq1.store/\r\nUser-Agent: {headers['User-Agent']}\r\n"
            cmd = [
                'ffmpeg',
                '-headers', ff_headers,
                '-i', video_url,
                '-c', 'copy',
                '-bsf:a', 'aac_adtstoasc',
                temp_input,
                '-y'
            ]
            process = subprocess.Popen(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                # محاولة بديلة: استخدام -user_agent مباشرة
                cmd2 = [
                    'ffmpeg',
                    '-user_agent', headers['User-Agent'],
                    '-i', video_url,
                    '-c', 'copy',
                    '-bsf:a', 'aac_adtstoasc',
                    temp_input,
                    '-y'
                ]
                process2 = subprocess.Popen(cmd2, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
                stdout2, stderr2 = process2.communicate()
                if process2.returncode != 0:
                    raise Exception(f"فشل تحميل m3u8: {stderr2.decode()}")
                # إذا نجح، نواصل

        else:
            # تحميل مباشر باستخدام requests
            session = requests.Session()
            session.headers.update(headers)
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
                        else:
                            if progress_callback:
                                progress_callback("تحميل...", min(40 + (downloaded // 1024 // 1024), 60))

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
