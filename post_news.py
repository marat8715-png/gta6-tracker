import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
import os, json, hashlib, re, sys

BOT_TOKEN   = os.environ['TELEGRAM_BOT_TOKEN'].strip()
CHANNEL_RAW = os.environ.get('TELEGRAM_CHANNEL', 'GTAVITracker').strip()
SITE_URL    = 'https://marat8715-png.github.io/gta6-tracker/'
HASHES_FILE = 'posted_hashes.json'

RSS_FEEDS = [
    'https://news.google.com/rss/search?q=GTA+VI+Grand+Theft+Auto&hl=ru&gl=RU&ceid=RU:ru',
    'https://vgtimes.ru/rss.xml',
]
HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; GTABot/1.0)'}

def tg(method, **kwargs):
    r = requests.post(
        f'https://api.telegram.org/bot{BOT_TOKEN}/{method}',
        json=kwargs, timeout=15
    )
    return r.json()

def find_channel():
    """Try different channel ID formats and return working one"""
    candidates = []
    raw = CHANNEL_RAW.lstrip('@')
    candidates = [f'@{raw}', raw, f'@{raw.lower()}', raw.lower()]

    for candidate in candidates:
        print(f'  Testing channel: {repr(candidate)}')
        result = tg('getChat', chat_id=candidate)
        print(f'    → ok={result.get("ok")} | {result.get("description","") or result.get("result",{}).get("type","")}')
        if result.get('ok'):
            chat_id = result['result']['id']
            title   = result['result'].get('title','?')
            print(f'    ✅ Found! chat_id={chat_id}, title={title}')
            return str(chat_id)

    print('  ❌ Channel not found via username. Trying getUpdates...')
    upd = tg('getUpdates', limit=10, allowed_updates=['channel_post'])
    print(f'  getUpdates: {upd}')
    return None

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
        print(f'  Feed {url[:60]}: {len(items)} items')
        return items
    except Exception as e:
        print(f'  Feed error {url[:50]}: {e}')
        return []

def get_news():
    seen, results = set(), []
    for url in RSS_FEEDS:
        for item in fetch_feed(url):
            key = item['link'] or item['title']
            if key not in seen:
                seen.add(key)
                results.append(item)
    return results

def is_recent(pub_str, hours=9999):
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

def main():
    print(f'=== GTA VI Telegram Bot ===')
    print(f'Token: {BOT_TOKEN[:12]}...')
    print(f'Channel raw: {repr(CHANNEL_RAW)}')

    # Verify bot itself
    me = tg('getMe')
    print(f'Bot: {me.get("result",{}).get("username","??")} | ok={me.get("ok")}')

    # Find working channel ID
    print('\nSearching for channel...')
    channel_id = find_channel()
    if not channel_id:
        print('FATAL: Cannot find channel. Exiting.')
        sys.exit(1)

    print(f'\nUsing channel_id: {channel_id}')

    # Fetch news
    print('\nFetching news...')
    items = get_news()
    print(f'Total: {len(items)} items')

    posted, had_before = load_hashes()
    updated = set(posted)
    max_posts = 5 if not had_before else 10

    count = errors = 0
    for item in items[:max_posts*3]:
        if count >= max_posts: break
        h = hashlib.md5((item['link'] or item['title']).encode()).hexdigest()
        if h in posted:
            continue

        print(f'\n  → {item["title"][:65]}')
        result = tg('sendMessage',
                    chat_id=channel_id,
                    text=make_message(item),
                    parse_mode='HTML',
                    disable_web_page_preview=False)

        if result.get('ok'):
            updated.add(h)
            count += 1
            print(f'  ✅ Posted!')
        else:
            errors += 1
            print(f'  ❌ {result.get("error_code")} {result.get("description")}')

    save_hashes(updated)
    print(f'\n=== Done: {count} posted, {errors} errors ===')
    if errors > 0 and count == 0:
        sys.exit(1)

if __name__ == '__main__':
    main()
