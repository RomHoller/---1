import requests
import os
import sys
import re
from datetime import datetime

VK_TOKEN = os.environ.get('VK_TOKEN')
TG_TOKEN = os.environ.get('TG_TOKEN')
GROUP_ID = os.environ.get('GROUP_ID')
CHAT_ID = os.environ.get('CHAT_ID')

LAST_POST_FILE = 'last_post_id.txt'

REPLACE_LINKS = {
    't.me/student_ast_kazak': 'vk.com/student_ast_kazak',
    'https://t.me/student_ast_kazak': 'vk.com/student_ast_kazak',
    'http://t.me/student_ast_kazak': 'vk.com/student_ast_kazak',
}

def read_last_post_id():
    try:
        with open(LAST_POST_FILE, 'r') as f:
            return int(f.read().strip())
    except:
        return None

def save_last_post_id(post_id):
    with open(LAST_POST_FILE, 'w') as f:
        f.write(str(post_id))

def replace_links(text):
    if not text:
        return text
    for old_link, new_link in REPLACE_LINKS.items():
        text = text.replace(old_link, new_link)
    return text

def send_media_group(photo_urls, caption=None):
    """
    Отправляет несколько фото одним сообщением (медиагруппой)
    Telegram API принимает до 10 фото за раз
    """
    if not photo_urls:
        return None
    
    # Подготавливаем медиагруппу
    media = []
    for i, url in enumerate(photo_urls):
        if i == 0 and caption:
            # Первое фото — с подписью
            media.append({
                'type': 'photo',
                'media': url,
                'caption': caption,
                'parse_mode': 'HTML'
            })
        else:
            # Остальные — без подписи
            media.append({
                'type': 'photo',
                'media': url
            })
    
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMediaGroup"
    params = {
        'chat_id': CHAT_ID,
        'media': str(media).replace("'", '"')  # Превращаем в JSON-строку
    }
    
    # Отправляем как JSON
    headers = {'Content-Type': 'application/json'}
    response = requests.post(url, json={'chat_id': CHAT_ID, 'media': media})
    return response

def send_text(text):
    """Отправляет только текст"""
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    params = {
        'chat_id': CHAT_ID,
        'text': text,
        'parse_mode': 'HTML'
    }
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
    
    if response.get('response') and response['response']['items']:
        post = response['response']['items'][0]
        post_id = post['id']
        
        last_id = read_last_post_id()
        
        if last_id is None:
            save_last_post_id(post_id)
            print(f"[{datetime.now()}] Первый запуск. Запомнен пост {post_id}")
        
        elif post_id != last_id:
            text = post.get('text', '')
            text = replace_links(text)
            
            # Собираем все фото
            photo_urls = []
            if 'attachments' in post:
                for attachment in post['attachments']:
                    if attachment['type'] == 'photo':
                        sizes = attachment['photo']['sizes']
                        photo_urls.append(sizes[-1]['url'])
            
            # Отправляем
            if photo_urls:
                # Все фото в одном сообщении (альбомом)
                # Если фото больше 10 — Telegram не примет, отправляем по 10
                for i in range(0, len(photo_urls), 10):
                    batch = photo_urls[i:i+10]
                    if i == 0:
                        # Первая группа — с текстом
                        send_media_group(batch, text)
                    else:
                        # Остальные группы — без текста
                        send_media_group(batch)
            else:
                # Если фото нет — отправляем только текст
                send_text(text)
            
            save_last_post_id(post_id)
            print(f"[{datetime.now()}] Пост {post_id} отправлен (фото: {len(photo_urls)})")
        
        else:
            print(f"[{datetime.now()}] Новых постов нет")
    
    else:
        print(f"[{datetime.now()}] Постов нет или ошибка VK")

except Exception as e:
    print(f"[{datetime.now()}] Ошибка: {e}")
    sys.exit(1)
