import requests
import os
import time
import sys
import re
from datetime import datetime

VK_TOKEN = os.environ.get('VK_TOKEN')
TG_TOKEN = os.environ.get('TG_TOKEN')
GROUP_ID = os.environ.get('GROUP_ID')
CHAT_ID = os.environ.get('CHAT_ID')

# ⚙️ НАСТРОЙКА ЗАМЕНЫ ССЫЛОК
# student_ast_kazak - одинаковый тег в обоих соцсетях
REPLACE_LINKS = {
    # Меняем ссылку на Telegram → ссылку на ВК
    't.me/student_ast_kazak': 'vk.com/student_ast_kazak',
    'https://t.me/student_ast_kazak': 'vk.com/student_ast_kazak',
    'http://t.me/student_ast_kazak': 'vk.com/student_ast_kazak',
}

if not all([VK_TOKEN, TG_TOKEN, GROUP_ID, CHAT_ID]):
    print("Ошибка: не все переменные окружения заданы!")
    sys.exit(1)

last_post_id = None

def replace_links(text):
    """Заменяет ссылки в тексте по словарю REPLACE_LINKS"""
    if not text:
        return text
    
    for old_link, new_link in REPLACE_LINKS.items():
        text = text.replace(old_link, new_link)
    
    return text

def send_to_telegram(text, photo_url=None):
    """Отправляет текст и фото в Telegram"""
    
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

while True:
    try:
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
            
            if post_id != last_post_id:
                text = post.get('text', '')
                
                photo_url = None
                if 'attachments' in post:
                    for attachment in post['attachments']:
                        if attachment['type'] == 'photo':
                            sizes = attachment['photo']['sizes']
                            photo_url = sizes[-1]['url']
                            break
                
                send_to_telegram(text, photo_url)
                
                last_post_id = post_id
                print(f"[{datetime.now()}] Пост {post_id} отправлен")
        
        time.sleep(60)
        
    except Exception as e:
        print(f"[{datetime.now()}] Ошибка: {e}")
        time.sleep(60)
