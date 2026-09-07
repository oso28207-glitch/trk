import os
import time
from datetime import datetime

TEMP_DIR = "temp_videos"

def clean_old_files(max_age_hours=24):
    """حذف جميع الملفات في المجلد المؤقت التي مضى على تعديلها أكثر من 24 ساعة"""
    now = time.time()
    deleted_count = 0
    for filename in os.listdir(TEMP_DIR):
        filepath = os.path.join(TEMP_DIR, filename)
        if os.path.isfile(filepath):
            file_age = now - os.path.getmtime(filepath)
            if file_age > max_age_hours * 3600:
                os.remove(filepath)
                deleted_count += 1
    return deleted_count

if __name__ == "__main__":
    count = clean_old_files()
    print(f"تم حذف {count} ملف قديم.")
