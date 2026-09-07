import requests
import time

BASE_URL = "https://esheq1.store/wp-json/esheeq/v1"

# قائمة بروكسيات مجانية (قد لا تعمل كلها، جرب واحدة)
# مصادر مثل: https://free-proxy-list.net/
PROXY = {
    "http": "http://45.155.205.233:8888",   # غير صالح، جرب استبداله بآخر من الموقع أعلاه
    "https": "https://45.155.205.233:8888"
}

def get_all_series():
    """جلب قائمة جميع المسلسلات"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        # حاول بدون بروكسي أولاً (قد يعمل أحياناً)
        response = requests.get(f"{BASE_URL}/series", headers=headers, timeout=10)
        # إذا فشل، جرب بالبروكسي
        if response.status_code != 200:
            response = requests.get(f"{BASE_URL}/series", headers=headers, proxies=PROXY, timeout=15)
        response.raise_for_status()
        data = response.json()
        return data.get("series", [])
    except Exception as e:
        print(f"خطأ في جلب المسلسلات: {e}")
        # في حالة الفشل، نعيد بيانات وهمية لتجربة واجهة الموقع
        return [{"id": 1, "title": "مسلسل تجريبي (تعذر الاتصال)"}]

def get_series_episodes(series_id):
    """جلب حلقات مسلسل معين"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(f"{BASE_URL}/series/{series_id}/episodes", headers=headers, timeout=10)
        if response.status_code != 200:
            response = requests.get(f"{BASE_URL}/series/{series_id}/episodes", headers=headers, proxies=PROXY, timeout=15)
        response.raise_for_status()
        data = response.json()
        return data.get("episodes", [])
    except Exception as e:
        print(f"خطأ في جلب الحلقات: {e}")
        return []

def get_video_download_url(episode_id):
    """الحصول على رابط التحميل المباشر"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(f"{BASE_URL}/get-video/{episode_id}", headers=headers, timeout=10)
        if response.status_code != 200:
            response = requests.get(f"{BASE_URL}/get-video/{episode_id}", headers=headers, proxies=PROXY, timeout=15)
        response.raise_for_status()
        data = response.json()
        mp4_urls = data.get("video_urls", {}).get("mp4", [])
        return mp4_urls[0] if mp4_urls else None
    except Exception as e:
        print(f"خطأ في جلب رابط الفيديو: {e}")
        return None
