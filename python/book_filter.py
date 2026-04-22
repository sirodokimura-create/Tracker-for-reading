import json
from typing import List, Dict, Optional
from enum import Enum
from datetime import datetime

class BookStatus(Enum):
    WANT_TO_READ = "want_to_read" 
    READING = "reading"             
    READ = "read"                   
    ABANDONED = "abandoned"         
    
    @classmethod
    def get_russian_name(cls, status: str) -> str:
        
        status_map = {
            cls.WANT_TO_READ.value: "Хочу прочитать",
            cls.READING.value: "Читаю",
            cls.READ.value: "Прочитано",
            cls.ABANDONED.value: "Брошено"
        }
        return status_map.get(status, "Неизвестно")
    
    @classmethod
    def get_all_statuses(cls) -> List[str]:
        """Возвращает список всех статусов"""
        return [status.value for status in cls]


class BookFilter:
    
    
    def __init__(self, books_data: List[Dict]):
        
        self.books_data = books_data
        self._validate_books()
    
    def _validate_books(self):
        
        for book in self.books_data:
            if 'status' not in book:
                book['status'] = BookStatus.WANT_TO_READ.value
            
            
            if book['status'] not in BookStatus.get_all_statuses():
                book['status'] = BookStatus.WANT_TO_READ.value
    
    def filter_by_status(self, status: str) -> List[Dict]:
        
        if status == 'all':
            return self.books_data.copy()
        
        return [book for book in self.books_data if book.get('status') == status]
    
    def get_books_by_status(self) -> Dict[str, List[Dict]]:
        
        grouped = {
            BookStatus.WANT_TO_READ.value: [],
            BookStatus.READING.value: [],
            BookStatus.READ.value: [],
            BookStatus.ABANDONED.value: []
        }
        
        for book in self.books_data:
            status = book.get('status', BookStatus.WANT_TO_READ.value)
            if status in grouped:
                grouped[status].append(book)
        
        return grouped
    
    def get_status_statistics(self) -> Dict[str, int]:
        
        grouped = self.get_books_by_status()
        return {
            status: len(books) 
            for status, books in grouped.items()
        }
    
    def filter_by_multiple_criteria(self, 
                                   status: Optional[str] = None,
                                   genre: Optional[str] = None,
                                   min_rating: Optional[float] = None,
                                   author: Optional[str] = None,
                                   year_from: Optional[int] = None,
                                   year_to: Optional[int] = None,
                                   search_query: Optional[str] = None) -> List[Dict]:
       
        result = self.books_data.copy()
        
        
        if status and status != 'all':
            result = [book for book in result if book.get('status') == status]
        
        
        if genre:
            genre_lower = genre.lower()
            result = [
                book for book in result 
                if genre_lower in book.get('genre', '').lower()
            ]
        
        
        if min_rating is not None:
            result = [
                book for book in result 
                if book.get('rating', 0) >= min_rating
            ]
        
        
        if author:
            author_lower = author.lower()
            result = [
                book for book in result 
                if author_lower in book.get('author', '').lower()
            ]
        
        
        if year_from or year_to:
            def check_year(book):
                year = book.get('year')
                if not year:
                    return False
                if year_from and year < year_from:
                    return False
                if year_to and year > year_to:
                    return False
                return True
            
            result = [book for book in result if check_year(book)]
        
        
        if search_query:
            query_lower = search_query.lower()
            result = [
                book for book in result
                if query_lower in book.get('title', '').lower() or
                   query_lower in book.get('author', '').lower()
            ]
        
        return result
    
    def sort_books(self, 
                   books: List[Dict], 
                   sort_by: str = 'date_added',
                   reverse: bool = True) -> List[Dict]:
       
        if sort_by == 'date_added':
            key_func = lambda x: x.get('added_date', '')
        elif sort_by == 'title':
            key_func = lambda x: x.get('title', '').lower()
        elif sort_by == 'author':
            key_func = lambda x: x.get('author', '').lower()
        elif sort_by == 'rating':
            key_func = lambda x: x.get('rating', 0)
        else:
            return books.copy()
        
        return sorted(books, key=key_func, reverse=reverse)
    
    def get_reading_progress(self) -> Dict:
        
        stats = self.get_status_statistics()
        total = len(self.books_data)
        
        if total == 0:
            return {
                'total': 0,
                'completed_percent': 0,
                'reading_percent': 0,
                'planned_percent': 0,
                'abandoned_percent': 0
            }
        
        return {
            'total': total,
            'completed_percent': round(stats.get(BookStatus.READ.value, 0) / total * 100, 1),
            'reading_percent': round(stats.get(BookStatus.READING.value, 0) / total * 100, 1),
            'planned_percent': round(stats.get(BookStatus.WANT_TO_READ.value, 0) / total * 100, 1),
            'abandoned_percent': round(stats.get(BookStatus.ABANDONED.value, 0) / total * 100, 1)
        }


