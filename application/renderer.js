let currentPage = 'home';          
let currentFilter = 'all';         
let currentStatusFilter = 'all';   
let books = [];                    
let currentBookId = null;          


document.addEventListener('DOMContentLoaded', async () => {
    await loadBooks();           
    setupEventListeners();       
    updateStats();               
});




async function loadBooks() {
    try {
        const result = await window.readingAPI.getBooks();
        let booksData = result?.data !== undefined ? result.data : result;
        
        if (booksData && Array.isArray(booksData)) {
            books = booksData;
            books.forEach(book => console.log(`Книга: ${book.title}, дата: ${book.added_date}`));
        } else {
            books = [];
        }
        
        updateStats();
        showRecentBooks();
        applyFilters();
        
        
        if (books.length === 0) {
            const emptyMsg = '<p class="no-books">📚 Нет добавленных книг. Нажмите "Добавить книгу", чтобы начать.</p>';
            document.getElementById('recent-books').innerHTML = emptyMsg;
            document.getElementById('library-books').innerHTML = emptyMsg;
        }
    } catch (error) {
        console.error(error);
        books = [];
        showNotification('Ошибка подключения к Python', 'error');
    }
}


function showRecentBooks() {
    const booksArray = Array.isArray(books) ? books : [];
    const sorted = [...booksArray].sort((a, b) => 
        (b.added_date || '1970-01-01').localeCompare(a.added_date || '1970-01-01')
    );
    const recentBooks = sorted.slice(0, 3);
    
    if (!recentBooks.length) {
        document.getElementById('recent-books').innerHTML = 
            '<p class="no-books">📚 Пока нет книг. Добавьте первую книгу!</p>';
    } else {
        renderBooks(recentBooks, 'recent-books');
    }
}



/**

 * @param {string} message - текст уведомления
 * @param {string} type 
 */
function showNotification(message, type = 'error') {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    
    const iconClass = type === 'error' ? 'fa-exclamation-circle' 
                    : type === 'success' ? 'fa-check-circle' 
                    : 'fa-info-circle';
    
    notification.innerHTML = `
        <i class="fas ${iconClass}"></i>
        <span>${message}</span>
    `;
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.classList.add('show');
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }, 10);
}




function displayFilteredBooks() {
    let filteredBooks = Array.isArray(books) ? books : [];
    
    if (currentStatusFilter !== 'all') {
        filteredBooks = filteredBooks.filter(b => b.status === currentStatusFilter);
    }
    
    renderBooks(filteredBooks, 'library-books');
}


function applyFilters() {
    displayFilteredBooks();
}

/**

 * @param {Array} booksArray - массив книг
 * @param {string} containerId - ID элемента-контейнера
 */
function renderBooks(booksArray, containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    if (!booksArray || !booksArray.length) {
        container.innerHTML = '<p class="no-books">📚 Книг не найдено</p>';
        return;
    }
    
    container.innerHTML = booksArray.map(book => createBookCard(book)).join('');
    
    // Добавляем обработчики клика на карточки
    container.querySelectorAll('.book-card').forEach(card => {
        card.addEventListener('click', () => {
            const bookId = parseInt(card.dataset.bookId);
            showBookDetails(bookId);
        });
    });
}

/**
 * @param {Object} book - объект книги
 * @returns {string} HTML-разметка карточки
 */
