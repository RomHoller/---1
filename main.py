import requests
import os
import sys
import re
import subprocess
from datetime import datetime

VK_TOKEN = os.environ.get('VK_TOKEN')
TG_TOKEN = os.environ.get('TG_TOKEN')
GROUP_ID = os.environ.get('GROUP_ID')
CHAT_ID = os.environ.get('CHAT_ID')

if not all([VK_TOKEN, TG_TOKEN, GROUP_ID, CHAT_ID]):
    print("[ОШИБКА] Не все переменные окружения заданы!")
    sys.exit(1)

# === НАСТРОЙКИ ===
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

LAST_ID_FILE = 'last_id.txt'

def read_last_id():
    try:
        if os.path.exists(LAST_ID_FILE):
            with open(LAST_ID_FILE, 'r') as f:
                content = f.read().strip()
                return int(content) if content else None
    except:
        pass
    return None

def save_last_id(post_id):
    try:
        with open(LAST_ID_FILE, 'w') as f:
            f.write(str(post_id))
        
        repo_url = f"https://x-access-token:{os.environ.get('GITHUB_TOKEN')}@github.com/{os.environ.get('GITHUB_REPOSITORY')}.git"
        
        subprocess.run(['git', 'config', '--global', 'user.email', 'bot@github.com'], check=True)
        subprocess.run(['git', 'config', '--global', 'user.name', 'GitHub Actions Bot'], check=True)
        subprocess.run(['git', 'add', LAST_ID_FILE], check=True)
        subprocess.run(['git', 'commit', '-m', f'Update last post ID to {post_id}'], check=True)
        subprocess.run(['git', 'push', repo_url, 'HEAD:main'], check=True)
        
        print(f"[СОХРАНЕНИЕ] ID {post_id} сохранён в репозитории")
    except Exception as e:
        print(f"[ОШИБКА СОХРАНЕНИЯ] {e}")

def add_space_after_emoji(text):
    emoji_pattern = r'([\U0001F000-\U0001FFFF]|[\u2600-\u27BF]|[\u2000-\u206F]|[\u2300-\u23FF])'
    return re.sub(f'({emoji_pattern})(?![ ])', r'\1 ', text)

def make_first_line_bold(text):
    """Делает первую строку жирной (до первого переноса)"""
    if not text:
        return text
    parts = text.split('\n', 1)
    if len(parts) == 1:
        return f"<b>{parts[0]}</b>"
    else:
        return f"<b>{parts[0]}</b>\n{parts[1]}"

def make_phrases_bold(text):
    for phrase in BOLD_PHRASES:
        text = text.replace(phrase, f"<b>{phrase}</b>")
    return text

def format_text(text):
    if not text:
        return text
    # Заменяем ссылки и текст
    for old, new in REPLACE_LINKS.items():
        text = text.replace(old, new)
    for old, new in REPLACE_TEXT.items():
        text = text.replace(old, new)
    # Пробелы после эмодзи
    text = add_space_after_emoji(text)
    # Жирный шрифт для первой строки
    text = make_first_line_bold(text)
    # Жирный шрифт для фраз
    text = make_phrases_bold(text)
    return text

def send_media_group(photos, caption):
    """Отправляет все фото одним альбомом с подписью"""
    if not photos:
        return None
    
    media = []
    for i, url in enumerate(photos):
        if i == 0 and caption:
            media.append({
                'type': 'photo',
                'media': url,
                'caption': caption,
                'parse_mode': 'HTML'
            })
        else:
            media.append({'type': 'photo', 'media': url})
    
    # Отправляем по 10 фото (лимит Telegram)
    for i in range(0, len(media), 10):
        batch = media[i:i+10]
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMediaGroup"
        response = requests.post(url, json={'chat_id': CHAT_ID, 'media': batch})
        if response.status_code != 200:
            print(f"[ОШИБКА TELEGRAM] {response.text}")
        else:
            print(f"[ОТПРАВКА] Альбом из {len(batch)} фото отправлен")

# === ОСНОВНАЯ ЛОГИКА ===
try:
    print(f"[{datetime.now()}] Проверка новых постов...")
    
    # Читаем сохранённый ID
    last_id = read_last_id()
    print(f"[{datetime.now()}] Последний сохранённый ID: {last_id}")
    
    # Запрос к VK
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
    print(f"[{datetime.now()}] Текущий пост: {post_id}")
    
    # Если ID совпадает с сохранённым — пропускаем
    if last_id is not None and post_id == last_id:
        print(f"[{datetime.now()}] Пост {post_id} уже был отправлен. Пропускаем.")
        sys.exit(0)
    
    # === ФОРМАТИРУЕМ ТЕКСТ ===
    raw_text = post.get('text', '')
    formatted_text = format_text(raw_text)
    print(f"[ТЕКСТ] {formatted_text[:100]}...")
    
    # === СОБИРАЕМ МЕДИА ===
    photos = []
    video_links = []
    if 'attachments' in post:
        for a in post['attachments']:
            if a['type'] == 'photo':
                # Берём самую большую фотографию
                sizes = a['photo']['sizes']
                photos.append(sizes[-1]['url'])
            elif a['type'] == 'video':
                v = a['video']
                video_links.append(f"https://vk.com/video{v['owner_id']}_{v['id']}")
    
    # Добавляем ссылки на видео в конец текста
    if video_links:
        formatted_text += "\n\n🎬 Видео:\n" + "\n".join(video_links)
    
    print(f"[МЕДИА] Фото: {len(photos)}, Видео: {len(video_links)}")
    
    # === ОТПРАВКА ===
    if photos:
        # Отправляем альбом с фото
        send_media_group(photos, formatted_text)
    else:
        # Если фото нет — отправляем только текст
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        response = requests.get(url, params={
            'chat_id': CHAT_ID,
            'text': formatted_text,
            'parse_mode': 'HTML'
        })
        if response.status_code != 200:
            print(f"[ОШИБКА TELEGRAM] {response.text}")
    
    # Сохраняем ID в репозиторий
    save_last_id(post_id)
    print(f"[{datetime.now()}] Пост {post_id} отправлен (фото: {len(photos)}, видео: {len(video_links)})")
    
except Exception as e:
    print(f"[{datetime.now()}] ОШИБКА: {e}")
    sys.exit(1)
