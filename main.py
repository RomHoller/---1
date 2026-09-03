import requests
import os
import sys
import re
import subprocess
from datetime import datetime
from time import sleep

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

def remove_links(text):
    """Удаляет все URL из текста для избежания WEBPAGE_CURL_FAILED"""
    return re.sub(r'https?://\S+', '', text)

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
    # Удаляем ссылки для избежания ошибки WEBPAGE_CURL_FAILED
    text = remove_links(text)
    return text

def get_best_photo_url(sizes):
    """Получает самый надежный URL фото"""
    # Приоритетные размеры (в порядке надежности)
    priority_sizes = ['x', 'y', 'z', 'w', 'r', 'q', 'p', 'o']
    
    for size_type in priority_sizes:
        for size in sizes:
            if size['type'] == size_type:
                return size['url']
    
    # Если ничего не найдено - берем последний (самый большой)
    return sizes[-1]['url']

def check_photo_available(url):
    """Проверяет доступность фото"""
    try:
        response = requests.head(url, timeout=10)
        return response.status_code == 200
    except:
        return False

def download_photo(url):
    """Скачивает фото и возвращает его содержимое"""
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            return response.content
        return None
    except:
        return None

def send_media_group(photos, caption):
    """Отправляет все фото одним альбомом с обработкой проблемных фото"""
    if not photos:
        send_text_only(caption)
        return
    
    print(f"[ОТПРАВКА] Формируем альбом из {len(photos)} фото")
    
    # Проверяем все фото и заменяем проблемные на скачанные версии
    valid_photos = []
    for i, url in enumerate(photos):
        print(f"[ПРОВЕРКА] Фото {i+1}...")
        
        # Проверяем доступность фото
        if check_photo_available(url):
            valid_photos.append(url)
            print(f"[ОК] Фото {i+1} доступно")
        else:
            print(f"[ПРЕДУПРЕЖДЕНИЕ] Фото {i+1} недоступно, пробуем скачать...")
            # Пробуем скачать фото
            photo_data = download_photo(url)
            if photo_data:
                # Сохраняем как временный файл и загружаем в Telegram
                temp_file = f'/tmp/photo_{i}.jpg'
                with open(temp_file, 'wb') as f:
                    f.write(photo_data)
                
                # Загружаем фото на сервер Telegram
                try:
                    with open(temp_file, 'rb') as f:
                        upload_response = requests.post(
                            f"https://api.telegram.org/bot{TG_TOKEN}/sendPhoto",
                            data={'chat_id': CHAT_ID},
                            files={'photo': f}
                        )
                        if upload_response.status_code == 200:
                            # Получаем file_id загруженного фото
                            file_id = upload_response.json()['result']['photo'][-1]['file_id']
                            # Используем file_id вместо URL
                            valid_photos.append(file_id)
                            print(f"[ОК] Фото {i+1} загружено как файл")
                        else:
                            print(f"[ОШИБКА] Не удалось загрузить фото {i+1}")
                except Exception as e:
                    print(f"[ОШИБКА] {e}")
                finally:
                    # Удаляем временный файл
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
            else:
                print(f"[ПРОПУСК] Фото {i+1} пропущено (недоступно)")
    
    if not valid_photos:
        print("[ОШИБКА] Нет доступных фото для отправки")
        send_text_only(caption)
        return
    
    print(f"[ОТПРАВКА] Отправляем альбом из {len(valid_photos)} фото")
    
    # Формируем медиа-группу
    media = []
    for i, photo in enumerate(valid_photos):
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
                
                # Если ошибка WEBPAGE_CURL_FAILED - пробуем отправить по одному
                if 'WEBPAGE_CURL_FAILED' in error_msg:
                    print("[ПОВТОР] Пробуем отправить фото по одному...")
                    send_photos_individually(valid_photos, caption)
        except Exception as e:
            print(f"[ОШИБКА] {e}")
            # При любой ошибке пробуем отправить по одному
            send_photos_individually(valid_photos, caption)

def send_photos_individually(photos, caption):
    """Отправляет фото по одному (как резервный вариант)"""
    success_count = 0
    
    for i, photo in enumerate(photos):
        try:
            if i == 0 and caption:
                response = requests.post(
                    f"https://api.telegram.org/bot{TG_TOKEN}/sendPhoto",
                    json={
                        'chat_id': CHAT_ID,
                        'photo': photo,
                        'caption': caption,
                        'parse_mode': 'HTML'
                    },
                    timeout=30
                )
            else:
                response = requests.post(
                    f"https://api.telegram.org/bot{TG_TOKEN}/sendPhoto",
                    json={'chat_id': CHAT_ID, 'photo': photo},
                    timeout=30
                )
            
            if response.status_code == 200:
                success_count += 1
                print(f"[ОК] Фото {i+1} отправлено")
            else:
                print(f"[ОШИБКА] Фото {i+1}: {response.text}")
        except Exception as e:
            print(f"[ОШИБКА] Фото {i+1}: {e}")
        
        sleep(0.5)  # Задержка между фото
    
    print(f"[ИТОГ] Отправлено {success_count} из {len(photos)} фото")

def send_text_only(text):
    """Отправляет только текст"""
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
                # Используем улучшенную функцию для получения URL
                sizes = a['photo']['sizes']
                photo_url = get_best_photo_url(sizes)
                photos.append(photo_url)
                print(f"[ФОТО] Добавлено фото: {photo_url[:80]}...")
            elif a['type'] == 'video':
                v = a['video']
                video_links.append(f"https://vk.com/video{v['owner_id']}_{v['id']}")
    
    # Добавляем ссылки на видео в конец текста
    if video_links:
        formatted_text += "\n\n🎬 Видео:\n" + "\n".join(video_links)
    
    print(f"[МЕДИА] Фото: {len(photos)}, Видео: {len(video_links)}")
    
    # === ОТПРАВКА ===
    if photos:
        # Отправляем альбомом
        send_media_group(photos, formatted_text)
    else:
        # Если фото нет — отправляем только текст
        send_text_only(formatted_text)
    
    # Сохраняем ID
    save_last_id(post_id)
    print(f"[{datetime.now()}] Пост {post_id} обработан (фото: {len(photos)}, видео: {len(video_links)})")
    
except Exception as e:
    print(f"[{datetime.now()}] ОШИБКА: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
