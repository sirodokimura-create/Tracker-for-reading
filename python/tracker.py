import sys
import os


script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)


import json
import requests
import re
import base64
import calendar_module
from datetime import datetime
from urllib.parse import urljoin


if sys.platform == 'win32':
    import io
    if sys.stdin is not None and hasattr(sys.stdin, 'buffer'):
        sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8')
    if sys.stdout is not None and hasattr(sys.stdout, 'buffer'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    if sys.stderr is not None and hasattr(sys.stderr, 'buffer'):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Безопасный вывод в stderr
def safe_stderr_print(msg):
    try:
        print(msg, file=sys.stderr)
        sys.stderr.flush()
    except:
        print(msg)

safe_stderr_print("Python процесс запущен!")

API_KEY = "AIzaSyAVopSdWmDv73diRWlaqkRqs4eO9mARywM"
USE_API_KEY = False

class BookParser:
    def __init__(self):
        safe_stderr_print("Инициализация...")
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.base_url = "https://www.googleapis.com/books/v1"
        self.desktop = self._get_desktop_path()
        self.data_file = os.path.join(self.desktop, 'books_data.json')
        self.books_data = self._load_books_data()
        self._build_reading_cache()
        safe_stderr_print(f"Загружено книг: {len(self.books_data)}")
        self._test_api_key()

    def _get_desktop_path(self):
        possible_paths = [
            os.path.join(os.path.expanduser('~'), 'Desktop'),
            os.path.join(os.path.expanduser('~'), 'Рабочий стол'),
        ]
        for path in possible_paths:
            if os.path.exists(path):
                return path
        return os.path.expanduser('~')

    def _load_books_data(self):
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        for book in data:
                            if 'status' not in book:
                                book['status'] = 'want_to_read'
                            if 'added_date' not in book:
                                book['added_date'] = datetime.now().isoformat()
                            if 'rating' not in book:
                                book['rating'] = 0
                            if 'genre' not in book:
                                book['genre'] = 'Без жанра'
                            if 'description' not in book:
                                book['description'] = ''
                            if 'notes' not in book:
                                book['notes'] = ''
                            if 'reading_sessions' not in book:
                                book['reading_sessions'] = []
                        return data
            return []
        except Exception as e:
            safe_stderr_print(f"Ошибка загрузки: {e}")
            return []

    def _build_reading_cache(self):
        self.reading_cache = {}
        for book in self.books_data:
            for sess in book.get('reading_sessions', []):
                try:
                    date_part = sess.split('T')[0]
                    self.reading_cache[date_part] = self.reading_cache.get(date_part, 0) + 1
                except:
                    pass

    def _save_books_data(self):
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.books_data, f, ensure_ascii=False, indent=2)
            self._build_reading_cache()
            safe_stderr_print(f"Сохранено {len(self.books_data)} книг")
        except Exception as e:
            safe_stderr_print(f"Ошибка сохранения: {e}")

    def _send_response(self, data, request_id=None):
        response = data
        if request_id is not None:
            response = {'_requestId': request_id, **data} if isinstance(data, dict) else {'_requestId': request_id, 'data': data}
        sys.stdout.write(json.dumps(response, ensure_ascii=False) + '\n')
        sys.stdout.flush()

    def _test_api_key(self):
        global USE_API_KEY
        try:
            test_url = "https://www.googleapis.com/books/v1/volumes"
            params = {'q': 'test', 'maxResults': 1}
            if API_KEY:
                params['key'] = API_KEY
                response = self.session.get(test_url, params=params, timeout=5)
                if response.status_code == 200:
                    USE_API_KEY = True
                    safe_stderr_print("✅ API ключ работает")
                else:
                    USE_API_KEY = False
            else:
                USE_API_KEY = False
        except:
            USE_API_KEY = False

    def _get_book_id_from_url(self, url):
        if not url:
            return None
        match = re.search(r'[?&]id=([a-zA-Z0-9_-]+)', url)
        if match:
            return match.group(1)
        match = re.search(r'/books\?id=([a-zA-Z0-9_-]+)', url)
        if match:
            return match.group(1)
        match = re.search(r'/volumes/([a-zA-Z0-9_-]+)', url)
        if match:
            return match.group(1)
        return None

    def _is_book_in_library(self, book_id, url):
        for book in self.books_data:
            if book.get('url') == url:
                return True
            existing_id = self._get_book_id_from_url(book.get('url', ''))
            if existing_id and book_id and existing_id == book_id:
                return True
        return False

    def get_all_books(self, request_id=None):
        self._send_response({'success': True, 'data': self.books_data}, request_id)

    def fuzzy_search(self, data, request_id=None):
        query = data.get('query', '').strip()
        safe_stderr_print(f"🔍 ПОИСК: '{query}'")
        if len(query) < 2:
            self._send_response({'success': False, 'error': 'Слишком короткий запрос', 'data': [], 'count': 0}, request_id)
            return

        url = "https://www.googleapis.com/books/v1/volumes"
        params = {
            'q': query,
            'maxResults': 40,
            'langRestrict': 'ru',
            'printType': 'books'
        }
        if USE_API_KEY and API_KEY:
            params['key'] = API_KEY

        try:
            response = self.session.get(url, params=params, timeout=15)
            if response.status_code != 200:
                self._send_response({'success': False, 'error': f'API error: {response.status_code}', 'data': [], 'count': 0}, request_id)
                return

            data = response.json()
            items = data.get('items', [])
            books_found = []
            for item in items:
                try:
                    volume_info = item.get('volumeInfo', {})
                    book_id = item.get('id', '')
                    book_url = f"https://books.google.com/books?id={book_id}" if book_id else ''
                    title = volume_info.get('title', 'Неизвестное название')
                    title = re.sub(r'\s+', ' ', title).strip()
                    authors = volume_info.get('authors', ['Автор не указан'])
                    author = ', '.join(authors) if authors else 'Автор не указан'
                    cover_url = volume_info.get('imageLinks', {}).get('thumbnail', '')
                    if cover_url:
                        cover_url = cover_url.replace('&zoom=1', '&zoom=3').replace('http://', 'https://')
                    description = volume_info.get('description', '')
                    if description:
                        description = re.sub(r'<[^>]+>', '', description)[:500] + ('...' if len(description) > 500 else '')
                    genre = ', '.join(volume_info.get('categories', ['Без жанра'])) if volume_info.get('categories') else 'Без жанра'
                    google_rating = volume_info.get('averageRating', 0)
                    is_added = self._is_book_in_library(book_id, book_url)
                    books_found.append({
                        'url': book_url,
                        'title': title,
                        'author': author,
                        'cover': cover_url,
                        'description': description,
                        'genre': genre,
                        'rating': google_rating,
                        'is_added': is_added
                    })
                except:
                    continue
            self._send_response({'success': True, 'query': query, 'count': len(books_found), 'data': books_found}, request_id)
        except Exception as e:
            self._send_response({'success': False, 'error': str(e), 'data': [], 'count': 0}, request_id)

    def add_book(self, data, request_id=None):
        url = data.get('url', '')
        if not url:
            self._send_response({'success': False, 'error': 'URL не указан'}, request_id)
            return

        try:
            existing = None
            for book in self.books_data:
                if book.get('url') == url:
                    existing = book
                    break
                existing_id = self._get_book_id_from_url(book.get('url', ''))
                new_id = self._get_book_id_from_url(url)
                if existing_id and new_id and existing_id == new_id:
                    existing = book
                    break

            if existing and not data.get('force_update'):
                self._send_response({'success': True, 'exists': True, 'book': existing}, request_id)
                return

            book_id = self._get_book_id_from_url(url)
            if not book_id:
                self._send_response({'success': False, 'error': 'Неверный формат URL'}, request_id)
                return

            api_url = f"https://www.googleapis.com/books/v1/volumes/{book_id}"
            params = {}
            if USE_API_KEY and API_KEY:
                params['key'] = API_KEY
            response = self.session.get(api_url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            volume_info = data.get('volumeInfo', {})

            title = volume_info.get('title', 'Неизвестное название')
            title = re.sub(r'\s+', ' ', title).strip()
            authors = volume_info.get('authors', ['Автор не указан'])
            author = ', '.join(authors) if authors else 'Автор не указан'
            genre = ', '.join(volume_info.get('categories', ['Без жанра'])) if volume_info.get('categories') else 'Без жанра'
            cover_url = volume_info.get('imageLinks', {}).get('thumbnail', '')
            if cover_url:
                cover_url = cover_url.replace('&zoom=1', '&zoom=3').replace('http://', 'https://')
            description = volume_info.get('description', '')
            if description:
                description = re.sub(r'<[^>]+>', '', description)
            google_rating = volume_info.get('averageRating', 0)

            cover_base64 = None
            if cover_url:
                try:
                    img_response = self.session.get(cover_url, timeout=15)
                    if img_response.status_code == 200:
                        image_base64 = base64.b64encode(img_response.content).decode('utf-8')
                        cover_base64 = f"data:image/jpeg;base64,{image_base64}"
                except:
                    pass

            new_id = len(self.books_data) + 1 if not existing else existing.get('id', len(self.books_data) + 1)
            now_full = datetime.now().isoformat()
            added_date = existing['added_date'] if existing and existing.get('added_date') else now_full
            notes = existing.get('notes', '') if existing else ''
            reading_sessions = existing.get('reading_sessions', []) if existing else []

            new_book = {
                'id': new_id,
                'url': url,
                'title': title,
                'author': author,
                'genre': genre,
                'rating': google_rating,
                'cover': cover_base64,
                'description': description,
                'status': 'want_to_read',
                'added_date': added_date,
                'notes': notes,
                'reading_sessions': reading_sessions
            }

            if existing:
                index = self.books_data.index(existing)
                new_book['id'] = existing['id']
                self.books_data[index] = new_book
            else:
                self.books_data.append(new_book)

            self._save_books_data()
            self._send_response({'success': True, 'book': new_book, 'exists': bool(existing), 'is_new': not existing}, request_id)
        except Exception as e:
            self._send_response({'success': False, 'error': str(e)}, request_id)

    def add_manual_book(self, data, request_id=None):
        try:
            title = data.get('title', '').strip()
            author = data.get('author', '').strip()
            if not title or not author:
                self._send_response({'success': False, 'error': 'Название и автор обязательны'}, request_id)
                return

            existing = None
            for book in self.books_data:
                if book.get('title', '').lower() == title.lower() and book.get('author', '').lower() == author.lower():
                    existing = book
                    break
            if existing:
                self._send_response({'success': True, 'exists': True, 'book': existing}, request_id)
                return

            cover_url = data.get('cover')
            cover_base64 = None
            if cover_url and cover_url.startswith('http'):
                try:
                    img_response = self.session.get(cover_url, timeout=15)
                    if img_response.status_code == 200:
                        image_base64 = base64.b64encode(img_response.content).decode('utf-8')
                        content_type = img_response.headers.get('content-type', 'image/jpeg')
                        if 'png' in content_type:
                            cover_base64 = f"data:image/png;base64,{image_base64}"
                        else:
                            cover_base64 = f"data:image/jpeg;base64,{image_base64}"
                except:
                    pass
            elif cover_url:
                cover_base64 = cover_url

            rating = data.get('rating', 0)
            try:
                rating = int(rating)
                rating = max(0, min(5, rating))
            except:
                rating = 0

            new_id = len(self.books_data) + 1
            now_full = datetime.now().isoformat()
            new_book = {
                'id': new_id,
                'url': None,
                'title': title,
                'author': author,
                'genre': data.get('genre', 'Без жанра').strip() or 'Без жанра',
                'rating': rating,
                'cover': cover_base64,
                'description': data.get('description', '').strip() or '',
                'status': data.get('status', 'want_to_read'),
                'added_date': now_full,
                'notes': '',
                'reading_sessions': []
            }
            self.books_data.append(new_book)
            self._save_books_data()
            self._send_response({'success': True, 'book': new_book, 'exists': False, 'is_new': True}, request_id)
        except Exception as e:
            self._send_response({'success': False, 'error': str(e)}, request_id)

    def update_book_notes(self, data, request_id=None):
        book_id = data.get('book_id')
        notes = data.get('notes', '')
        for book in self.books_data:
            if book.get('id') == book_id:
                book['notes'] = notes
                self._save_books_data()
                self._send_response({'success': True}, request_id)
                return
        self._send_response({'success': False, 'error': 'Книга не найдена'}, request_id)

    def delete_book(self, data, request_id=None):
        book_id = data.get('book_id')
        for i, book in enumerate(self.books_data):
            if book.get('id') == book_id:
                del self.books_data[i]
                self._save_books_data()
                self._send_response({'success': True}, request_id)
                return
        self._send_response({'success': False, 'error': 'Книга не найдена'}, request_id)

    def add_reading_session(self, data, request_id=None):
        book_id = data.get('book_id')
        session_time = data.get('timestamp', datetime.now().isoformat())
        for book in self.books_data:
            if book.get('id') == book_id:
                if 'reading_sessions' not in book:
                    book['reading_sessions'] = []
                book['reading_sessions'].append(session_time)
                if book.get('status') != 'read':
                    book['status'] = 'reading'
                self._save_books_data()
                self._send_response({'success': True, 'sessions': book['reading_sessions']}, request_id)
                return
        self._send_response({'success': False, 'error': 'Книга не найдена'}, request_id)

    def get_reading_sessions(self, data, request_id=None):
        book_id = data.get('book_id')
        for book in self.books_data:
            if book.get('id') == book_id:
                sessions = book.get('reading_sessions', [])
                self._send_response({'success': True, 'sessions': sessions}, request_id)
                return
        self._send_response({'success': False, 'error': 'Книга не найдена'}, request_id)

    def update_book_status(self, data, request_id=None):
        book_id = data.get('book_id')
        status = data.get('status')
        for book in self.books_data:
            if book.get('id') == book_id:
                book['status'] = status
                self._save_books_data()
                self._send_response({'success': True}, request_id)
                return
        self._send_response({'success': False, 'error': 'Книга не найдена'}, request_id)

    def update_book_rating(self, data, request_id=None):
        book_id = data.get('book_id')
        rating = data.get('rating')
        for book in self.books_data:
            if book.get('id') == book_id:
                book['rating'] = rating
                self._save_books_data()
                self._send_response({'success': True}, request_id)
                return
        self._send_response({'success': False, 'error': 'Книга не найдена'}, request_id)

    def search_online(self, query, request_id=None):
        self.fuzzy_search({'query': query}, request_id)

    def get_calendar(self, data, request_id=None):
        year = data.get('year')
        month = data.get('month')
        if not year or not month:
            now = datetime.now()
            year = now.year
            month = now.month
        html = calendar_module.generate_calendar_html(year, month, self.reading_cache)
        self._send_response({'success': True, 'html': html}, request_id)


def main():
    parser = BookParser()
    safe_stderr_print("Python готов к приёму команд")
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
            request = json.loads(line)
            command = request.get('command')
            data = request.get('data', {})
            req_id = request.get('_requestId')
            if command == 'get_books':
                parser.get_all_books(req_id)
            elif command == 'search_online':
                parser.search_online(data.get('query', ''), req_id)
            elif command == 'fuzzy_search':
                parser.fuzzy_search(data, req_id)
            elif command == 'add_book':
                parser.add_book(data, req_id)
            elif command == 'add_manual_book':
                parser.add_manual_book(data, req_id)
            elif command == 'update_status':
                parser.update_book_status(data, req_id)
            elif command == 'update_rating':
                parser.update_book_rating(data, req_id)
            elif command == 'update_book_notes':
                parser.update_book_notes(data, req_id)
            elif command == 'delete_book':
                parser.delete_book(data, req_id)
            elif command == 'add_reading_session':
                parser.add_reading_session(data, req_id)
            elif command == 'get_reading_sessions':
                parser.get_reading_sessions(data, req_id)
            elif command == 'get_calendar':
                parser.get_calendar(data, req_id)
            else:
                parser._send_response({'success': False, 'error': f'Неизвестная команда: {command}'}, req_id)
        except Exception as e:
            safe_stderr_print(f"Ошибка в главном цикле: {e}")


if __name__ == '__main__':
    main()
    input("Нажмите Enter для выхода...")