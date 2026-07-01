import requests
import os
import time
import sys
from datetime import datetime

print("[ДИАГНОСТИКА] Скрипт запущен")

# Чтение переменных окружения
VK_TOKEN = os.environ.get('VK_TOKEN')
TG_TOKEN = os.environ.get('TG_TOKEN')
GROUP_ID = os.environ.get('GROUP_ID')
CHAT_ID = os.environ.get('CHAT_ID')

print(f"[ДИАГНОСТИКА] VK_TOKEN: {'Есть' if VK_TOKEN else 'НЕТ!'}")
print(f"[ДИАГНОСТИКА] TG_TOKEN: {'Есть' if TG_TOKEN else 'НЕТ!'}")
print(f"[ДИАГНОСТИКА] GROUP_ID: {GROUP_ID}")
print(f"[ДИАГНОСТИКА] CHAT_ID: {CHAT_ID}")

if not all([VK_TOKEN, TG_TOKEN, GROUP_ID, CHAT_ID]):
    print("[ОШИБКА] Не все переменные окружения заданы!")
    sys.exit(1)

last_post_id = None
print("[ДИАГНОСТИКА] Начинаю проверку постов...")

while True:
    try:
        print(f"[{datetime.now()}] Проверяю новые посты...")
        
        url = "https://api.vk.com/method/wall.get"
        params = {
            'owner_id': GROUP_ID,
            'count': 1,
            'access_token': VK_TOKEN,
            'v': '5.131'
        }
        response = requests.get(url, params=params).json()
        print(f"[{datetime.now()}] Ответ VK: {response}")
        
        if response.get('response') and response['response']['items']:
            post = response['response']['items'][0]
            post_id = post['id']
            print(f"[{datetime.now()}] Найден пост {post_id}, last_post_id = {last_post_id}")
            
            if post_id != last_post_id:
                text = post.get('text', '')
                if not text:
                    text = '📢 Новый пост (без текста)'
                
                print(f"[{datetime.now()}] Отправляю в Telegram: {text[:50]}...")
                
                tg_url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
                tg_params = {
                    'chat_id': CHAT_ID,
                    'text': f"📢 Новый пост:\n\n{text}",
                    'parse_mode': 'HTML'
                }
                tg_response = requests.get(tg_url, params=tg_params)
                print(f"[{datetime.now()}] Ответ Telegram: {tg_response.text}")
                
                last_post_id = post_id
                print(f"[{datetime.now()}] Пост {post_id} отправлен")
            else:
                print(f"[{datetime.now()}] Пост {post_id} уже был отправлен")
        else:
            print(f"[{datetime.now()}] Постов нет или ошибка VK")
        
        time.sleep(60)
        
    except Exception as e:
        print(f"[{datetime.now()}] ОШИБКА: {e}")
        time.sleep(60)
