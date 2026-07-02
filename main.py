import requests
import time
import re
import os
from datetime import datetime

VK_TOKEN = "сюда_свой_vk_токен"
TG_TOKEN = "сюда_свой_telegram_токен"
GROUP_ID = "сюда_id_группы"
CHAT_ID = "сюда_id_чата"

REPLACE_LINKS = {
    't.me/student_ast_kazak': 'vk.com/student_ast_kazak',
    'https://t.me/student_ast_kazak': 'vk.com/student_ast_kazak',
}

REPLACE_TEXT = {
    'Подписаться на Сотню в TG': 'Подписаться на Сотню в ВК',
}

BOLD_PHRASES = [
    'Слава Богу, что мы казаки!',
    'Подписаться на Сотню в ВК',
]

LAST_ID_FILE = '/tmp/last_post_id.txt'

def read_last_id():
    try:
        with open(LAST_ID_FILE, 'r') as f:
            return int(f.read().strip())
    except:
        return None

def save_last_id(post_id):
    with open(LAST_ID_FILE, 'w') as f:
        f.write(str(post_id))

def add_space_after_emoji(text):
    emoji_pattern = r'([\U0001F000-\U0001FFFF]|[\u2600-\u27BF]|[\u2000-\u206F]|[\u2300-\u23FF])'
    return re.sub(f'({emoji_pattern})(?![ ])', r'\1 ', text)

def make_bold(text):
    for phrase in BOLD_PHRASES:
        text = text.replace(phrase, f"<b>{phrase}</b>")
    return text

def format_text(text):
    if not text:
        return text
    for old, new in REPLACE_LINKS.items():
        text = text.replace(old, new)
    for old, new in REPLACE_TEXT.items():
        text = text.replace(old, new)
    text = add_space_after_emoji(text)
    text = make_bold(text)
    return text

# === ОСНОВНАЯ ЛОГИКА ===
while True:
    try:
        r = requests.get(
            "https://api.vk.com/method/wall.get",
            params={
                'owner_id': GROUP_ID,
                'count': 2,
                'access_token': VK_TOKEN,
                'v': '5.131'
            }
        ).json()
        
        if r.get('response') and r['response']['items']:
            # Ищем первый НЕзакрепленный пост
            post = None
            for p in r['response']['items']:
                if not p.get('is_pinned', False):
                    post = p
                    break
            if post is None:
                post = r['response']['items'][0]
            
            last_id = read_last_id()
            
            # Если пост новый или бот только запустился
            if last_id is None or post['id'] != last_id:
                text = format_text(post.get('text', ''))
                
                photos = []
                video_links = []
                if 'attachments' in post:
                    for a in post['attachments']:
                        if a['type'] == 'photo':
                            photos.append(a['photo']['sizes'][-1]['url'])
                        elif a['type'] == 'video':
                            v = a['video']
                            video_links.append(f"https://vk.com/video{v['owner_id']}_{v['id']}")
                
                if video_links:
                    text += "\n\n🎬 Видео:\n" + "\n".join(video_links)
                
                if photos:
                    media = []
                    for i, url in enumerate(photos):
                        if i == 0 and text:
                            media.append({'type': 'photo', 'media': url, 'caption': text, 'parse_mode': 'HTML'})
                        else:
                            media.append({'type': 'photo', 'media': url})
                    for i in range(0, len(media), 10):
                        requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMediaGroup", json={'chat_id': CHAT_ID, 'media': media[i:i+10]})
                else:
                    requests.get(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", params={'chat_id': CHAT_ID, 'text': text, 'parse_mode': 'HTML'})
                
                save_last_id(post['id'])
                print(f"[{datetime.now()}] Пост {post['id']} отправлен")
            else:
                print(f"[{datetime.now()}] Новых постов нет")
        
        time.sleep(60)
    except Exception as e:
        print(f"[{datetime.now()}] Ошибка: {e}")
        time.sleep(60)
