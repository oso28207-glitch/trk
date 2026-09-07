import cloudscraper
import requests
from bs4 import BeautifulSoup
import re
import time
from urllib.parse import urljoin, urlparse

# رؤوس تحاكي المتصفح
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'ar,en;q=0.9',
    'Referer': 'https://esheq1.store/',
    'Origin': 'https://esheq1.store',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
}

def extract_servers_from_page(page_url):
    """
    يستخرج روابط السيرفرات (data-src) من صفحة /see/
    """
    try:
        scraper = cloudscraper.create_scraper()
        response = scraper.get(page_url, headers=HEADERS, timeout=20)
        
        if response.status_code != 200:
            print(f"⚠️ فشل جلب الصفحة: {response.status_code}")
            return []

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # البحث عن قائمة السيرفرات
        server_items = soup.select('.serversList li')
        servers = []
        for li in server_items:
            data_src = li.get('data-src')
            if data_src:
                # تنظيف الرابط من &amp; إلى &
                data_src = data_src.replace('&amp;', '&')
                servers.append(data_src)
        
        # إذا لم نجد شيئاً، نحاول البحث عن iframe داخل .watch
        if not servers:
            watch_div = soup.select_one('.watch')
            if watch_div:
                iframe = watch_div.find('iframe')
                if iframe and iframe.get('src'):
                    servers.append(iframe['src'])
        
        # إزالة التكرارات
        servers = list(dict.fromkeys(servers))
        print(f"✅ تم العثور على {len(servers)} سيرفرات")
        return servers
    
    except Exception as e:
        print(f"❌ خطأ في استخراج السيرفرات: {e}")
        return []

def try_server(embed_url, timeout=25):
    """
    محاولة استخراج رابط الفيديو النهائي من رابط السيرفر
    """
    try:
        # إعداد جلسة مع رؤوس خاصة للسيرفر
        session = cloudscraper.create_scraper()
        
        # نضيف رؤوس إضافية تحاكي الطلب من داخل الموقع
        headers = HEADERS.copy()
        headers['Referer'] = 'https://esheq1.store/'
        
        response = session.get(embed_url, headers=headers, timeout=timeout)
        
        if response.status_code != 200:
            print(f"⚠️ السيرفر {embed_url} رد بـ {response.status_code}")
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. البحث عن فيديو مباشر
        video_tag = soup.find('video')
        if video_tag and video_tag.get('src'):
            return video_tag['src']
        
        # 2. البحث عن iframe
        iframe = soup.find('iframe')
        if iframe and iframe.get('src'):
            # نستدعي نفس الدالة بشكل متكرر (لتجنب الحلقات اللانهائية نحدد عدد المحاولات)
            return try_server(iframe['src'], timeout)
        
        # 3. البحث عن روابط .m3u8 أو .mp4 في النص
        video_links = re.findall(r'https?://[^\s"\']+\.(?:m3u8|mp4)', response.text)
        if video_links:
            return video_links[0]
        
        # 4. البحث عن روابط داخل script tags (قد تكون مشفرة)
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string:
                found = re.findall(r'https?://[^\s"\']+\.(?:m3u8|mp4)', script.string)
                if found:
                    return found[0]
        
        return None
        
    except Exception as e:
        print(f"❌ خطأ في محاولة السيرفر {embed_url}: {e}")
        return None

def get_video_url_from_episode(episode_url, progress_callback=None):
    """
    الدالة الرئيسية: تستقبل رابط الحلقة، وتضيف /see/، ثم تجرب جميع السيرفرات.
    """
    # التأكد من أن الرابط كامل
    if not episode_url.startswith('http'):
        if episode_url.startswith('/'):
            episode_url = 'https://esheq1.store' + episode_url
        else:
            episode_url = 'https://esheq1.store/' + episode_url
    
    # ✅ إضافة /see/ إلى الرابط
    if not episode_url.endswith('/see/'):
        if episode_url.endswith('/'):
            episode_url = episode_url[:-1]
        episode_url = episode_url + '/see/'
    
    print(f"🔍 جلب السيرفرات من: {episode_url}")
    
    if progress_callback:
        progress_callback("جارٍ استخراج قائمة السيرفرات...", 5)
    
    servers = extract_servers_from_page(episode_url)
    if not servers:
        return None, "لم يتم العثور على أي سيرفرات في الصفحة. قد تكون الصفحة محمية أو تحتاج إلى تحديث."
    
    total = len(servers)
    for idx, embed_url in enumerate(servers):
        percent = int((idx / total) * 30) + 10
        if progress_callback:
            progress_callback(f"محاولة السيرفر {idx+1} من {total}...", percent)
        
        video_url = try_server(embed_url)
        if video_url:
            print(f"✅ تم العثور على رابط صالح: {video_url}")
            if progress_callback:
                progress_callback(f"تم العثور على رابط من السيرفر {idx+1}", 35)
            return video_url, None
        
        time.sleep(0.5)  # انتظار بسيط بين المحاولات
    
    return None, "فشلت جميع محاولات العثور على رابط فيديو صالح."

# دالة مساعدة لاختبار الملف مباشرة
if __name__ == "__main__":
    test_url = "https://esheq1.store/watch/%d9%85%d8%b3%d9%84%d8%b3%d9%84-%d9%81%d9%8a-%d8%a7%d9%84%d8%b3%d8%a7%d8%a8%d8%b9%d8%a9-%d8%b9%d8%b4%d8%b1-%d8%a7%d9%84%d8%ad%d9%84%d9%82%d8%a9-15-%d9%85%d8%aa%d8%b1%d8%ac%d9%85%d8%a9/"
    print("🧪 اختبار استخراج السيرفرات...")
    video_url, error = get_video_url_from_episode(test_url)
    if video_url:
        print(f"✅ رابط الفيديو: {video_url}")
    else:
        print(f"❌ فشل: {error}")
