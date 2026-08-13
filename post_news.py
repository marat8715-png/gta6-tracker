import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
import os, json, hashlib, re, html

BOT_TOKEN   = os.environ['TELEGRAM_BOT_TOKEN']
CHANNEL     = os.environ.get('TELEGRAM_CHANNEL', '@GTAVITracker')
SITE_URL    = 'https://marat8715-png.github.io/gta6-tracker/'
HASHES_FILE = 'posted_hashes.json'

RSS_FEEDS = [
    'https://news.google.com/rss/search?q=GTA+VI+Grand+Theft+Auto+6&hl=ru&gl=RU&ceid=RU:ru',
    'https://news.google.com/rss/search?q=GTA+VI+Rockstar+Games&hl=ru&gl=RU&ceid=RU:ru',
]

def clean_html(text):
    text = re.sub(r'<[^>]+>', '', text)
    return html.unescape(text).strip()

def title_hash(title):
    normalized = re.sub(r'\W+', '', title.lower())[:80]
    return hashlib.md5(normalized.encode()).hexdigest()

def url_hash(url):
    return hashlib.md5(url.encode()).hexdigest()

def get_news():
    items = []
    seen_titles = set()
    for feed_url in RSS_FEEDS:
        try:
            r = requests.get(feed_url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
            root = ET.fromstring(r.content)
            for item in root.findall('.//item')[:10]:
                title = clean_html(item.findtext('title', ''))
                if not title:
                    continue
                th = title_hash(title)
                if th in seen_titles:
                    continue
                seen_titles.add(th)
                items.append({
                    'title':       title,
                    'link':        item.findtext('link', '').strip(),
                    'pubDate':     item.findtext('pubDate', ''),
                    'description': clean_html(item.findtext('description', '')),
                })
        except Exception as e:
            print(f'Feed error: {e}')
    print(f'Найдено статей из RSS: {len(items)}')
    return items

def is_recent(pub_date_str, hours=48):
    """Публикуем новости за последние 48 часов"""
    try:
        pub_dt = parsedate_to_datetime(pub_date_str)
        age = datetime.now(timezone.utc) - pub_dt
        print(f'  Возраст статьи: {int(age.total_seconds()/3600)} ч.')
        return age <= timedelta(hours=hours)
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
        json.dump(list(hashes)[-300:], f)

def post(item):
    title = item['title']
    link  = item['link']
    desc  = item['description'][:250]
    if desc:
        desc = f'\n\n{desc}…'

    text = (
        f'🎮 <b>GTA VI — Новость</b>{desc}\n\n'
        f'📰 <b>{title}</b>\n\n'
        f'🔗 <a href="{link}">Читать полностью</a>\n'
        f'🌐 <a href="{SITE_URL}">GTA VI TRACKER — все новости</a>'
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
        print(f'\n→ Проверяю: {item["title"][:60]}')
        uh = url_hash(item['link'])
        th = title_hash(item['title'])

        if uh in posted or th in posted:
            print(f'  Skip: уже публиковалось')
            continue

        if not is_recent(item['pubDate'], hours=48):
            print(f'  Skip: слишком старая (>48ч)')
            continue

        result = post(item)
        if result.get('ok'):
            updated.add(uh)
            updated.add(th)
            count += 1
            print(f'  ✅ Опубликовано!')
        else:
            print(f'  ❌ Ошибка Telegram: {result.get("description", "unknown")}')

    save_hashes(updated)
    print(f'\n=== Итого опубликовано: {count} новостей ===')

if __name__ == '__main__':
    main()
