import requests, os, sys

BOT_TOKEN = os.environ['TELEGRAM_BOT_TOKEN'].strip()
CHANNEL   = '-1004401509809'

def tg(method, **kwargs):
    r = requests.post(
        f'https://api.telegram.org/bot{BOT_TOKEN}/{method}',
        json=kwargs, timeout=15
    )
    return r.json()

# 1. Get bot's own user ID
me = tg('getMe')
bot_id = me['result']['id']
print(f"Bot ID: {bot_id}, username: {me['result']['username']}")

# 2. Check bot membership in channel
print(f"\nChecking bot membership in {CHANNEL}...")
member = tg('getChatMember', chat_id=CHANNEL, user_id=bot_id)
print(f"Result: {member}")

# 3. Try sending a simple test message
print(f"\nAttempting test message...")
result = tg('sendMessage', chat_id=CHANNEL, text='🤖 Тест подключения GTA VI Tracker Bot')
print(f"sendMessage result: {result}")

# 4. Also try with username
print(f"\nAttempting with @GTAVITracker...")
result2 = tg('sendMessage', chat_id='@GTAVITracker', text='🤖 Тест подключения')
print(f"Result: {result2}")
