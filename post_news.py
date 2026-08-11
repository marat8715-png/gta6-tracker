import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
import os, json, hashlib, re, sys

BOT_TOKEN   = os.environ['TELEGRAM_BOT_TOKEN']
CHANNEL     = os.environ.get('TELEGRAM_CHANNEL', '@GTAVITracker')
SITE_URL    = 'https://marat8715-png.github.io/gta6-tracker/'
HASHES_FILE = 'posted_hashes.json'

RSS_FEEDS = [
    'https://news.google.com/rss/search?q=GTA+VI+Grand+Theft+Auto&hl=ru&gl=RU&ceid=RU:ru',
    'https://vgtimes.ru/rss.xml',
    'https://gamemag.ru/feed',
]
HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; GTABot/1.0)'}

def fetch_feed(url):
    try:
        r = requests.get(url, timeout=12, headers=HEADERS)
        r.raise_for_status()
        root = ET.fromstring(r.content)
        items = []
        for item in root.findall('.//item'):
            title = item.findtext('title', '').strip()
            link  = item.findtext('link', '').strip()
            guid  = item.findtext('guid', '').strip()
            if 'google.com' in link and guid.startswith('http'):
                link = guid
            pub  = item.findtext('pubDate', '')
            desc = item.findtext('description', '').strip()
            combined = (title + desc).lower()
            if 'google.com' not in url:
                if not any(kw in combined for kw in ['gta', 'grand theft', 'rockstar']):
                    continue
            if title:
                items.append({'title': title, 'link': link, 'pubDate': pub, 'description': desc})
        print(f'  [{url[:55]}] → {len(items)} items')
        return items
    except Exception as e:
        print(f'  [FEED ERROR] {url[:55]}: {e}')
        return []

def get_all_news():
    seen, results = set(), []
    for url in RSS_FEEDS:
        for item in fetch_feed(url):
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
        return True

def load_hashes():
    try:
        with open(HASHES_FILE) as f:
            data = json.load(f)
            return set(data), len(data) > 0
    except:
        return set(), False

def save_hashes(hashes):
    with open(HASHES_FILE, 'w') as f:
        json.dump(list(hashes)[-300:], f)

def clean_html(text):
    return re.sub(r'<[^>]+>', '', text or '').strip()

def make_message(item):
    title = clean_html(item['title'])
    link  = item['link']
    desc  = clean_html(item['description'])
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
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
    payload = {'chat_id': CHANNEL, 'text': text,
                'parse_mode': 'HTML', 'disable_web_page_preview': False}
    r = requests.post(url, json=payload, timeout=15)
    resp = r.json()
    print(f'  [TG RESPONSE] ok={resp.get("ok")} | {resp}')
    return resp

def main():
    print(f'=== GTA VI Telegram Bot ===')
    print(f'Channel: {CHANNEL}')
    print(f'Bot token: {BOT_TOKEN[:10]}...')
    print(f'\nFetching RSS feeds...')

    items = get_all_news()
    print(f'Total unique items: {len(items)}')

    posted, had_before = load_hashes()
    print(f'Already posted hashes: {len(posted)} | First run: {not had_before}')
    updated = set(posted)

    time_limit = 48 if had_before else 9999
    max_posts  = 10 if had_before else 5

    count, errors = 0, 0
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

        print(f'  Posting: {item["title"][:65]}')
        result = send(make_message(item))

        if result.get('ok'):
            updated.add(h)
            count += 1
            print(f'  ✅ Success!')
        else:
            errors += 1
            print(f'  ❌ Error: {result.get("description","?")} (code {result.get("error_code","?")})')

    save_hashes(updated)
    print(f'\n=== Done: {count} posted, {errors} errors ===')

    if errors > 0 and count == 0:
        print('FATAL: All posts failed. Check bot permissions in channel.')
        sys.exit(1)

if __name__ == '__main__':
    main()
