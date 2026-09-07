import cloudscraper
import time
import re
import json
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import shutil
import os

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9',
    'Accept-Language': 'ar,en;q=0.9',
    'Referer': 'https://esheq1.store/',
    'Origin': 'https://esheq1.store',
}

def setup_selenium():
    """إعداد متصفح Chrome في وضع headless"""
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument('--disable-notifications')
    chrome_options.add_argument('--ignore-certificate-errors')
    
    chromedriver_path = '/usr/bin/chromedriver'
    if not os.path.exists(chromedriver_path):
        chromedriver_path = shutil.which('chromedriver')
        if not chromedriver_path:
            print("❌ لم يتم العثور على chromedriver")
            return None
    
    try:
        service = Service(executable_path=chromedriver_path)
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        return driver
    except Exception as e:
        print(f"❌ فشل إعداد Selenium: {e}")
        return None

def extract_servers_with_selenium(page_url):
    """استخدام Selenium لاستخراج السيرفرات من صفحة /see/"""
    driver = setup_selenium()
    if not driver:
        return []
    
    try:
        print(f"🖥️ فتح الصفحة بـ Selenium: {page_url}")
        driver.get(page_url)
        time.sleep(5)
        
        # البحث عن قائمة السيرفرات
        servers = []
        try:
            server_list = driver.find_element(By.CSS_SELECTOR, "ul.serversList")
            items = server_list.find_elements(By.TAG_NAME, "li")
            for item in items:
                data_src = item.get_attribute("data-src")
                if data_src:
                    data_src = data_src.replace('&amp;', '&')
                    servers.append(data_src)
        except:
            pass
        
        # إذا لم نجد، نبحث عن iframe في .watch
        if not servers:
            try:
                iframe = driver.find_element(By.CSS_SELECTOR, ".watch iframe")
                src = iframe.get_attribute("src")
                if src:
                    servers.append(src)
            except:
                pass
        
        driver.quit()
        return list(dict.fromkeys(servers))
    except Exception as e:
        print(f"❌ خطأ في Selenium: {e}")
        driver.quit()
        return []

def extract_video_from_uqload(driver, url):
    """استخراج رابط الفيديو من Uqload"""
    try:
        if 'uqload.to' in url:
            url = url.replace('uqload.to', 'uqload.is')
        print(f"🔄 فتح Uqload: {url}")
        driver.get(url)
        time.sleep(5)
        
        page_source = driver.page_source
        
        # البحث عن sources
        match = re.search(r'sources:\s*\[\s*"([^"]+\.mp4[^"]*)"\s*\]', page_source)
        if match:
            return match.group(1)
        
        # البحث عن أي رابط mp4
        match = re.search(r'(https?://[^"\']+\.mp4[^"\']*)', page_source)
        if match:
            return match.group(1)
        
        return None
    except Exception as e:
        print(f"❌ خطأ في Uqload: {e}")
        return None

def try_server_with_selenium(embed_url, progress_callback=None):
    """محاولة استخراج الفيديو من رابط السيرفر باستخدام Selenium"""
    driver = setup_selenium()
    if not driver:
        return None
    
    try:
        # إذا كان الرابط من Uqload
        if 'uqload' in embed_url:
            video_url = extract_video_from_uqload(driver, embed_url)
            driver.quit()
            return video_url
        
        # فتح الرابط مباشرة
        print(f"🔄 فتح السيرفر: {embed_url}")
        driver.get(embed_url)
        time.sleep(5)
        
        # البحث عن iframe داخل الصفحة
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        for iframe in iframes:
            src = iframe.get_attribute("src")
            if src:
                print(f"📦 تم العثور على iframe: {src}")
                # فتح iframe
                driver.get(src)
                time.sleep(5)
                break
        
        # البحث عن عنصر الفيديو
        try:
            video = driver.find_element(By.TAG_NAME, "video")
            src = video.get_attribute("src")
            if src and src.startswith("http"):
                driver.quit()
                return src
        except:
            pass
        
        # البحث عن روابط mp4 أو m3u8 في الصفحة
        page_source = driver.page_source
        patterns = [
            r'(https?://[^"\']+\.mp4[^"\']*)',
            r'(https?://[^"\']+\.m3u8[^"\']*)',
            r'file:\s*["\']([^"\']+\.mp4[^"\']*)["\']',
            r'src:\s*["\']([^"\']+\.mp4[^"\']*)["\']',
        ]
        for pattern in patterns:
            match = re.search(pattern, page_source, re.IGNORECASE)
            if match:
                driver.quit()
                return match.group(1)
        
        driver.quit()
        return None
    except Exception as e:
        print(f"❌ خطأ في السيرفر: {e}")
        driver.quit()
        return None

def get_video_url_from_episode(episode_url, progress_callback=None):
    """الدالة الرئيسية لاستخراج رابط الفيديو"""
    # التأكد من الرابط
    if not episode_url.startswith('http'):
        if episode_url.startswith('/'):
            episode_url = 'https://esheq1.store' + episode_url
        else:
            episode_url = 'https://esheq1.store/' + episode_url
    
    # إضافة /see/
    if not episode_url.endswith('/see/'):
        if episode_url.endswith('/'):
            episode_url = episode_url[:-1]
        episode_url = episode_url + '/see/'
    
    if progress_callback:
        progress_callback("جارٍ استخراج السيرفرات...", 10)
    
    # استخراج السيرفرات
    servers = extract_servers_with_selenium(episode_url)
    if not servers:
        return None, "لم يتم العثور على سيرفرات"
    
    total = len(servers)
    for idx, embed_url in enumerate(servers):
        if progress_callback:
            progress_callback(f"محاولة السيرفر {idx+1}/{total}...", 10 + int((idx/total)*30))
        
        video_url = try_server_with_selenium(embed_url)
        if video_url:
            if progress_callback:
                progress_callback(f"تم العثور على رابط", 40)
            return video_url, None
        
        time.sleep(1)
    
    return None, "فشلت جميع السيرفرات"
