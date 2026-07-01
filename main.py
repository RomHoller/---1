import requests
import os
import sys
import re
from datetime import datetime

# === ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ ===
VK_TOKEN = os.environ.get('VK_TOKEN')
TG_TOKEN = os.environ.get('TG_TOKEN')
GROUP_ID = os.environ.get('GROUP_ID')
CHAT_ID = os.environ.get('CHAT_ID')

if not all([VK_TOKEN, TG_TOKEN, GROUP_ID, CHAT_ID]):
    print("[ОШИБКА] Не все переменные окружения заданы!")
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

def make_first_line_bold(text):
    """Делает первую строку текста жирной (до первого переноса)"""
    if not text:
        return text
    
    # Ищем первый перенос строки
    parts = text.split('\n', 1)
    
    if len(parts) == 1:
        # Если переноса нет — вся строка жирная
        return f"<b>{parts[0]}</b>"
    else:
        # Первая строка — жирная, остальное — как есть
        return f"<b>{parts[0]}</b>\n{parts[1]}"

def replace_all(text):
    if not text:
        return text
    for old, new in REPLACE_LINKS.items():
        text = text.replace(old, new)
    for old, new in REPLACE_TEXT.items():
        text = text.replace(old, new)
    return text

def send_telegram_message(text, photos=None):
    """Отправляет сообщение с жирной первой строкой"""
    # Сначала заменяем ссылки и текст
    text = replace_all(text)
    
    # Затем делаем первую строку жирной
    text = make_first_line_bold(text)
    
    if photos:
        media = []
        for i, url in enumerate(photos):
            if i == 0 and text:
                media.append({
                    'type': 'photo',
                    'media': url,
                    'caption': text,
                    'parse_mode': 'HTML'
                })
            else:
                media.append({'type': 'photo', 'media': url})
        
        for i in range(0, len(media), 10):
            batch = media[i:i+10]
            requests.post(
                f"https://api.telegram.org/bot{TG_TOKEN}/sendMediaGroup",
                json={'chat_id': CHAT_ID, 'media': batch}
            )
    else:
        requests.get(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            params={'chat_id': CHAT_ID, 'text': text, 'parse_mode': 'HTML'}
        )

def send_startup_notification():
    """Отправляет уведомление о запуске бота"""
    try:
        requests.get(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            params={
                'chat_id': CHAT_ID,
                'text': f"🔄 Бот запущен в {datetime.now().strftime('%H:%M:%S')}",
                'parse_mode': 'HTML'
            }
        )
        print("[ДИАГНОСТИКА] Уведомление о запуске отправлено")
    except Exception as e:
        print(f"[ДИАГНОСТИКА] Не удалось отправить уведомление: {e}")

# === ОСНОВНАЯ ЛОГИКА ===
try:
    print(f"[{datetime.now()}] Проверка новых постов...")
    
    send_startup_notification()
    
    response = requests.get(
        "https://api.vk.com/method/wall.get",
        params={
            'owner_id': GROUP_ID,
            'count': 1,
            'access_token': VK_TOKEN,
            'v': '5.131'
        }
    ).json()
    
    if 'error' in response:
        print(f"[ОШИБКА VK] {response['error']}")
        sys.exit(1)
    
    if not response.get('response') or not response['response']['items']:
        print(f"[{datetime.now()}] Постов в группе нет")
        sys.exit(0)
    
    post = response['response']['items'][0]
    post_id = post['id']
    text = post.get('text', '')
    
    print(f"[{datetime.now()}] Найден пост #{post_id}")
    
    photos = []
    if 'attachments' in post:
        for attachment in post['attachments']:
            if attachment['type'] == 'photo':
                sizes = attachment['photo']['sizes']
                photos.append(sizes[-1]['url'])
    
    print(f"[{datetime.now()}] Фото в посте: {len(photos)} шт.")
    
    send_telegram_message(text, photos if photos else None)
    
    print(f"[{datetime.now()}] Пост #{post_id} успешно отправлен!")
    
except Exception as e:
    print(f"[{datetime.now()}] КРИТИЧЕСКАЯ ОШИБКА: {e}")
    sys.exit(1)