function createBookCard(book) {
    const statusLabels = {
        reading: 'Читаю',
        read: 'Прочитано',
        want_to_read: 'Хочу прочитать',
        abandoned: 'Брошено'
    };
    
    const shortTitle = book.title?.length > 35 
        ? book.title.substring(0, 32) + '...' 
        : book.title || 'Без названия';
        
    const shortAuthor = book.author?.length > 25 
        ? book.author.substring(0, 22) + '...' 
        : book.author || 'Неизвестный автор';
    
    const coverHtml = book.cover 
        ? `<img src="${book.cover}" alt="${book.title}" onerror="this.parentElement.innerHTML='<div class=\'no-cover\'><i class=\'fas fa-book\'></i></div>'">` 
        : `<div class="no-cover"><i class="fas fa-book"></i></div>`;
    
    return `
        <div class="book-card" data-book-id="${book.id}">
            <div class="book-cover">${coverHtml}</div>
            <div class="book-info">
                <h3 title="${book.title || 'Без названия'}">${shortTitle}</h3>
                <p class="book-author" title="${book.author || 'Неизвестный автор'}">${shortAuthor}</p>
                <span class="book-status status-${book.status}">${statusLabels[book.status] || 'Хочу прочитать'}</span>
            </div>
        </div>
    `;
}



/**
 * @param {number} bookId - ID книги
 */
function showBookDetails(bookId) {
    const book = books.find(b => b.id === bookId);
    if (!book) return;
    
    currentBookId = bookId;
    

    const coverHtml = book.cover 
        ? `<img src="${book.cover}" alt="${book.title}" onerror="this.parentElement.innerHTML='<i class=\'fas fa-book\'></i>'">` 
        : `<i class="fas fa-book"></i>`;
    
    const sessions = book.reading_sessions || [];
    const sessionsHtml = sessions.length === 0 
        ? '<p>Нет сессий чтения</p>' 
        : `<ul class="reading-sessions-list">${sessions.map(s => `<li>${new Date(s).toLocaleString()}</li>`).join('')}</ul>`;
    

    const starsHtml = [1, 2, 3, 4, 5].map(star => {
        const filled = star <= (book.rating || 0) ? '' : '-o';
        return `<i class="fas fa-star${filled}" style="cursor:pointer" onclick="event.stopPropagation(); setRating(${book.id}, ${star})"></i>`;
    }).join('');
    
    const modalContent = document.getElementById('book-detail-content');
    modalContent.innerHTML = `
        <div class="book-detail-cover">${coverHtml}</div>
        <div class="book-detail-info">
            <h2>${book.title || 'Без названия'}</h2>
            <p class="book-detail-author">${book.author || 'Неизвестный автор'}</p>
            
            <div class="book-detail-meta">
                <div class="book-detail-meta-item">
                    <i class="fas fa-tag"></i>
                    <span>${book.genre || 'Без жанра'}</span>
                </div>
                <div class="book-detail-meta-item">
                    <i class="fas fa-star"></i>
                    <div class="rating">${starsHtml}</div>
                </div>
            </div>
            
            <p class="book-detail-description">${book.description || 'Описание отсутствует'}</p>
            
            <div class="book-notes-section">
                <h3><i class="fas fa-pen-alt"></i> Мои заметки</h3>
                <textarea id="book-notes" rows="4" placeholder="Добавьте заметки о книге...">${book.notes || ''}</textarea>
                <button id="save-notes-btn" class="btn-secondary">Сохранить заметки</button>
            </div>
            
            <div class="reading-history-section">
                <h3><i class="fas fa-history"></i> История чтения</h3>
                <div class="reading-sessions-container">${sessionsHtml}</div>
                <button id="add-reading-session-btn" class="btn-primary">📖 Читаю сейчас</button>
            </div>
            
            <div class="book-detail-actions">
                <select class="status-select" id="book-status">
                    <option value="want_to_read" ${book.status === 'want_to_read' ? 'selected' : ''}>Хочу прочитать</option>
                    <option value="reading" ${book.status === 'reading' ? 'selected' : ''}>Читаю</option>
                    <option value="read" ${book.status === 'read' ? 'selected' : ''}>Прочитано</option>
                    <option value="abandoned" ${book.status === 'abandoned' ? 'selected' : ''}>Брошено</option>
                </select>
                <button id="delete-book-btn" class="btn-danger">🗑 Удалить книгу</button>
            </div>
        </div>
    `;
    
    
    document.getElementById('save-notes-btn').addEventListener('click', () => {
        saveNotes(book.id, document.getElementById('book-notes').value);
    });
    
    document.getElementById('add-reading-session-btn').addEventListener('click', () => {
        addReadingSession(book.id);
    });
    
    document.getElementById('delete-book-btn').addEventListener('click', () => {
        deleteBookFromLibrary(book.id);
    });
    
    document.getElementById('book-status').addEventListener('change', (e) => {
        updateBookStatus(book.id, e.target.value);
    });
    
    document.getElementById('book-modal').classList.add('active');
}


