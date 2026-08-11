import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
import os, json, hashlib

BOT_TOKEN = os.environ['TELEGRAM_BOT_TOKEN']
CHANNEL   = os.environ.get('TELEGRAM_CHANNEL', '@GTAVITracker')
SITE_URL  = 'https://marat8715-png.github.io/gta6-tracker/'
RSS_URL   = 'https://news.google.com/rss/search?q=GTA+VI+Grand+Theft+Auto&hl=ru&gl=RU&ceid=RU:ru'
HASHES_FILE = 'posted_hashes.json'

def get_news():
    r = requests.get(RSS_URL, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
    root = ET.fromstring(r.content)
    items = []
    for item in root.findall('.//item')[:8]:
        items.append({
            'title':       item.findtext('title', '').strip(),
            'link':        item.findtext('link', '').strip(),
            'pubDate':     item.findtext('pubDate', ''),
            'description': item.findtext('description', '').strip(),
            'source':      item.findtext('source', ''),
        })
    return items

def is_recent(pub_date_str, hours=3):
    try:
        pub_dt = parsedate_to_datetime(pub_date_str)
        return (datetime.now(timezone.utc) - pub_dt) <= timedelta(hours=hours)
    except:
        return True

def load_hashes():
    try:
        with open(HASHES_FILE) as f:
            return set(json.load(f))
    except:
        return set()

def save_hashes(hashes):
    with open(HASHES_FILE, 'w') as f:
        json.dump(list(hashes)[-200:], f)

def clean_html(text):
    import re
    return re.sub(r'<[^>]+>', '', text).strip()

def post(item):
    title = item['title']
    link  = item['link']
    desc  = clean_html(item['description'])[:280]
    if desc: desc = f"\n\n{desc}…"

    text = (
        f"🎮 <b>GTA VI — Новость</b>{desc}\n\n"
        f"📰 <b>{title}</b>\n\n"
        f"🔗 <a href='{link}'>Читать полностью</a>\n"
        f"🌐 <a href='{SITE_URL}'>GTA VI TRACKER — все новости</a>"
    )
    r = requests.post(
        f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage',
        json={'chat_id': CHANNEL, 'text': text,
              'parse_mode': 'HTML', 'disable_web_page_preview': False},
        timeout=10
    )
    return r.json()

def main():
    items   = get_news()
    posted  = load_hashes()
    updated = set(posted)
    count   = 0

    for item in items:
        h = hashlib.md5(item['link'].encode()).hexdigest()
        if h in posted:
            print(f"Skip (already posted): {item['title'][:60]}")
            continue
        if not is_recent(item['pubDate'], hours=3):
            print(f"Skip (old): {item['title'][:60]}")
            continue

        result = post(item)
        if result.get('ok'):
            updated.add(h)
            count += 1
            print(f"✅ Posted: {item['title'][:70]}")
        else:
            print(f"❌ Error: {result.get('description','unknown')}")

    save_hashes(updated)
    print(f"\nДобавлено {count} новых новостей в @{CHANNEL}")

if __name__ == '__main__':
    main()
