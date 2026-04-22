import re
import json
import requests
from bs4 import BeautifulSoup
from collections import defaultdict
from typing import List, Dict, Tuple, Set
import time

class FuzzySearchEngine:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        self.base_url = "https://www.litres.ru"
        
    def extract_trigrams(self, word: str) -> Set[str]:
        
        word = word.lower().strip()
        if len(word) < 3:
            return {word}
        
        trigrams = set()
        for i in range(len(word) - 2):
            trigrams.add(word[i:i+3])
        return trigrams
    
    def calculate_trigram_similarity(self, query: str, text: str) -> float:
        
        if not query or not text:
            return 0.0
        
        
        query_words = re.findall(r'[а-яёa-z]+', query.lower())
        text_words = re.findall(r'[а-яёa-z]+', text.lower())
        
        if not query_words or not text_words:
            return 0.0
        
        
        query_trigrams = set()
        for word in query_words:
            query_trigrams.update(self.extract_trigrams(word))
        
        
        text_trigrams = set()
        for word in text_words:
            text_trigrams.update(self.extract_trigrams(word))
        
        if not query_trigrams:
            return 0.0
        
        
        intersection = query_trigrams.intersection(text_trigrams)
        
        
        union = query_trigrams.union(text_trigrams)
        if not union:
            return 0.0
        
        jaccard = len(intersection) / len(union)
        
        
        word_bonus = 0
        for q_word in query_words:
            for t_word in text_words:
                if q_word == t_word or t_word.startswith(q_word) or q_word.startswith(t_word):
                    word_bonus += 0.1
        
        return min(1.0, jaccard + word_bonus)
    
    def search_books(self, query: str, threshold: float = 0.3) -> List[Dict]:
        
        print(f"Поиск книг по запросу: {query}")
        
        
        search_url = f"{self.base_url}/search/"
        params = {
            'q': query,
            'page': 1
        }
        
        try:
            response = self.session.get(search_url, params=params, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            
            books = self._parse_search_results(soup, query, threshold)
            
            
            books.sort(key=lambda x: x['relevance'], reverse=True)
            
            return books
            
        except Exception as e:
            print(f"Ошибка при поиске: {e}")
            return []
    
    def _parse_search_results(self, soup: BeautifulSoup, query: str, threshold: float) -> List[Dict]:
        
        books = []
        
        
        book_cards = soup.find_all('div', {'class': re.compile(r'book-card|art-card|biblio-book')})
        
        if not book_cards:
            
            book_cards = soup.find_all('article', {'class': re.compile(r'book|art')})
        
        if not book_cards:
            
            books = self._parse_json_ld(soup, query, threshold)
            if books:
                return books
        
        for card in book_cards:
            book_data = self._extract_book_from_card(card)
            if book_data:
                
                title_similarity = self.calculate_trigram_similarity(query, book_data['title'])
                author_similarity = self.calculate_trigram_similarity(query, book_data['author'])
                
                
                relevance = max(title_similarity, author_similarity * 0.7)
                
                if relevance >= threshold:
                    book_data['relevance'] = relevance
                    books.append(book_data)
        
        return books
    
    def _parse_json_ld(self, soup: BeautifulSoup, query: str, threshold: float) -> List[Dict]:
       
        books = []
        json_scripts = soup.find_all('script', type='application/ld+json')
        
        for script in json_scripts:
            try:
                data = json.loads(script.string)
                
                
                items = []
                if isinstance(data, dict):
                    if '@graph' in data:
                        items = data['@graph']
                    elif 'itemListElement' in data:
                        items = data['itemListElement']
                    else:
                        items = [data]
                elif isinstance(data, list):
                    items = data
                
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    
                    
                    item_type = item.get('@type', '')
                    if 'Book' in item_type or 'Product' in item_type:
                        title = item.get('name', '')
                        author = ''
                        
                        
                        author_data = item.get('author')
                        if isinstance(author_data, dict):
                            author = author_data.get('name', '')
                        elif isinstance(author_data, str):
                            author = author_data
                        elif isinstance(author_data, list) and author_data:
                            if isinstance(author_data[0], dict):
                                author = author_data[0].get('name', '')
                            else:
                                author = str(author_data[0])
                        
                        url = item.get('url', '')
                        image = item.get('image', '')
                        if isinstance(image, dict):
                            image = image.get('url', '')
                        elif isinstance(image, list) and image:
                            image = image[0] if isinstance(image[0], str) else image[0].get('url', '')
                        
                        if title:
                            
                            title_similarity = self.calculate_trigram_similarity(query, title)
                            author_similarity = self.calculate_trigram_similarity(query, author)
                            relevance = max(title_similarity, author_similarity * 0.7)
                            
                            if relevance >= threshold:
                                books.append({
                                    'title': title,
                                    'author': author,
                                    'url': url if url.startswith('http') else self.base_url + url,
                                    'cover': image,
                                    'genre': item.get('genre', ''),
                                    'relevance': relevance
                                })
            except json.JSONDecodeError:
                continue
        
        return books
    
    def _extract_book_from_card(self, card) -> Dict:
        
        try:
            
            title_elem = card.find('a', {'class': re.compile(r'title|name|book-title')})
            if not title_elem:
                title_elem = card.find('h3') or card.find('h2') or card.find('div', {'class': re.compile(r'title')})
            
            title = title_elem.text.strip() if title_elem else ''
            
            
            url = ''
            if title_elem and title_elem.get('href'):
                url = title_elem['href']
            else:
                link_elem = card.find('a', href=True)
                if link_elem:
                    url = link_elem['href']
            
            if url and not url.startswith('http'):
                url = self.base_url + url
            
            
            author_elem = card.find('a', {'class': re.compile(r'author')})
            if not author_elem:
                author_elem = card.find('div', {'class': re.compile(r'author')})
            if not author_elem:
                author_elem = card.find('span', {'class': re.compile(r'author')})
            
            author = author_elem.text.strip() if author_elem else ''
            
            
            cover_elem = card.find('img', {'class': re.compile(r'cover|image')})
            cover = ''
            if cover_elem and cover_elem.get('src'):
                cover = cover_elem['src']
                if cover.startswith('//'):
                    cover = 'https:' + cover
            
            
            genre_elem = card.find('div', {'class': re.compile(r'genre')})
            genre = genre_elem.text.strip() if genre_elem else ''
            
            if title:
                return {
                    'title': title,
                    'author': author,
                    'url': url,
                    'cover': cover,
                    'genre': genre
                }
            
        except Exception as e:
            print(f"Ошибка при парсинге карточки: {e}")
        
        return None
    
    def search_local(self, query: str, books_data: List[Dict], threshold: float = 0.3) -> List[Dict]:
        
        results = []
        
        for book in books_data:
            title = book.get('title', '')
            author = book.get('author', '')
            
            title_similarity = self.calculate_trigram_similarity(query, title)
            author_similarity = self.calculate_trigram_similarity(query, author)
            
            relevance = max(title_similarity, author_similarity * 0.7)
            
            if relevance >= threshold:
                book_copy = book.copy()
                book_copy['relevance'] = relevance
                results.append(book_copy)
        
        results.sort(key=lambda x: x['relevance'], reverse=True)
        return results
    
    def suggest_corrections(self, query: str, words_dict: Set[str]) -> List[str]:
       
        query_trigrams = self.extract_trigrams(query)
        suggestions = []
        
        for word in words_dict:
            word_trigrams = self.extract_trigrams(word)
            intersection = query_trigrams.intersection(word_trigrams)
            union = query_trigrams.union(word_trigrams)
            
            if union:
                similarity = len(intersection) / len(union)
                if similarity > 0.4 and similarity < 1.0:
                    suggestions.append((word, similarity))
        
        suggestions.sort(key=lambda x: x[1], reverse=True)
        return [s[0] for s in suggestions[:5]]


class BookSearchAPI:
    
    def __init__(self):
        self.engine = FuzzySearchEngine()
        self.local_books = []
        
    def load_local_books(self, filepath: str):
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                self.local_books = json.load(f)
        except Exception as e:
            print(f"Ошибка загрузки локальных книг: {e}")
            self.local_books = []
    
    def search_online(self, query: str) -> Dict:
       
        results = self.engine.search_books(query, threshold=0.25)
        
        # Проверяем, какие книги уже есть в локальной библиотеке
        local_urls = {book.get('url', '') for book in self.local_books}
        for result in results:
            result['is_added'] = result.get('url', '') in local_urls
        
        return {
            'success': True,
            'query': query,
            'count': len(results),
            'data': results
        }
    
    def search_local(self, query: str) -> Dict:
        
        results = self.engine.search_local(query, self.local_books, threshold=0.25)
        
        return {
            'success': True,
            'query': query,
            'count': len(results),
            'data': results
        }
    
    def get_suggestions(self, query: str) -> Dict:
        
        all_words = set()
        for book in self.local_books:
            title_words = re.findall(r'[а-яёa-z]+', book.get('title', '').lower())
            author_words = re.findall(r'[а-яёa-z]+', book.get('author', '').lower())
            all_words.update(title_words)
            all_words.update(author_words)
        
        
        query_words = re.findall(r'[а-яёa-z]+', query.lower())
        suggestions = {}
        
        for word in query_words:
            if len(word) >= 3:
                word_suggestions = self.engine.suggest_corrections(word, all_words)
                if word_suggestions:
                    suggestions[word] = word_suggestions
        
        return {
            'success': True,
            'query': query,
            'suggestions': suggestions
        }


def main():
   
    api = BookSearchAPI()
    
    print("=" * 60)
    print("Fuzzy Search Engine - Поиск с учетом ошибок")
    print("=" * 60)
    print("\nАлгоритм использует триграммы (трехбуквия) для поиска")
    print("Это позволяет находить книги даже при опечатках в запросе\n")
    
    while True:
        query = input("\nВведите название книги или автора (или 'exit' для выхода): ").strip()
        
        if query.lower() == 'exit':
            break
        
        if not query:
            continue
        
        print(f"\nПоиск: '{query}'")
        print("-" * 40)
        
        
        print("\nТриграммы запроса:")
        trigrams = api.engine.extract_trigrams(query)
        print(f"  {', '.join(sorted(trigrams))}\n")
        
    
        result = api.search_online(query)
        
        if result['success'] and result['data']:
            print(f"Найдено книг: {result['count']}")
            print("\nРезультаты (отсортированы по релевантности):")
            print("-" * 40)
            
            for i, book in enumerate(result['data'][:10], 1):
                relevance_percent = int(book['relevance'] * 100)
                print(f"\n{i}. {book['title']}")
                print(f"   Автор: {book['author']}")
                print(f"   Релевантность: {relevance_percent}%")
                print(f"   URL: {book['url']}")
        else:
            print("Книги не найдены")
        
        
        if len(query) < 10:
            suggestions = api.get_suggestions(query)
            if suggestions['suggestions']:
                print("\n💡 Возможно, вы имели в виду:")
                for wrong, correct in suggestions['suggestions'].items():
                    print(f"   '{wrong}' → {', '.join(correct[:3])}")


if __name__ == "__main__":
    main()