function closeBookModal() {
    document.getElementById('book-modal').classList.remove('active');
}


async function saveNotes(bookId, notes) {
    try {
        const result = await window.readingAPI.updateBookNotes(bookId, notes);
        if (result && result.success) {
            showNotification('Заметки сохранены', 'success');
            const book = books.find(b => b.id === bookId);
            if (book) book.notes = notes;
        } else {
            showNotification('Ошибка сохранения заметок', 'error');
        }
    } catch (e) {
        console.error(e);
        showNotification('Ошибка сохранения заметок', 'error');
    }
}


async function deleteBookFromLibrary(bookId) {
    if (!confirm('Вы уверены, что хотите удалить эту книгу?')) return;
    
    try {
        const result = await window.readingAPI.deleteBook(bookId);
        if (result && result.success) {
            showNotification('Книга удалена', 'success');
            await loadBooks();
            closeBookModal();
            navigateToPage('library');
        } else {
            showNotification('Ошибка удаления книги', 'error');
        }
    } catch (e) {
        console.error(e);
        showNotification('Ошибка удаления книги', 'error');
    }
}


async function addReadingSession(bookId) {
    try {
        const now = new Date().toISOString();
        const result = await window.readingAPI.addReadingSession(bookId, now);
        
        if (result && result.success) {
            showNotification('Сессия чтения добавлена!', 'success');
            const book = books.find(b => b.id === bookId);
            if (book) {
                if (!book.reading_sessions) book.reading_sessions = [];
                book.reading_sessions.push(now);
                if (book.status !== 'read') book.status = 'reading';
            }
            showBookDetails(bookId);
        } else {
            showNotification('Ошибка добавления сессии', 'error');
        }
    } catch (e) {
        console.error(e);
        showNotification('Ошибка добавления сессии', 'error');
    }
}


async function updateBookStatus(bookId, newStatus) {
    try {
        const result = await window.readingAPI.updateStatus(bookId, newStatus);
        if (result && !result.error) {
            const book = books.find(b => b.id === bookId);
            if (book) {
                book.status = newStatus;
                await loadBooks();
                showBookDetails(bookId);
                showNotification('Статус обновлен', 'success');
            }
        } else if (result?.error) {
            showNotification(`Ошибка: ${result.error}`, 'error');
        }
    } catch (e) {
        console.error(e);
        showNotification('Ошибка обновления статуса', 'error');
    }
}


async function setRating(bookId, rating) {
    try {
        const result = await window.readingAPI.updateRating(bookId, rating);
        if (result && !result.error) {
            const book = books.find(b => b.id === bookId);
            if (book) {
                book.rating = rating;
                showBookDetails(bookId);
                showNotification('Рейтинг обновлен', 'success');
            }
        }
    } catch (e) {
        console.error(e);
        showNotification('Ошибка установки рейтинга', 'error');
    }
}


async function addBookManually(bookData) {
    try {
        showNotification('Добавление книги...', 'info');
        const result = await window.readingAPI.pythonRequest({ 
            command: 'add_manual_book', 
            data: bookData 
        });
        
        if (result && result.success) {
            await loadBooks();
            showNotification(`✅ Книга "${bookData.title}" добавлена!`, 'success');
            navigateToPage('home');
            return true;
        } else {
            showNotification(`❌ Ошибка: ${result?.error || 'Неизвестная ошибка'}`, 'error');
            return false;
        }
    } catch (e) {
        console.error(e);
        showNotification('❌ Ошибка при добавлении книги', 'error');
        return false;
    }
}