class BookLibraryManager:
    
    
    def __init__(self, data_file: str):
        
        self.data_file = data_file
        self.books = self._load_books()
        self.filter = BookFilter(self.books)
    
    def _load_books(self) -> List[Dict]:
        
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                # Приводим к единому формату
                if isinstance(data, list):
                    for i, book in enumerate(data):
                        if 'id' not in book:
                            book['id'] = i + 1
                        if 'status' not in book:
                            book['status'] = BookStatus.WANT_TO_READ.value
                        if 'added_date' not in book:
                            book['added_date'] = datetime.now().isoformat()[:10]
                    return data
                return []
        except (FileNotFoundError, json.JSONDecodeError):
            return []
    
    def _save_books(self):
        
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.books, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения: {e}")
    
    def get_books_by_status(self, status: str = 'all') -> List[Dict]:
        
        return self.filter.filter_by_status(status)
    
    def update_book_status(self, book_id: int, new_status: str) -> bool:
        
        for book in self.books:
            if book.get('id') == book_id:
                book['status'] = new_status
                self._save_books()
                
                self.filter = BookFilter(self.books)
                return True
        return False
    
    def get_status_counts(self) -> Dict[str, int]:
        
        stats = self.filter.get_status_statistics()
        
        
        stats['all'] = len(self.books)
        
        return stats
    
    def get_library_page_data(self, status: str = 'all', 
                             sort_by: str = 'date_added',
                             page: int = 1, 
                             per_page: int = 20) -> Dict:
        
        filtered_books = self.get_books_by_status(status)
        
        
        sorted_books = self.filter.sort_books(filtered_books, sort_by)
        
        
        total = len(sorted_books)
        start = (page - 1) * per_page
        end = start + per_page
        paginated_books = sorted_books[start:end]
        
        return {
            'success': True,
            'status': status,
            'sort_by': sort_by,
            'page': page,
            'per_page': per_page,
            'total': total,
            'total_pages': (total + per_page - 1) // per_page,
            'books': paginated_books,
            'status_counts': self.get_status_counts(),
            'reading_progress': self.filter.get_reading_progress()
        }



