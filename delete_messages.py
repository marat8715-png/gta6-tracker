import requests, os

BOT_TOKEN = os.environ['TELEGRAM_BOT_TOKEN']
CHANNEL   = "-1004401509809"

def tg(method, **kwargs):
    r = requests.post(f'https://api.telegram.org/bot{BOT_TOKEN}/{method}', json=kwargs, timeout=10)
    return r.json()

deleted = []
failed  = []

# Try deleting message IDs 1-20 to catch all bad ones
for msg_id in range(1, 21):
    result = tg('deleteMessage', chat_id=CHANNEL, message_id=msg_id)
    if result.get('ok'):
        deleted.append(msg_id)
        print(f"✅ Удалено #{msg_id}")
    else:
        failed.append(msg_id)
        print(f"   Пропущено #{msg_id}: {result.get('description','')}")

print(f"\nИтог: удалено {len(deleted)} сообщений: {deleted}")