async function handleSearch(event) {
    const query = event.target.value.trim();
    const container = document.getElementById('search-results');
    
    if (query.length < 2) {
        container.innerHTML = '<p class="no-books">Введите минимум 2 символа для поиска</p>';
        return;
    }
    
    try {
        const result = await window.readingAPI.pythonRequest({ 
            command: 'fuzzy_search', 
            data: { query } 
        });
        
        if (result.success && result.data && result.data.length) {
            container.innerHTML = `
                <div class="search-results-header">
                    <p>Найдено ${result.count} книг по запросу "${result.query}"</p>
                    <p class="relevance-hint">🔍 Результаты поиска Google Books</p>
                </div>
                <div class="books-grid search-grid">
                    ${result.data.map(book => createSearchResultCard(book)).join('')}
                </div>
            `;
            
            
            container.querySelectorAll('.search-result-card').forEach(card => {
                card.addEventListener('click', (e) => {
                    if (!e.target.classList.contains('add-book-btn')) {
                        showSearchBookDetails(JSON.parse(card.dataset.book));
                    }
                });
            });
            
            container.querySelectorAll('.add-book-btn').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    e.stopPropagation();
                    const url = btn.dataset.url;
                    if (url) {
                        
                        await addBookFromSearchUrl(url);
                    }
                });
            });
        } else {
            container.innerHTML = `
                <div class="search-results-header">
                    <p>По запросу "${query}" ничего не найдено</p>
                    <p class="relevance-hint">
                        💡 Попробуйте 
                        <button id="manual-add-from-search" class="link-btn">добавить книгу вручную</button>
                    </p>
                </div>
                <div class="no-books">📖 Книги не найдены</div>
            `;
            document.getElementById('manual-add-from-search')?.addEventListener('click', () => openManualAddDialog(query));
        }
    } catch (e) {
        console.error(e);
        container.innerHTML = `
            <div class="search-results-header">
                <p>❌ Ошибка при поиске</p>
                <p class="relevance-hint">
                    💡 Попробуйте 
                    <button id="manual-add-from-search-error" class="link-btn">добавить книгу вручную</button>
                </p>
            </div>
        `;
        document.getElementById('manual-add-from-search-error')?.addEventListener('click', () => openManualAddDialog(query));
    }
}


async function addBookFromSearchUrl(url) {
    showNotification('Добавление книги из поиска...', 'info');
    try {
        const result = await window.readingAPI.addBook({ url });
        if (result.error) {
            showNotification(`Ошибка: ${result.error}`, 'error');
            return false;
        }
        if (result.exists) {
            if (confirm('📚 Книга уже существует. Обновить данные?')) {
                const updateResult = await window.readingAPI.addBook({ url, force_update: true });
                if (updateResult.success) {
                    await loadBooks();
                    showNotification(`✅ Книга "${updateResult.book.title}" обновлена!`, 'success');
                    navigateToPage('home');
                    return true;
                } else {
                    showNotification('❌ Ошибка обновления', 'error');
                }
            }
            return false;
        } else if (result.success) {
            await loadBooks();
            showNotification(`✅ Книга "${result.book.title}" добавлена!`, 'success');
            navigateToPage('home');
            return true;
        } else {
            showNotification('❌ Не удалось добавить книгу', 'error');
            return false;
        }
    } catch (e) {
        console.error(e);
        showNotification('❌ Ошибка при добавлении книги', 'error');
        return false;
    }
}


