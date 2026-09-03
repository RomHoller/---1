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
    for old, new in REPLACE_LINKS.items():
        text = text.replace(old, new)
    for old, new in REPLACE_TEXT.items():
        text = text.replace(old, new)
    text = add_space_after_emoji(text)
    text = make_first_line_bold(text)
    text = make_phrases_bold(text)
    return text

def get_all_photo_urls(sizes):
    """Получает все доступные размеры фото"""
    urls = []
    for size in sizes:
        urls.append(size['url'])
    return urls

def send_media_group(photos, caption):
    """Отправляет все фото одним альбомом"""
    if not photos:
        send_text_only(caption)
        return
    
    print(f"[ОТПРАВКА] Формируем альбом из {len(photos)} фото")
    
    # Формируем медиа-группу
    media = []
    for i, photo in enumerate(photos):
        if i == 0 and caption:
            media.append({
                'type': 'photo',
                'media': photo,
                'caption': caption,
                'parse_mode': 'HTML'
            })
        else:
            media.append({'type': 'photo', 'media': photo})
    
    # Отправляем по 10 фото (лимит Telegram)
    for batch_idx in range(0, len(media), 10):
        batch = media[batch_idx:batch_idx+10]
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMediaGroup"
        
        try:
            response = requests.post(url, json={'chat_id': CHAT_ID, 'media': batch}, timeout=30)
            
            if response.status_code == 200:
                print(f"[ОТПРАВКА] Альбом из {len(batch)} фото отправлен")
            else:
                error_data = response.json()
                error_msg = error_data.get('description', '')
                print(f"[ОШИБКА] {error_msg}")
                
                # Если ошибка с фото - пробуем отправить альбом без подписи
                if 'WEBPAGE_CURL_FAILED' in error_msg:
                    print("[ПОВТОР] Пробуем отправить альбом без подписи...")
                    send_media_group_no_caption(photos, caption)
                else:
                    send_text_only(caption)
                    
        except Exception as e:
            print(f"[ОШИБКА] {e}")
            send_text_only(caption)

def send_media_group_no_caption(photos, caption):
    """Отправляет альбом без подписи, а текст отдельно"""
    send_text_only(caption)
    
    media = []
    for photo in photos:
        media.append({'type': 'photo', 'media': photo})
    
    for batch_idx in range(0, len(media), 10):
        batch = media[batch_idx:batch_idx+10]
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMediaGroup"
        
        try:
            response = requests.post(url, json={'chat_id': CHAT_ID, 'media': batch}, timeout=30)
            if response.status_code == 200:
                print(f"[ОТПРАВКА] Альбом из {len(batch)} фото отправлен (без подписи)")
            else:
                print(f"[ОШИБКА] {response.text}")
        except Exception as e:
            print(f"[ОШИБКА] {e}")

def send_text_only(text):
    if not text:
        return
    
    try:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        response = requests.post(url, json={
            'chat_id': CHAT_ID,
            'text': text,
            'parse_mode': 'HTML',
            'disable_web_page_preview': True
        })
        
        if response.status_code == 200:
            print("[ОК] Текст отправлен")
        else:
            print(f"[ОШИБКА] {response.text}")
    except Exception as e:
        print(f"[ОШИБКА] {e}")

# === ОСНОВНАЯ ЛОГИКА ===
try:
    print(f"[{datetime.now()}] Проверка новых постов...")
    
    last_id = read_last_id()
    print(f"[{datetime.now()}] Последний сохранённый ID: {last_id}")
    
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
    
    post = None
    for p in r['response']['items']:
        if not p.get('is_pinned', False):
            post = p
            break
    if post is None:
        post = r['response']['items'][0]
    
    post_id = post['id']
    print(f"[{datetime.now()}] Текущий пост: {post_id}")
    
    if last_id is not None and post_id == last_id:
        print(f"[{datetime.now()}] Пост {post_id} уже был отправлен. Пропускаем.")
        sys.exit(0)
    
    raw_text = post.get('text', '')
    formatted_text = format_text(raw_text)
    print(f"[ТЕКСТ] {formatted_text[:100]}...")
    
    photos = []
    video_links = []
    
    if 'attachments' in post:
        for a in post['attachments']:
            if a['type'] == 'photo':
                # Берем все размеры фото, чтобы был выбор
                sizes = a['photo']['sizes']
                # Используем самый большой размер
                photo_url = sizes[-1]['url']
                photos.append(photo_url)
                print(f"[ФОТО] Добавлено фото (размер: {sizes[-1]['type']})")
            elif a['type'] == 'video':
                v = a['video']
                video_links.append(f"https://vk.com/video{v['owner_id']}_{v['id']}")
    
    if video_links:
        formatted_text += "\n\n🎬 Видео:\n" + "\n".join(video_links)
    
    print(f"[МЕДИА] Фото: {len(photos)}, Видео: {len(video_links)}")
    
    if photos:
        send_media_group(photos, formatted_text)
    else:
        send_text_only(formatted_text)
    
    save_last_id(post_id)
    print(f"[{datetime.now()}] Пост {post_id} обработан (фото: {len(photos)}, видео: {len(video_links)})")
    
except Exception as e:
    print(f"[{datetime.now()}] ОШИБКА: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
