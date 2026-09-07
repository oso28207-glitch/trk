import requests

BASE_URL = "https://esheq1.store/wp-json/esheeq/v1"

def get_all_series():
    """جلب قائمة جميع المسلسلات"""
    try:
        response = requests.get(f"{BASE_URL}/series", timeout=15)
        response.raise_for_status()
        data = response.json()
        return data.get("series", [])
    except Exception as e:
        print(f"خطأ في جلب المسلسلات: {e}")
        return []

def get_series_episodes(series_id):
    """جلب حلقات مسلسل معين باستخدام الـ ID الرقمي"""
    try:
        response = requests.get(f"{BASE_URL}/series/{series_id}/episodes", timeout=15)
        response.raise_for_status()
        data = response.json()
        return data.get("episodes", [])
    except Exception as e:
        print(f"خطأ في جلب الحلقات: {e}")
        return []

def get_video_download_url(episode_id):
    """الحصول على رابط التحميل المباشر بصيغة MP4 من معرف الحلقة"""
    try:
        response = requests.get(f"{BASE_URL}/get-video/{episode_id}", timeout=15)
        response.raise_for_status()
        data = response.json()
        # نفضل روابط MP4 على M3U8 لأنها أسهل للضغط
        mp4_urls = data.get("video_urls", {}).get("mp4", [])
        if mp4_urls:
            return mp4_urls[0]  # خذ أول رابط MP4
        return None
    except Exception as e:
        print(f"خطأ في جلب رابط الفيديو: {e}")
        return None
