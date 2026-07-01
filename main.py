import requests
import os
import sys
import re
from datetime import datetime

VK_TOKEN = os.environ.get('VK_TOKEN')
TG_TOKEN = os.environ.get('TG_TOKEN')
GROUP_ID = os.environ.get('GROUP_ID')
CHAT_ID = os.environ.get('CHAT_ID')

# Файл для хранения ID последнего отправленного поста
LAST_POST_FILE = 'last_post_id.txt'

REPLACE_LINKS = {
    't.me/student_ast_kazak': 'vk.com/student_ast_kazak',
    'https://t.me/student_ast_kazak': 'vk.com/student_ast_kazak',
    'http://t.me/student_ast_kazak': 'vk.com/student_ast_kazak',
}

def read_last_post_id():
    """Читает сохранённый ID последнего поста из файла"""
    try:
        with open(LAST_POST_FILE, 'r') as f:
            return int(f.read().strip())
    except:
        return None

def save_last_post_id(post_id):
    """Сохраняет ID последнего поста в файл"""
    with open(LAST_POST_FILE, 'w') as f:
        f.write(str(post_id))

def replace_links(text):
    if not text:
        return text
    for old_link, new_link in REPLACE_LINKS.items():
        text = text.replace(old_link, new_link)
    return text

def send_to_telegram(text, photo_url=None):
    text = replace_links(text)
    
    if photo_url:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendPhoto"
        params = {
            'chat_id': CHAT_ID,
            'photo': photo_url,
            'caption': text,
            'parse_mode': 'HTML'
        }
    else:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        params = {
            'chat_id': CHAT_ID,
            'text': text,
            'parse_mode': 'HTML'
        }
    
    response = requests.get(url, params=params)
    return response

# Основная логика — выполняется один раз при запуске
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
            # Первый запуск — просто запоминаем
            save_last_post_id(post_id)
            print(f"[{datetime.now()}] Первый запуск. Запомнен пост {post_id}")
        
        elif post_id != last_id:
            # Новый пост!
            text = post.get('text', '')
            
            photo_url = None
            if 'attachments' in post:
                for attachment in post['attachments']:
                    if attachment['type'] == 'photo':
                        sizes = attachment['photo']['sizes']
                        photo_url = sizes[-1]['url']
                        break
            
            send_to_telegram(text, photo_url)
            save_last_post_id(post_id)
            print(f"[{datetime.now()}] Пост {post_id} отправлен")
        
        else:
            print(f"[{datetime.now()}] Новых постов нет")
    
    else:
        print(f"[{datetime.now()}] Постов нет или ошибка VK")

except Exception as e:
    print(f"[{datetime.now()}] Ошибка: {e}")
    sys.exit(1)
