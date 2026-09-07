import cloudscraper
from bs4 import BeautifulSoup
import time
import re

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'ar,en;q=0.9',
    'Referer': 'https://esheq1.store/',
}

def extract_servers_from_page(page_url):
    """يستخرج جميع روابط السيرفرات (data-src) من صفحة الحلقة"""
    try:
        scraper = cloudscraper.create_scraper()
        response = scraper.get(page_url, headers=HEADERS, timeout=20)
        
        if response.status_code != 200:
            print(f"فشل جلب الصفحة: {response.status_code}")
            return []

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # البحث عن قائمة السيرفرات
        server_items = soup.select('.serversList li')
        servers = []
        for li in server_items:
            data_src = li.get('data-src')
            if data_src:
                servers.append(data_src)
        
        # إذا لم نجد شيئاً، نحاول البحث عن iframe داخل .watch
        if not servers:
            watch_div = soup.select_one('.watch')
            if watch_div:
                iframe = watch_div.find('iframe')
                if iframe and iframe.get('src'):
                    servers.append(iframe['src'])
        
        # إزالة التكرارات
        return list(dict.fromkeys(servers))
    
    except Exception as e:
        print(f"Error extracting servers: {e}")
        return []

def try_server(embed_url, timeout=30):
    """محاولة جلب الفيديو من رابط السيرفر (embed)"""
    try:
        scraper = cloudscraper.create_scraper()
        response = scraper.get(embed_url, headers=HEADERS, timeout=timeout)
        if response.status_code != 200:
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # البحث عن فيديو مباشر
        video_tag = soup.find('video')
        if video_tag and video_tag.get('src'):
            return video_tag['src']
        
        # البحث عن iframe آخر
        iframe = soup.find('iframe')
        if iframe and iframe.get('src'):
            # نستدعي نفس الدالة بشكل متكرر (تجنب الحلقات اللانهائية)
            return try_server(iframe['src'], timeout)
        
        # البحث عن روابط .mp4 في النص
        mp4_links = re.findall(r'https?://[^\s"\']+\.mp4', response.text)
        if mp4_links:
            return mp4_links[0]
        
        # البحث عن روابط .m3u8
        m3u8_links = re.findall(r'https?://[^\s"\']+\.m3u8', response.text)
        if m3u8_links:
            return m3u8_links[0]
        
        return None
    except Exception as e:
        print(f"Error trying server {embed_url}: {e}")
        return None

def get_video_url_from_episode(episode_url, progress_callback=None):
    """
    يحاول استخراج رابط فيديو صالح من صفحة الحلقة بتجربة جميع السيرفرات.
    """
    # التأكد من أن الرابط كامل
    if not episode_url.startswith('http'):
        if episode_url.startswith('/'):
            episode_url = 'https://esheq1.store' + episode_url
        else:
            episode_url = 'https://esheq1.store/' + episode_url

    # ✅ إضافة /see/ إلى الرابط إذا لم تكن موجودة
    if not episode_url.endswith('/see/'):
        if episode_url.endswith('/'):
            episode_url = episode_url[:-1]
        episode_url = episode_url + '/see/'

    if progress_callback:
        progress_callback(f"جارٍ جلب السيرفرات من الصفحة...", 5)

    servers = extract_servers_from_page(episode_url)
    if not servers:
        return None, "لم يتم العثور على أي سيرفرات في الصفحة. قد تكون الصفحة محمية أو تحتاج إلى تحديث."

    total = len(servers)
    for idx, embed_url in enumerate(servers):
        if progress_callback:
            progress_callback(f"جارٍ تجربة السيرفر {idx+1} من {total}...", int((idx/total)*30) + 10)

        video_url = try_server(embed_url)
        if video_url:
            if progress_callback:
                progress_callback(f"تم العثور على رابط صالح من السيرفر {idx+1}", 40)
            return video_url, None

        time.sleep(0.5)

    return None, "فشلت جميع محاولات العثور على رابط فيديو صالح."

# دالة مساعدة لاستخراج معرف الحلقة من الرابط (إذا لزم الأمر)
def extract_episode_id_from_url(url):
    import re
    match = re.search(r'/watch/([^/]+)/?', url)
    if match:
        return match.group(1)
    return None

# اختبار سريع
if __name__ == "__main__":
    test_url = "https://esheq1.store/watch/%d9%85%d8%b3%d9%84%d8%b3%d9%84-%d9%81%d9%8a-%d8%a7%d9%84%d8%b3%d8%a7%d8%a8%d8%b9%d8%a9-%d8%b9%d8%b4%d8%b1-%d8%a7%d9%84%d8%ad%d9%84%d9%82%d8%a9-15-%d9%85%d8%aa%d8%b1%d8%ac%d9%85%d8%a9/"
    video_url, error = get_video_url_from_episode(test_url)
    if video_url:
        print(f"✅ تم العثور على رابط الفيديو: {video_url}")
    else:
        print(f"❌ فشل: {error}")
