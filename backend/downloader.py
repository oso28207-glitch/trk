import os
import subprocess
import requests
import time

TEMP_DIR = "temp_videos"
os.makedirs(TEMP_DIR, exist_ok=True)

tasks = {}

def download_and_compress(episode_id, download_url, task_id):
    try:
        tasks[task_id]['status'] = 'downloading'
        tasks[task_id]['progress'] = 5

        temp_input = os.path.join(TEMP_DIR, f"{task_id}_input.mp4")
        temp_output = os.path.join(TEMP_DIR, f"{task_id}_144p.mp4")

        response = requests.get(download_url, stream=True, timeout=30)
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0

        with open(temp_input, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        percent = int((downloaded / total_size) * 20) + 5
                        tasks[task_id]['progress'] = min(percent, 25)

        tasks[task_id]['status'] = 'converting'
        tasks[task_id]['progress'] = 30

        cmd = [
            'ffmpeg', '-i', temp_input,
            '-vf', 'scale=-2:144',
            '-c:v', 'libx264', '-preset', 'fast', '-crf', '28',
            '-c:a', 'aac', '-b:a', '64k',
            temp_output, '-y'
        ]
        process = subprocess.Popen(cmd, stderr=subprocess.PIPE, universal_newlines=True)
        for line in process.stderr:
            if 'time=' in line:
                tasks[task_id]['progress'] = min(tasks[task_id]['progress'] + 0.5, 90)
        process.wait()

        if process.returncode != 0:
            raise Exception("فشل في الضغط")

        if os.path.exists(temp_input):
            os.remove(temp_input)

        tasks[task_id]['status'] = 'completed'
        tasks[task_id]['progress'] = 100
        tasks[task_id]['file_path'] = temp_output

    except Exception as e:
        tasks[task_id]['status'] = 'error'
        tasks[task_id]['error'] = str(e)