function createSearchResultCard(book) {
    const coverHtml = book.cover 
        ? `<img src="${book.cover}" alt="${book.title}" onerror="this.parentElement.innerHTML='<div class=\'no-cover\'><i class=\'fas fa-book\'></i></div>'">` 
        : `<div class="no-cover"><i class="fas fa-book"></i></div>`;
        
    const shortTitle = book.title?.length > 35 
        ? book.title.substring(0, 32) + '...' 
        : book.title || 'Без названия';
        
    const shortAuthor = book.author?.length > 25 
        ? book.author.substring(0, 22) + '...' 
        : book.author || 'Неизвестный автор';
    
    const ratingHtml = book.rating && book.rating > 0 
        ? `<div class="book-rating">⭐ ${book.rating.toFixed(1)}</div>` 
        : '';
    
    return `
        <div class="book-card search-result-card" data-book='${JSON.stringify(book)}'>
            <div class="book-cover">${coverHtml}</div>
            <div class="book-info">
                <h3 title="${book.title || 'Без названия'}">${shortTitle}</h3>
                <p class="book-author" title="${book.author || 'Неизвестный автор'}">${shortAuthor}</p>
                ${ratingHtml}
                <button class="add-book-btn" data-url="${book.url}" ${book.is_added ? 'disabled' : ''}>
                    ${book.is_added ? '✓ Уже в библиотеке' : '+ Добавить'}
                </button>
            </div>
        </div>
    `;
}


