def download_and_compress(video_url, task_id, progress_callback=None):
    try:
        temp_input = os.path.join(TEMP_DIR, f"{task_id}_input.mp4")
        temp_output = os.path.join(TEMP_DIR, f"{task_id}_144p.mp4")

        # ✅ إعداد رؤوس خاصة لتجاوز 403
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://esheq1.store/',
            'Origin': 'https://esheq1.store',
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        }

        session = requests.Session()
        session.headers.update(headers)

        # إذا كان الرابط بصيغة .m3u8، نستخدم ffmpeg مباشرة للتحميل
        if video_url.endswith('.m3u8'):
            if progress_callback:
                progress_callback("تحميل تدفق HLS (m3u8)...", 40)
            # استخدام ffmpeg لتحميل m3u8 وتحويله مباشرة
            cmd = [
                'ffmpeg', '-headers', f'Referer: https://esheq1.store/\r\n',
                '-i', video_url,
                '-c', 'copy', '-bsf:a', 'aac_adtstoasc',
                temp_input, '-y'
            ]
            subprocess.run(cmd, check=True)
        else:
            # تحميل مباشر للملفات العادية
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

        # ... باقي الكود (الضغط إلى 144p) كما هو ...
    except Exception as e:
        raise
