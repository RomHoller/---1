import requests
import os
import sys
import re
from datetime import datetime

# === ЧИТАЕМ СЕКРЕТЫ ИЗ ОКРУЖЕНИЯ (GITHUB ACTIONS) ===
VK_TOKEN = os.environ.get('VK_TOKEN')
TG_TOKEN = os.environ.get('TG_TOKEN')
GROUP_ID = os.environ.get('GROUP_ID')
CHAT_ID = os.environ.get('CHAT_ID')

if not all([VK_TOKEN, TG_TOKEN, GROUP_ID, CHAT_ID]):
    print("[ОШИБКА] Не все переменные окружения заданы!")
    sys.exit(1)

# === НАСТРОЙКИ ФОРМАТИРОВАНИЯ ===
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

LAST_ID_FILE = 'last_post_id.txt'

def read_last_id():
    """Читает ID последнего отправленного поста из файла"""
    try:
        if os.path.exists(LAST_ID_FILE):
            with open(LAST_ID_FILE, 'r') as f:
                return int(f.read().strip())
    except:
        pass
    return None

def save_last_id(post_id):
    """Сохраняет ID последнего отправленного поста в файл"""
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
try:
    print(f"[{datetime.now()}] Проверка новых постов...")
    
    # Запрашиваем 2 поста, чтобы обойти закрепленный
    r = requests.get(
        "https://api.vk.com/method/wall.get",
        params={
            'owner_id': GROUP_ID,
            'count': 2,
            'access_token': VK_TOKEN,
            'v': '5.131'
        }
    ).json()
    
    if 'error' in r:
        print(f"[ОШИБКА VK] {r['error']}")
        sys.exit(1)
    
    if not r.get('response') or not r['response']['items']:
        print(f"[{datetime.now()}] Постов нет")
        sys.exit(0)
    
    # Ищем первый НЕзакрепленный пост
    post = None
    for p in r['response']['items']:
        if not p.get('is_pinned', False):
            post = p
            break
    if post is None:
        post = r['response']['items'][0]
    
    post_id = post['id']
    
    # Проверяем, не отправляли ли уже этот пост
    last_id = read_last_id()
    
    if last_id is not None and post_id == last_id:
        print(f"[{datetime.now()}] Пост {post_id} уже был отправлен ранее. Пропускаем.")
        sys.exit(0)
    
    # Новый пост — отправляем
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
    
    # Отправляем в Telegram
    if photos:
        media = []
        for i, url in enumerate(photos):
            if i == 0 and text:
                media.append({'type': 'photo', 'media': url, 'caption': text, 'parse_mode': 'HTML'})
            else:
                media.append({'type': 'photo', 'media': url})
        for i in range(0, len(media), 10):
            resp = requests.post(
                f"https://api.telegram.org/bot{TG_TOKEN}/sendMediaGroup",
                json={'chat_id': CHAT_ID, 'media': media[i:i+10]}
            )
            if resp.status_code != 200:
                print(f"[ОШИБКА TELEGRAM] {resp.text}")
    else:
        resp = requests.get(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            params={'chat_id': CHAT_ID, 'text': text, 'parse_mode': 'HTML'}
        )
        if resp.status_code != 200:
            print(f"[ОШИБКА TELEGRAM] {resp.text}")
    
    # Сохраняем ID отправленного поста
    save_last_id(post_id)
    print(f"[{datetime.now()}] Пост {post_id} отправлен (фото: {len(photos)}, видео: {len(video_links)})")
    
except Exception as e:
    print(f"[{datetime.now()}] ОШИБКА: {e}")
    sys.exit(1)