function showSearchBookDetails(book) {
    const modal = document.createElement('div');
    modal.className = 'modal book-preview-modal';
    modal.style.display = 'flex';
    
    const coverHtml = book.cover 
        ? `<img src="${book.cover}" alt="${book.title}" onerror="this.parentElement.innerHTML='<i class=\'fas fa-book\'></i>'">` 
        : `<i class="fas fa-book"></i>`;
    
    modal.innerHTML = `
        <div class="modal-content book-preview-content">
            <span class="close-modal preview-close">&times;</span>
            <div class="book-preview-container">
                <div class="book-preview-cover">${coverHtml}</div>
                <div class="book-preview-info">
                    <h2>${book.title || 'Без названия'}</h2>
                    <p class="book-preview-author">${book.author || 'Неизвестный автор'}</p>
                    <div class="book-preview-meta">
                        <div class="book-preview-meta-item">
                            <i class="fas fa-tag"></i>
                            <span>${book.genre || 'Жанр не указан'}</span>
                        </div>
                        ${book.rating && book.rating > 0 ? `
                        <div class="book-preview-meta-item">
                            <i class="fas fa-star"></i>
                            <span>${book.rating.toFixed(1)} / 5</span>
                        </div>` : ''}
                    </div>
                    ${book.description ? `<p class="book-preview-description">${book.description.substring(0, 200)}${book.description.length > 200 ? '...' : ''}</p>` : ''}
                    <div class="book-preview-actions">
                        <select class="status-select preview-status-select">
                            <option value="want_to_read">Хочу прочитать</option>
                            <option value="reading">Читаю</option>
                            <option value="read">Прочитано</option>
                            <option value="abandoned">Брошено</option>
                        </select>
                        <button class="preview-add-btn btn-primary">Добавить в библиотеку</button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    modal.querySelector('.preview-close').addEventListener('click', () => modal.remove());
    modal.addEventListener('click', (e) => { if (e.target === modal) modal.remove(); });
    
    const addBtn = modal.querySelector('.preview-add-btn');
    const statusSelect = modal.querySelector('.preview-status-select');
    
    addBtn.addEventListener('click', async () => {
        const selectedStatus = statusSelect.value;
        addBtn.disabled = true;
        addBtn.textContent = 'Добавление...';
        
        try {
            const result = await window.readingAPI.addBook({ url: book.url });
            if (result.error) {
                showNotification(`Ошибка: ${result.error}`, 'error');
                addBtn.disabled = false;
                addBtn.textContent = 'Добавить в библиотеку';
                return;
            }
            
            if (result.exists && result.book) {
                if (selectedStatus !== result.book.status) {
                    await window.readingAPI.updateStatus(result.book.id, selectedStatus);
                }
                showNotification(`Книга "${result.book.title}" уже есть в библиотеке`, 'success');
            } else if (result.success && result.book) {
                if (selectedStatus !== 'want_to_read') {
                    await window.readingAPI.updateStatus(result.book.id, selectedStatus);
                }
                showNotification(`Книга "${result.book.title}" добавлена!`, 'success');
            }
            
            await loadBooks();
            modal.remove();
            navigateToPage('home');
        } catch (e) {
            console.error(e);
            showNotification('Ошибка добавления книги', 'error');
            addBtn.disabled = false;
            addBtn.textContent = 'Добавить в библиотеку';
        }
    });
}


function showAddMethodSelector() {
    
    openManualAddDialog();
}


function openManualAddDialog(prefilledQuery = '') {
    const modal = document.createElement('div');
    modal.className = 'modal manual-add-modal';
    modal.style.display = 'flex';
    
    modal.innerHTML = `
        <div class="modal-content manual-add-content">
            <span class="close-modal manual-close">&times;</span>
            <h2><i class="fas fa-pen-alt"></i> Добавить книгу вручную</h2>
            <p class="manual-add-desc">Заполните информацию. Обязательные поля отмечены <span class="required-star">*</span></p>
            <form id="manual-book-form">
                <div class="form-row">
                    <div class="form-group">
                        <label>Название <span class="required-star">*</span></label>
                        <input type="text" id="manual-title" placeholder="Введите название книги" value="${prefilledQuery.replace(/"/g, '&quot;')}" required>
                    </div>
                    <div class="form-group">
                        <label>Автор <span class="required-star">*</span></label>
                        <input type="text" id="manual-author" placeholder="Введите автора" required>
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label>Жанр</label>
                        <input type="text" id="manual-genre" placeholder="Например: фэнтези, роман">
                    </div>
                    <div class="form-group">
                        <label>Рейтинг (0-5)</label>
                        <select id="manual-rating">
                            <option value="0">Не оценено</option>
                            <option value="1">⭐ 1</option>
                            <option value="2">⭐⭐ 2</option>
                            <option value="3">⭐⭐⭐ 3</option>
                            <option value="4">⭐⭐⭐⭐ 4</option>
                            <option value="5">⭐⭐⭐⭐⭐ 5</option>
                        </select>
                    </div>
                </div>
                <div class="form-group">
                    <label>Статус чтения</label>
                    <select id="manual-status">
                        <option value="want_to_read">📚 Хочу прочитать</option>
                        <option value="reading">📖 Читаю</option>
                        <option value="read">✅ Прочитано</option>
                        <option value="abandoned">❌ Брошено</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>URL обложки</label>
                    <input type="url" id="manual-cover" placeholder="https://example.com/cover.jpg">
                    <small class="form-hint">Оставьте пустым, если нет ссылки</small>
                </div>
                <div class="form-group">
                    <label>Описание</label>
                    <textarea id="manual-description" rows="4" placeholder="Краткое описание..."></textarea>
                </div>
                <div class="form-actions">
                    <button type="button" id="cancel-manual-btn" class="btn-secondary">Отмена</button>
                    <button type="submit" id="submit-manual-btn" class="btn-primary"><i class="fas fa-save"></i> Добавить книгу</button>
                </div>
            </form>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    const closeModal = () => modal.remove();
    modal.querySelector('.manual-close').addEventListener('click', closeModal);
    modal.querySelector('#cancel-manual-btn').addEventListener('click', closeModal);
    modal.addEventListener('click', (e) => { if (e.target === modal) closeModal(); });
    
    const form = modal.querySelector('#manual-book-form');
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const title = modal.querySelector('#manual-title').value.trim();
        const author = modal.querySelector('#manual-author').value.trim();
        
        if (!title || !author) {
            showNotification('Заполните название и автора', 'error');
            return;
        }
        
        const bookData = {
            title,
            author,
            genre: modal.querySelector('#manual-genre').value.trim() || 'Без жанра',
            rating: parseInt(modal.querySelector('#manual-rating').value),
            cover: modal.querySelector('#manual-cover').value.trim() || null,
            description: modal.querySelector('#manual-description').value.trim() || '',
            status: modal.querySelector('#manual-status').value
        };
        
        const submitBtn = modal.querySelector('#submit-manual-btn');
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Добавление...';
        
        const success = await addBookManually(bookData);
        if (success) {
            closeModal();
        } else {
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<i class="fas fa-save"></i> Добавить книгу';
        }
    });
    
    setTimeout(() => modal.querySelector('#manual-title').focus(), 100);
}