def test_book_filter():
    
    test_books = [
        {
            'id': 1,
            'title': 'Война и мир',
            'author': 'Лев Толстой',
            'status': 'read',
            'rating': 4.8,
            'genre': 'Классика',
            'added_date': '2024-01-15'
        },
        {
            'id': 2,
            'title': 'Преступление и наказание',
            'author': 'Фёдор Достоевский',
            'status': 'reading',
            'rating': 4.9,
            'genre': 'Классика',
            'added_date': '2024-02-01'
        },
        {
            'id': 3,
            'title': 'Мастер и Маргарита',
            'author': 'Михаил Булгаков',
            'status': 'want_to_read',
            'rating': 0,
            'genre': 'Классика',
            'added_date': '2024-02-10'
        },
        {
            'id': 4,
            'title': '1984',
            'author': 'Джордж Оруэлл',
            'status': 'read',
            'rating': 4.7,
            'genre': 'Антиутопия',
            'added_date': '2024-01-20'
        },
        {
            'id': 5,
            'title': 'Гарри Поттер',
            'author': 'Джоан Роулинг',
            'status': 'reading',
            'rating': 4.9,
            'genre': 'Фэнтези',
            'added_date': '2024-02-05'
        }
    ]
    
    
    book_filter = BookFilter(test_books)
    
    print("=" * 60)
    print("ТЕСТИРОВАНИЕ ФИЛЬТРАЦИИ КНИГ ПО СТАТУСУ")
    print("=" * 60)
    
    
    print("\n1. Все книги:")
    all_books = book_filter.filter_by_status('all')
    for book in all_books:
        print(f"   - {book['title']} ({BookStatus.get_russian_name(book['status'])})")
    
    
    print("\n2. Книги со статусом 'Прочитано':")
    read_books = book_filter.filter_by_status(BookStatus.READ.value)
    for book in read_books:
        print(f"   - {book['title']} (Рейтинг: {book['rating']})")
    
    
    print("\n3. Книги со статусом 'Читаю':")
    reading_books = book_filter.filter_by_status(BookStatus.READING.value)
    for book in reading_books:
        print(f"   - {book['title']}")
    
    
    print("\n4. Статистика по статусам:")
    stats = book_filter.get_status_statistics()
    for status, count in stats.items():
        print(f"   - {BookStatus.get_russian_name(status)}: {count} книг")
    
    
    print("\n5. Прогресс чтения:")
    progress = book_filter.get_reading_progress()
    print(f"   - Всего книг: {progress['total']}")
    print(f"   - Прочитано: {progress['completed_percent']}%")
    print(f"   - В процессе: {progress['reading_percent']}%")
    print(f"   - В планах: {progress['planned_percent']}%")
    
    
    print("\n6. Группировка книг по статусам:")
    grouped = book_filter.get_books_by_status()
    for status, books in grouped.items():
        if books:
            print(f"\n   {BookStatus.get_russian_name(status)} ({len(books)}):")
            for book in books:
                print(f"      • {book['title']}")
    
    
    print("\n7. Сложная фильтрация (Прочитано + Рейтинг > 4.7):")
    filtered = book_filter.filter_by_multiple_criteria(
        status=BookStatus.READ.value,
        min_rating=4.7
    )
    for book in filtered:
        print(f"   - {book['title']} (Рейтинг: {book['rating']})")
    
    return book_filter


def test_library_manager():
    
    
    print("\n" + "=" * 60)
    print("ТЕСТИРОВАНИЕ МЕНЕДЖЕРА БИБЛИОТЕКИ")
    print("=" * 60)
    
    
    import tempfile
    import os
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        test_data = [
            {
                'id': 1,
                'title': 'Тестовая книга 1',
                'status': 'read',
                'added_date': '2024-01-01'
            },
            {
                'id': 2,
                'title': 'Тестовая книга 2',
                'status': 'reading',
                'added_date': '2024-01-02'
            }
        ]
        json.dump(test_data, f)
        temp_file = f.name
    
    
    manager = BookLibraryManager(temp_file)
    
    
    page_data = manager.get_library_page_data(status='all', page=1, per_page=10)
    
    print(f"\nСтатус: {page_data['status']}")
    print(f"Всего книг: {page_data['total']}")
    print(f"Всего страниц: {page_data['total_pages']}")
    print("\nКниги на странице:")
    for book in page_data['books']:
        print(f"   - {book['title']} ({BookStatus.get_russian_name(book['status'])})")
    
    print("\nСтатистика по статусам:")
    for status, count in page_data['status_counts'].items():
        if status != 'all':
            print(f"   - {BookStatus.get_russian_name(status)}: {count}")
        else:
            print(f"   - Всего: {count}")
    
    
    os.unlink(temp_file)
    
    return manager


if __name__ == "__main__":
    
    test_book_filter()
    test_library_manager()
    
    print("\n" + "=" * 60)
    print("ГОТОВО! Алгоритм фильтрации работает корректно.")
    print("=" * 60)