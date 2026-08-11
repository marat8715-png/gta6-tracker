import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
import os, json, hashlib, re

BOT_TOKEN   = os.environ['TELEGRAM_BOT_TOKEN']
CHANNEL     = os.environ.get('TELEGRAM_CHANNEL', '@GTAVITracker')
SITE_URL    = 'https://marat8715-png.github.io/gta6-tracker/'
HASHES_FILE = 'posted_hashes.json'

# Несколько RSS-источников для надёжности
RSS_FEEDS = [
    'https://news.google.com/rss/search?q=GTA+VI+Grand+Theft+Auto+6&hl=ru&gl=RU&ceid=RU:ru',
    'https://vgtimes.ru/rss.xml',
    'https://gamemag.ru/feed',
]

HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; GTABot/1.0)'}

def fetch_feed(url):
    """Fetch and parse RSS feed, return list of items"""
    try:
        r = requests.get(url, timeout=12, headers=HEADERS)
        r.raise_for_status()
        root = ET.fromstring(r.content)
        items = []
        for item in root.findall('.//item'):
            title = item.findtext('title', '').strip()
            link  = item.findtext('link', '').strip()
            # Google News uses <guid> for real URL, link is a redirect
            guid  = item.findtext('guid', '').strip()
            if 'google.com' in link and guid.startswith('http'):
                link = guid
            pub   = item.findtext('pubDate', '')
            desc  = item.findtext('description', '').strip()
            # Filter: only GTA VI related for non-Google feeds
            combined = (title + desc).lower()
            if 'google.com' not in url:
                if not any(kw in combined for kw in ['gta', 'grand theft', 'rockstar']):
                    continue
            if title:
                items.append({'title': title, 'link': link,
                              'pubDate': pub, 'description': desc})
        return items
    except Exception as e:
        print(f'  Feed error ({url[:50]}): {e}')
        return []

def get_all_news():
    seen, results = set(), []
    for feed_url in RSS_FEEDS:
        items = fetch_feed(feed_url)
        print(f'  Feed {feed_url[:55]}: {len(items)} items')
        for item in items:
            key = item['link'] or item['title']
            if key not in seen:
                seen.add(key)
                results.append(item)
    return results

def is_recent(pub_str, hours=48):
    try:
        pub_dt = parsedate_to_datetime(pub_str)
        return (datetime.now(timezone.utc) - pub_dt) <= timedelta(hours=hours)
    except:
        return True  # если дата не парсится — считаем свежей

def load_hashes():
    try:
        with open(HASHES_FILE) as f:
            data = json.load(f)
            return set(data), len(data) > 0
    except:
        return set(), False  # (hashes, is_not_first_run)

def save_hashes(hashes):
    with open(HASHES_FILE, 'w') as f:
        json.dump(list(hashes)[-300:], f)

def clean_html(text):
    return re.sub(r'<[^>]+>', '', text or '').strip()

def make_message(item):
    title = clean_html(item['title'])
    link  = item['link']
    desc  = clean_html(item['description'])
    # Обрезаем описание
    if len(desc) > 300:
        desc = desc[:300].rsplit(' ', 1)[0] + '…'
    desc_block = f'\n\n{desc}' if desc else ''
    return (
        f'🎮 <b>GTA VI — Новости</b>{desc_block}\n\n'
        f'📰 <b>{title}</b>\n\n'
        f'🔗 <a href="{link}">Читать полностью</a>\n'
        f'🌐 <a href="{SITE_URL}">GTA VI TRACKER</a>'
    )

def send(text):
    r = requests.post(
        f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage',
        json={'chat_id': CHANNEL, 'text': text,
              'parse_mode': 'HTML', 'disable_web_page_preview': False},
        timeout=15
    )
    return r.json()

def main():
    print(f'Channel: {CHANNEL}')
    print('Fetching news...')

    items = get_all_news()
    print(f'Total unique items: {len(items)}')

    posted, had_posts_before = load_hashes()
    updated = set(posted)

    # При первом запуске постим последние 5 новостей без фильтра по времени
    # При обычном запуске — только за последние 48 часов
    time_limit = 48 if had_posts_before else 999
    max_posts  = 5 if not had_posts_before else 10

    count = 0
    for item in items:
        if count >= max_posts:
            break
        h = hashlib.md5((item['link'] or item['title']).encode()).hexdigest()
        if h in posted:
            print(f'  Skip (dup): {item["title"][:55]}')
            continue
        if not is_recent(item['pubDate'], hours=time_limit):
            print(f'  Skip (old): {item["title"][:55]}')
            continue

        msg = make_message(item)
        result = send(msg)

        if result.get('ok'):
            updated.add(h)
            count += 1
            print(f'  ✅ Posted: {item["title"][:65]}')
        else:
            err = result.get('description', 'unknown error')
            print(f'  ❌ Failed: {err} | title: {item["title"][:50]}')

    save_hashes(updated)
    print(f'\nDone. Posted {count} item(s) to {CHANNEL}')

if __name__ == '__main__':
    main()