function updateStats() {
    const booksArray = Array.isArray(books) ? books : [];
    document.getElementById('reading-count').textContent = booksArray.filter(b => b.status === 'reading').length;
    document.getElementById('read-count').textContent = booksArray.filter(b => b.status === 'read').length;
    document.getElementById('total-books').textContent = booksArray.length;
}


function navigateToPage(page) {
    document.querySelectorAll('.nav-item').forEach(item => item.classList.remove('active'));
    document.querySelector(`.nav-item[data-page="${page}"]`)?.classList.add('active');
    
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.getElementById(`${page}-page`)?.classList.add('active');
    
    currentPage = page;
    
    if (page === 'home') {
        showRecentBooks();
        loadCalendar();
    } else if (page === 'library') {
        applyFilters();
    }
}


async function loadCalendar(year = null, month = null) {
    const container = document.getElementById('calendar-container');
    if (!container) return;
    
    const now = new Date();
    if (year === null) year = now.getFullYear();
    if (month === null) month = now.getMonth() + 1;
    
    try {
        const result = await window.readingAPI.pythonRequest({
            command: 'get_calendar',
            data: { year: year, month: month }
        });
        
        if (result && result.success) {
            container.innerHTML = result.html;
            
            
            document.querySelectorAll('.calendar-nav-prev').forEach(btn => {
                btn.addEventListener('click', () => {
                    const newYear = parseInt(btn.dataset.year);
                    const newMonth = parseInt(btn.dataset.month);
                    loadCalendar(newYear, newMonth);
                });
            });
            
            document.querySelectorAll('.calendar-nav-next').forEach(btn => {
                btn.addEventListener('click', () => {
                    const newYear = parseInt(btn.dataset.year);
                    const newMonth = parseInt(btn.dataset.month);
                    loadCalendar(newYear, newMonth);
                });
            });
            
            document.querySelectorAll('.calendar-nav-today').forEach(btn => {
                btn.addEventListener('click', () => {
                    const today = new Date();
                    loadCalendar(today.getFullYear(), today.getMonth() + 1);
                });
            });
            
            
            document.querySelectorAll('.calendar-day.has-reading').forEach(day => {
                day.addEventListener('mouseenter', (e) => {
                    const date = e.target.dataset.date;
                    
                });
            });
        } else {
            container.innerHTML = '<div class="calendar-error">Ошибка загрузки календаря</div>';
        }
    } catch (error) {
        console.error('Ошибка загрузки календаря:', error);
        container.innerHTML = '<div class="calendar-error">Ошибка загрузки календаря</div>';
    }
}


function setupEventListeners() {
    
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', () => navigateToPage(item.dataset.page));
    });
    
    
    document.getElementById('status-filter')?.addEventListener('change', (e) => {
        currentStatusFilter = e.target.value;
        applyFilters();
    });
    
    
    document.getElementById('search-input')?.addEventListener('input', debounce(handleSearch, 300));
    
    
    document.querySelector('.close-modal')?.addEventListener('click', closeBookModal);
    window.addEventListener('click', (e) => {
        if (e.target === document.getElementById('book-modal')) closeBookModal();
    });
    
    
    document.getElementById('add-book-btn')?.addEventListener('click', showAddMethodSelector);
}


function debounce(func, wait) {
    let timeout;
    return function(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func(...args), wait);
    };
}