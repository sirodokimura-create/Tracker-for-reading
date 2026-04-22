const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('readingAPI', {
    // Загрузить книги из JSON (прямая загрузка с рабочего стола)
    loadBooksFromJson: () => ipcRenderer.invoke('load-books-from-json'),
    
    // Сохранить книги в JSON (прямое сохранение на рабочий стол)
    saveBooksToJson: (books) => ipcRenderer.invoke('save-books-to-json', books),
    
    // Получить все книги через Python
    getBooks: () => ipcRenderer.invoke('python-request', {
        command: 'get_books'
    }),
    
    // Добавить книгу через парсинг URL
    addBook: (bookData) => ipcRenderer.invoke('python-request', {
        command: 'add_book',
        data: bookData
    }),
    
    // Обновить статус книги
    updateStatus: (bookId, status) => ipcRenderer.invoke('python-request', {
        command: 'update_status',
        data: { book_id: bookId, status }
    }),
    
    // Обновить рейтинг книги
    updateRating: (bookId, rating) => ipcRenderer.invoke('python-request', {
        command: 'update_rating',
        data: { book_id: bookId, rating }
    }),
    
    // Поиск книг на сайте Литрес (заменён на Google Books)
    searchBooks: (query) => ipcRenderer.invoke('python-request', {
        command: 'search_online',
        data: { query }
    }),
    
    // Универсальный метод для любых запросов к Python
    pythonRequest: (request) => ipcRenderer.invoke('python-request', request),
    
    // ---------- НОВЫЕ МЕТОДЫ ----------
    // Сохранить заметки
    updateBookNotes: (bookId, notes) => ipcRenderer.invoke('python-request', {
        command: 'update_book_notes',
        data: { book_id: bookId, notes }
    }),
    
    // Удалить книгу
    deleteBook: (bookId) => ipcRenderer.invoke('python-request', {
        command: 'delete_book',
        data: { book_id: bookId }
    }),
    
    // Добавить сессию чтения
    addReadingSession: (bookId, timestamp) => ipcRenderer.invoke('python-request', {
        command: 'add_reading_session',
        data: { book_id: bookId, timestamp }
    }),
    
    // Получить сессии чтения
    getReadingSessions: (bookId) => ipcRenderer.invoke('python-request', {
        command: 'get_reading_sessions',
        data: { book_id: bookId }
    })
});