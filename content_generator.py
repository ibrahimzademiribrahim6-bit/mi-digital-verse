import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
SERPER_API_KEY = os.getenv('SERPER_API_KEY')

def serper_search(query, search_type="search", num=5):
    """Serper API ilə axtarış edir. search_type: 'search' və ya 'images'"""
    if not SERPER_API_KEY:
        return []
    url = f"https://google.serper.dev/{search_type}"
    headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
    payload = {"q": query, "num": num}
    if search_type == "images":
        payload["gl"] = "us"
        payload["hl"] = "en"
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if search_type == "search":
            return data.get("organic", [])
        elif search_type == "images":
            return data.get("images", [])
        return []
    except Exception as e:
        print(f"Serper xətası ({search_type}): {e}")
        return []

def get_image_url(title):
    """Başlığa uyğun ilk şəkil linkini qaytar (əgər tapılmasa boş qaytar)."""
    images = serper_search(title + " anime manhwa", search_type="images", num=1)
    if images:
        return images[0].get("link", "")
    return ""

def generate_news_content():
    """Serper ilə real anime/manhwa xəbərlərini tapıb, DeepSeek ilə 3 xəbər kimi formatlaşdırır."""
    query = "anime manhwa manga news 2025"
    raw = serper_search(query, search_type="search", num=5)

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    prompt = f"""
    Sənə aşağıda real axtarış nəticələri verilib. Bunlara əsasən 3 xəbər yarat.
    Hər xəbər üçün:
    - Başlıq (maraqlı, dəqiq)
    - Məzmun (3-4 cümlə)
    - Kateqoriya (Anime, Manga, Webtoon/Manhua, Oyun, Ümumi)
    - Şəkil URL (əgər axtarış nəticəsində varsa istifadə et, yoxsa boş qoy)
    Məlumatlar dəqiq olsun, heç bir uydurma əlavə etmə.
    Axtarış nəticələri:
    {json.dumps(raw[:5], ensure_ascii=False)}
    Cavab yalnız JSON formatında olsun:
    {{"news": [{{"title": "...", "content": "...", "category": "...", "image_url": "..."}}]}}
    """
    data = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 1500
    }
    try:
        resp = requests.post("https://api.deepseek.com/chat/completions", headers=headers, json=data, timeout=60)
        resp.raise_for_status()
        text = resp.json()['choices'][0]['message']['content']
        start = text.find('{')
        end = text.rfind('}') + 1
        if start != -1 and end > start:
            return json.loads(text[start:end]).get('news', [])
        return []
    except Exception as e:
        print(f"DeepSeek xəbər xətası: {e}")
        return []

def generate_manga_content():
    """Serper ilə populyar manhwa/manhua/anime tapıb, DeepSeek ilə 3 əsəri formatlaşdırır."""
    query = "top manhwa manhua anime 2025"
    raw = serper_search(query, search_type="search", num=5)

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    prompt = f"""
    Sənə aşağıda real axtarış nəticələri verilib. Bunlara əsasən 3 manhwa, manhua, anime və ya manga əsəri seç.
    Hər biri üçün:
    - Başlıq
    - Açıqlama (2-3 cümlə)
    - Növü (anime, manga, manhwa, manhua, webtoon)
    - Reytinq (0-10 arası, onluq kəsr ola bilər)
    - Status (Davam edir, Bitib)
    - Bölüm sayı (tam ədəd)
    - Şəkil URL (əgər axtarış nəticəsində varsa istifadə et, yoxsa boş qoy)
    Axtarış nəticələri:
    {json.dumps(raw[:5], ensure_ascii=False)}
    Cavab yalnız JSON formatında olsun:
    {{"manga": [{{"title": "...", "description": "...", "type": "manhwa", "cover_url": "...", "rating": 8.5, "status": "Davam edir", "chapters": 120}}]}}
    """
    data = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 1200
    }
    try:
        resp = requests.post("https://api.deepseek.com/chat/completions", headers=headers, json=data, timeout=60)
        resp.raise_for_status()
        text = resp.json()['choices'][0]['message']['content']
        start = text.find('{')
        end = text.rfind('}') + 1
        if start != -1 and end > start:
            return json.loads(text[start:end]).get('manga', [])
        return []
    except Exception as e:
        print(f"DeepSeek manqa xətası: {e}")
        return []