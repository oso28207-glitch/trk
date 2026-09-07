import cloudscraper
import time

BASE_URL = "https://esheq1.store/wp-json/esheeq/v1"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json',
}

def safe_request(url, params=None, max_retries=3):
    scraper = cloudscraper.create_scraper()
    for attempt in range(max_retries):
        try:
            response = scraper.get(url, params=params, headers=HEADERS, timeout=30)
            if response.status_code == 200:
                return response.json()
            print(f"حالة غير متوقعة: {response.status_code}")
        except Exception as e:
            print(f"خطأ (محاولة {attempt+1}): {e}")
            time.sleep(2)
    return None

def get_all_series():
    data = safe_request(f"{BASE_URL}/series")
    if data and "series" in data:
        return data["series"]
    return [{"id": 1, "title": "مسلسل تجريبي (تعذر الاتصال)", "slug": "test"}]

def get_series_episodes(series_id):
    data = safe_request(f"{BASE_URL}/series/{series_id}/episodes")
    if data and "episodes" in data:
        return data["episodes"]
    return []

def get_video_download_url(episode_id):
    data = safe_request(f"{BASE_URL}/get-video/{episode_id}")
    if data and "video_urls" in data:
        mp4_urls = data["video_urls"].get("mp4", [])
        return mp4_urls[0] if mp4_urls else None
    return None
