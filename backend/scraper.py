import requests
from bs4 import BeautifulSoup
import time
import re

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def get_episode_page_url(episode_id):
    """تُرجع رابط صفحة الحلقة بناءً على معرفها (يمكن تعديلها إذا كانت الروابط معروفة)"""
    # في الموقع، الروابط تكون مثل: https://esheq1.store/watch/.../
    # لكن قد لا نعرف الرابط مباشرة، لذا سنستخدم البحث عن الحلقة عبر API إن أمكن.
    # نعتمد على أن لدينا معرف الحلقة ويمكننا بناء الرابط إذا عرفنا نمطه.
    # لكن الأفضل أن نمرر الرابط الكامل من الواجهة عند الضغط على الحلقة.
    # سنعدل الدالة لتأخذ الرابط مباشرة.
    pass

def extract_servers_from_page(page_url):
    """يستخرج جميع روابط السيرفرات (data-src) من صفحة الحلقة"""
    try:
        response = requests.get(page_url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        server_items = soup.select('.serversList li')
        servers = []
        for li in server_items:
            data_src = li.get('data-src')
            if data_src:
                servers.append(data_src)
        return servers
    except Exception as e:
        print(f"Error extracting servers: {e}")
        return []

def try_server(embed_url, timeout=20):
    """محاولة جلب الفيديو من رابط السيرفر (embed)"""
    # قد يكون الرابط مباشراً للفيديو، أو صفحة تحتوي على الفيديو.
    # نحاول استخراج الفيديو من الصفحة أو التحقق من وجوده.
    try:
        # نحاول جلب الصفحة
        resp = requests.get(embed_url, headers=HEADERS, timeout=timeout)
        if resp.status_code != 200:
            return None
        # نحاول البحث عن فيديو في الصفحة (قد يكون داخل iframe آخر أو مصدر video)
        # غالباً ما يكون الرابط النهائي موجوداً في خاصية src أو داخل عنصر video
        soup = BeautifulSoup(resp.text, 'html.parser')
        # البحث عن فيديو
        video_tag = soup.find('video')
        if video_tag and video_tag.get('src'):
            return video_tag['src']
        # البحث عن iframe آخر
        iframe = soup.find('iframe')
        if iframe and iframe.get('src'):
            # قد يكون هناك تداخل، نعيد استدعاء الدالة على الرابط الجديد (تجنب الحلقات اللانهائية)
            return try_server(iframe['src'], timeout)
        # البحث عن رابط .mp4 مباشر
        mp4_links = re.findall(r'https?://[^\s"\']+\.mp4', resp.text)
        if mp4_links:
            return mp4_links[0]
        # إذا لم نجد شيئاً، نعيد None
        return None
    except Exception as e:
        print(f"Error trying server {embed_url}: {e}")
        return None

def get_video_url_from_episode(page_url, progress_callback=None):
    """
    يحاول استخراج رابط فيديو صالح من صفحة الحلقة بتجربة جميع السيرفرات.
    progress_callback: دالة تُستدعى لتحديث التقدم (نص, نسبة)
    """
    servers = extract_servers_from_page(page_url)
    if not servers:
        return None, "لم يتم العثور على أي سيرفرات في الصفحة."
    
    total = len(servers)
    for idx, embed_url in enumerate(servers):
        if progress_callback:
            progress_callback(f"جارٍ تجربة السيرفر {idx+1} من {total}...", int((idx/total)*30))
        video_url = try_server(embed_url)
        if video_url:
            if progress_callback:
                progress_callback(f"تم العثور على رابط صالح من السيرفر {idx+1}", 35)
            return video_url, None
        time.sleep(0.5)  # انتظار بسيط بين المحاولات
    
    return None, "فشلت جميع محاولات العثور على رابط فيديو صالح."

# دالة مساعدة لاستخراج معرف الحلقة من الرابط (إذا لزم الأمر)
def extract_episode_id_from_url(url):
    # مثال: https://esheq1.store/watch/..../
    # يمكن استخراج الجزء الأخير
    import re
    match = re.search(r'/watch/([^/]+)/?', url)
    if match:
        return match.group(1)
    return None
