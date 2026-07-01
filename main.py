import requests
import os
import sys
import re
import signal
from datetime import datetime

# === ТАЙМАУТ 60 СЕКУНД ===
def timeout_handler(signum, frame):
    print("[ОШИБКА] Превышено время выполнения (60 секунд)")
    sys.exit(1)

signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(60)

VK_TOKEN = os.environ.get('VK_TOKEN')
TG_TOKEN = os.environ.get('TG_TOKEN')
GROUP_ID = os.environ.get('GROUP_ID')
CHAT_ID = os.environ.get('CHAT_ID')

if not all([VK_TOKEN, TG_TOKEN, GROUP_ID, CHAT_ID]):
    print("Ошибка: не все переменные окружения заданы!")
    sys.exit(1)

# === НАСТРОЙКА ЗАМЕН ===
REPLACE_LINKS = {
    't.me/student_ast_kazak': 'vk.com/student_ast_kazak',
    'https://t.me/student_ast_kazak': 'vk.com/student_ast_kazak',
    'http://t.me/student_ast_kazak': 'vk.com/student_ast_kazak',
}

REPLACE_TEXT = {
    'Подписаться на Сотню в TG': 'Подписаться на Сотню в ВК',
    'подписаться на Сотню в TG': 'подписаться на Сотню в ВК',
    'Подписаться на сотню в TG': 'Подписаться на сотню в ВК',
    'подписаться на сотню в TG': 'подписаться на сотню в ВК',
}

def replace_links_and_text(text):
    if not text:
        return text
    for old_link, new_link in REPLACE_LINKS.items():
        text = text.replace(old_link, new_link)
    for old_text, new_text in REPLACE_TEXT.items():
        text = text.replace(old_text, new_text)
    return text

def send_media_group(photo_urls, caption=None):
    if not photo_urls:
        return None
    media = []
    for i, url in enumerate(photo_urls):
        if i == 0 and caption:
            media.append({
                'type': 'photo',
                'media': url,
                'caption': caption,
                'parse_mode': 'HTML'
            })
        else:
            media.append({'type': 'photo', 'media': url})
    response = requests.post(
        f"https://api.telegram.org/bot{TG_TOKEN}/sendMediaGroup",
        json={'chat_id': CHAT_ID, 'media': media}
    )
    return response

def send_text(text):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    params = {'chat_id': CHAT_ID, 'text': text, 'parse_mode': 'HTML'}
    return requests.get(url, params=params)

try:
    print(f"[{datetime.now()}] Проверка новых постов...")
    
    url = "https://api.vk.com/method/wall.get"
    params = {
        'owner_id': GROUP_ID,
        'count': 1,
        'access_token': VK_TOKEN,
        'v': '5.131'
    }
    response = requests.get(url, params=params).json()
    
    # ДИАГНОСТИКА: выводим полный ответ VK
    print(f"[ДИАГНОСТИКА] Ответ VK: {response}")
    
    if response.get('response') and response['response']['items']:
        post = response['response']['items'][0]
        post_id = post['id']
        text = post.get('text', '')
        
        print(f"[ДИАГНОСТИКА] Найден пост ID={post_id}, текст: {text[:100]}...")
        
        # Заменяем ссылки и текст
        text = replace_links_and_text(text)
        
        # Собираем фото
        photo_urls = []
        if 'attachments' in post:
            for attachment in post['attachments']:
                if attachment['type'] == 'photo':
                    sizes = attachment['photo']['sizes']
                    photo_urls.append(sizes[-1]['url'])
        
        print(f"[ДИАГНОСТИКА] Фото: {len(photo_urls)} шт.")
        
        # Отправляем
        if photo_urls:
            for i in range(0, len(photo_urls), 10):
                batch = photo_urls[i:i+10]
                if i == 0:
                    send_media_group(batch, text)
                else:
                    send_media_group(batch)
        else:
            send_text(text)
        
        print(f"[{datetime.now()}] Пост {post_id} отправлен (фото: {len(photo_urls)})")
    else:
        print(f"[{datetime.now()}] Постов нет или ошибка VK")
        if 'error' in response:
            print(f"[ОШИБКА VK] {response['error']}")

except Exception as e:
    print(f"[{datetime.now()}] ОШИБКА: {e}")
    sys.exit(1)
