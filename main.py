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

# === ФРАЗЫ, КОТОРЫЕ ДЕЛАЕМ ЖИРНЫМИ ===
BOLD_PHRASES = [
    'Слава Богу, что мы казаки!',
    'Слава богу, что мы казаки!',
    'Подписаться на Сотню в ВК',
    'подписаться на Сотню в ВК',
]

def add_space_after_emoji(text):
    """Ставит пробел после каждого эмодзи, если его нет"""
    # Простой regex: ищем эмодзи и ставим после него пробел, если его нет
    emoji_pattern = r'([\U0001F000-\U0001FFFF]|[\u2600-\u27BF]|[\u2000-\u206F]|[\u2300-\u23FF]|[\u2500-\u27FF])'
    result = re.sub(f'({emoji_pattern})(?![ ])', r'\1 ', text)
    return result

def make_phrases_bold(text):
    """Делает указанные фразы жирными"""
    for phrase in BOLD_PHRASES:
        if phrase in text:
            text = text.replace(phrase, f"<b>{phrase}</b>")
    return text

def make_first_line_bold(text):
    """Делает первую строку текста жирной (до первого переноса)"""
    if not text:
        return text
    parts = text.split('\n', 1)
    if len(parts) == 1:
        return f"<b>{parts[0]}</b>"
    else:
        return f"<b>{parts[0]}</b>\n{parts[1]}"

def replace_all(text):
    if not text:
        return text
    # Заменяем ссылки
    for old, new in REPLACE_LINKS.items():
        text = text.replace(old, new)
    # Заменяем текст
    for old, new in REPLACE_TEXT.items():
        text = text.replace(old, new)
    return text

def format_text(text):
    """Применяет все форматирования к тексту"""
    if not text:
        return text
    
    # 1. Заменяем ссылки и текст
    text = replace_all(text)
    
    # 2. Ставим пробелы после эмодзи
    text = add_space_after_emoji(text)
    
    # 3. Делаем первую строку жирной
    text = make_first_line_bold(text)
    
    # 4. Делаем жирными указанные фразы (они могут быть в любом месте)
    text = make_phrases_bold(text)
    
    return text

def send_telegram_message(text, photos=None, video_links=None):
    """Отправляет текст, фото (альбомом) и ссылки на видео"""
    # Форматируем текст
    text = format_text(text)
    
    # Добавляем ссылки на видео в конец текста
    if video_links:
        video_text = "\n\n🎬 Видео:\n" + "\n".join(video_links)
        text += video_text
    
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

# === ОСНОВНАЯ ЛОГИКА ===
try:
    print(f"[{datetime.now()}] Проверка новых постов...")
    
    # Запрашиваем 2 поста, чтобы обойти закрепленный
    response = requests.get(
        "https://api.vk.com/method/wall.get",
        params={
            'owner_id': GROUP_ID,
            'count': 2,
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
    
    # Ищем первый НЕзакрепленный пост
    post = None
    for p in response['response']['items']:
        if not p.get('is_pinned', False):
            post = p
            break
    
    if post is None:
        post = response['response']['items'][0]
    
    post_id = post['id']
    text = post.get('text', '')
    
    print(f"[{datetime.now()}] Найден пост #{post_id}")
    
    photos = []
    video_links = []
    
    if 'attachments' in post:
        for attachment in post['attachments']:
            if attachment['type'] == 'photo':
                sizes = attachment['photo']['sizes']
                photos.append(sizes[-1]['url'])
            elif attachment['type'] == 'video':
                video = attachment['video']
                video_url = f"https://vk.com/video{video['owner_id']}_{video['id']}"
                video_links.append(video_url)
    
    print(f"[{datetime.now()}] Фото: {len(photos)} шт., видео: {len(video_links)} шт.")
    
    send_telegram_message(text, photos if photos else None, video_links if video_links else None)
    
    print(f"[{datetime.now()}] Пост #{post_id} успешно отправлен!")
    
except Exception as e:
    print(f"[{datetime.now()}] КРИТИЧЕСКАЯ ОШИБКА: {e}")
    sys.exit(1)
