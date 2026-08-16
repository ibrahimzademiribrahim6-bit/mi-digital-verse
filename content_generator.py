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
    """
    Başlığa uyğun ilk uyğun şəkil linkini qaytarır.
    Əgər tapılmasa, bir neçə açar söz kombinasiyası sınayır.
    """
    keywords_list = [
        title,
        title + " anime",
        title + " manhwa",
        title + " manga",
        title + " poster",
        title + " cover"
    ]
    for query in keywords_list:
        images = serper_search(query, search_type="images", num=1)
        if images:
            link = images[0].get("link", "")
            if link:
                return link
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

def fetch_and_generate_news():
    """
    Etibarlı anime/manqa xəbər saytlarından güncəl xəbərləri tapıb,
    DeepSeek-ə daha canlı, jurnalist üslubunda məqalələr yazdırır.
    """
    from datetime import datetime
    current_year = datetime.now().strftime("%Y")
    current_date = datetime.now().strftime("%Y-%m-%d")

    # Etibarlı xəbər mənbələri
    sites = [
        "animenewsnetwork.com",
        "crunchyroll.com/news",
        "myanimelist.net/news",
        "animecorner.me",
        "mangamogura.com",
        "animegeek.com",
        "otakukart.com",
        "animehunch.com",
    ]
    site_query = " OR ".join([f"site:{s}" for s in sites])
    query = f"({site_query}) anime OR manga OR manhwa news {current_year}"

    raw = serper_search(query, search_type="search", num=10)

    # Yalnız etibarlı saytlardan nəticələri götür
    allowed_domains = [
        "animenewsnetwork.com",
        "crunchyroll.com",
        "myanimelist.net",
        "animecorner.me",
        "mangamogura.com",
        "animegeek.com",
        "otakukart.com",
        "animehunch.com",
    ]
    filtered = []
    seen = set()
    for item in raw:
        link = item.get('link', '')
        if any(domain in link for domain in allowed_domains):
            if link not in seen:
                seen.add(link)
                filtered.append(item)

    raw = filtered[:5]

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }

    prompt = f"""
    Sən təcrübəli anime/manqa jurnalistisən. Aşağıda real axtarış nəticələri verilib.
    Bugünkü tarix: {current_date}.
    Hər nəticə üçün **canlı, enerjili, oxucunu yormayan** xəbər məqaləsi yaz.
    Tələblər:
    - Başlıq maraqlı, dəqiq, qısa (10 sözdən çox olmasın).
    - Məzmun 8-12 cümlə olsun. İlk cümlə xəbərin əsas məğzini versin.
    - "Həftəlik xülasə", "Reddit istifadəçiləri", "YouTube videosu" kimi zəif mənbə ifadələrini işlətmə. Əgər mənbə zəifdirsə, yalnız faktları çıxar.
    - Tarix, studiya, platforma, mövsüm kimi dəqiq məlumatları daxil et.
    - Neytral, peşəkar, amma insan kimi yaz. Süni və quru olmasın.
    - Kateqoriyanı müəyyən et: Anime, Manga, Webtoon/Manhua, Oyun, Ümumi.
    - Şəkil axtarmaq üçün 3-4 açar söz təklif et.
    - Əgər axtarış nəticəsində URL varsa, onu da daxil et.
    Axtarış nəticələri:
    {json.dumps(raw, ensure_ascii=False)}
    Cavab yalnız JSON formatında olsun:
    {{"news": [{{"title": "...", "content": "...", "category": "...", "source_url": "...", "image_search_keywords": "..."}}]}}
    """

    data = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 3500
    }

    try:
        resp = requests.post("https://api.deepseek.com/chat/completions", headers=headers, json=data, timeout=120)
        resp.raise_for_status()
        text = resp.json()['choices'][0]['message']['content']
        start = text.find('{')
        end = text.rfind('}') + 1
        if start != -1 and end > start:
            return json.loads(text[start:end]).get('news', [])
        return []
    except Exception as e:
        print(f"fetch_and_generate_news xətası: {e}")
        return []

def generate_listicle(topic):
    """
    Mövzuya uyğun Azərbaycanca siyahı məqaləsi yaradır.
    Axtarışlar ingilis + uyğun orijinal dildə aparılır.
    """
    from datetime import datetime
    current_date = datetime.now().strftime("%Y-%m-%d")

    # Mövzuya uyğun dili müəyyənləşdir
    topic_lower = topic.lower()
    if 'manhua' in topic_lower or 'çin' in topic_lower or 'china' in topic_lower:
        extra_lang = 'zh'
        extra_query = '最佳十部国产漫画 2026'
    elif 'manhwa' in topic_lower or 'kore' in topic_lower:
        extra_lang = 'ko'
        extra_query = '최고의 만화 2026'
    elif 'anime' in topic_lower or 'manga' in topic_lower:
        extra_lang = 'ja'
        extra_query = '2026年 アニメ ランキング'
    else:
        extra_lang = 'en'
        extra_query = topic

    queries = [
        f"{topic} best list rankings",
        f"{topic} top 10 2026",
        extra_query
    ]

    all_raw = []
    for q in queries:
        raw_part = serper_search(q, search_type="search", num=4)
        all_raw.extend(raw_part)

    # Unikallaşdır
    unique = {}
    for item in all_raw:
        link = item.get('link', '')
        if link and link not in unique:
            unique[link] = item
    raw = list(unique.values())[:8]

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }

    prompt = f"""
    Sən peşəkar anime/manqa/webtoon redaktorusan. Məqaləni **Azərbaycan dilində** yaz.
    Mövzu: "{topic}"
    Bugünkü tarix: {current_date}

    Tələblər:
    - Başlıq Azərbaycanca olsun, amma orijinal adları ingilis/orijinal dildə saxla.
    - Məqalə 8-10 maddədən ibarət olsun.
    - Hər maddə üçün:
      a) Sıra nömrəsi
      b) Orijinal adı (ingilis + mötərizədə yapon/koreya/çin adı)
      c) Qısa hekayə (2-3 cümlə, konkret, süni olmayan)
      d) Niyə populyardır (1-2 cümlə)
    - Giriş hissəsində mövzunun niyə önəmli olduğunu 2-3 cümlə ilə izah et.
    - Nəticədə oxucuya ümumi tövsiyə ver, 2-3 cümlə.
    - Heç bir saytdan köçürmə, məlumatları çoxsaylı mənbədən toplayıb öz sözlərinlə yaz.
    - Süni, boş ifadələr işlətmə. Hər cümlə məlumat versin.
    - Hər maddə üçün şəkil axtarmaq üçün 3-4 açar söz təklif et.
    - Məqalə mətni düz mətn formatında olsun, hər maddə ayrı sətirdə başlasın.

    Axtarış nəticələri (yalnız mənbə kimi):
    {json.dumps(raw, ensure_ascii=False)}

    Cavab JSON formatında olsun:
    {{"title": "...", "content": "...", "category": "Anime", "image_search_keywords": "..."}}
    """

    data = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 8000
    }

    try:
        resp = requests.post("https://api.deepseek.com/chat/completions", headers=headers, json=data, timeout=120)
        resp.raise_for_status()
        text = resp.json()['choices'][0]['message']['content']
        start = text.find('{')
        end = text.rfind('}') + 1
        if start != -1 and end > start:
            return json.loads(text[start:end])
        return None
    except Exception as e:
        print(f"generate_listicle xətası: {e}")
        return None