"""Persistent, write-once genre classifications for books."""

import re
from typing import Dict

import requests
from openai import OpenAI

OPENAI_TEXT_MODEL = 'gpt-5.6-terra'

SCHEMA_SQL = """
    CREATE TABLE IF NOT EXISTS book_genres (
        id BIGSERIAL PRIMARY KEY,
        title TEXT NOT NULL,
        author TEXT NOT NULL DEFAULT '',
        title_key TEXT NOT NULL,
        author_key TEXT NOT NULL,
        genre TEXT,
        classified_at TIMESTAMPTZ,
        UNIQUE (title_key, author_key),
        CHECK (genre IS NULL OR (btrim(genre) <> '' AND lower(btrim(genre)) NOT IN ('unknown', 'uncategorized')))
    )
"""


def normalize_book_key(value):
    return re.sub(r'\s+', ' ', str(value or '')).strip().lower()


def valid_genre(value):
    return isinstance(value, str) and value.strip().lower() not in ('', 'unknown', 'uncategorized')


def find_or_add_book(cursor, title, author):
    title_key = normalize_book_key(title)
    author_key = normalize_book_key(str(author or '').split(',')[0])
    if not title_key:
        raise ValueError('A book title is required for genre classification.')

    # Serialize classification for the same title across concurrent updater runs.
    cursor.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))', (title_key,))
    cursor.execute('SELECT id, author_key, genre FROM book_genres WHERE title_key = %s', (title_key,))
    books = cursor.fetchall()
    match = next((book for book in books if book[1] == author_key), None)
    if match is None and len(books) == 1 and (not author_key or not books[0][1]):
        match = books[0]
        if author_key and not match[1]:
            cursor.execute('UPDATE book_genres SET author = %s, author_key = %s WHERE id = %s',
                           (author.strip(), author_key, match[0]))
    if match is not None:
        return match[0], match[2]

    cursor.execute('''
        INSERT INTO book_genres (title, author, title_key, author_key)
        VALUES (%s, %s, %s, %s) RETURNING id
    ''', (title.strip(), str(author or '').strip(), title_key, author_key))
    return cursor.fetchone()[0], None


def initialize_genre_store(connection):
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_advisory_xact_lock(hashtextextended('book_genres_schema', 0))")
        cursor.execute(SCHEMA_SQL)
        cursor.execute("SELECT to_regclass('books_read_ratings')")
        if cursor.fetchone()[0]:
            cursor.execute('SELECT title, author, genres, genre FROM books_read_ratings ORDER BY lower(title)')
            books = cursor.fetchall()
            for title, author, genre, manual_genre in books:
                if not title:
                    continue
                book_id, saved_genre = find_or_add_book(cursor, title, author)
                candidate = genre if valid_genre(genre) else manual_genre
                if not saved_genre and valid_genre(candidate):
                    cursor.execute('''
                        UPDATE book_genres SET genre = %s, classified_at = CURRENT_TIMESTAMP
                        WHERE id = %s AND genre IS NULL
                    ''', (candidate.strip().lower(), book_id))
        cursor.execute('SELECT COUNT(*), COUNT(genre) FROM book_genres')
        total, classified = cursor.fetchone()
    return {'books': total, 'classified': classified, 'pending': total - classified}


def get_or_classify_genre(connection, book_info, classifier):
    with connection.cursor() as cursor:
        book_id, saved_genre = find_or_add_book(cursor, book_info['title'], book_info.get('author', ''))
        if saved_genre:
            return saved_genre
        genre = classifier()
        if not valid_genre(genre):
            return 'Unknown'
        genre = genre.strip().lower()
        cursor.execute('''
            UPDATE book_genres SET genre = %s, classified_at = CURRENT_TIMESTAMP
            WHERE id = %s AND genre IS NULL RETURNING genre
        ''', (genre, book_id))
        saved = cursor.fetchone()
        if saved is None:
            cursor.execute('SELECT genre FROM book_genres WHERE id = %s', (book_id,))
            saved = cursor.fetchone()
        return saved[0]


def get_open_library_genre(book_info: Dict[str, str]) -> str:
    title = book_info.get('title', '').strip()
    author = book_info.get('author', '').split(',')[0].strip()
    title_parts = re.split(r'\s+by\s+', title, maxsplit=1, flags=re.IGNORECASE)
    if len(title_parts) == 2:
        title, author = title_parts
    title = re.sub(r'\s+\([^()]*\)\s*$', '', title).strip()
    params = {'title': title, 'fields': 'subject', 'limit': 1}
    if author:
        params['author'] = re.sub(r'\s+', ' ', author)
    try:
        response = requests.get('https://openlibrary.org/search.json', params=params, timeout=10,
                                headers={'User-Agent': 'BookRatingsDashboard/1.0 (https://book-ratings-dash-f20755edd755.herokuapp.com)'})
        response.raise_for_status()
        matches = response.json().get('docs', [])
        subjects = (matches[0].get('subject') or []) if matches else []
    except (requests.RequestException, ValueError, KeyError):
        return ''

    subject_genres = {
        'science fiction': ['science fiction'],
        'dystopian': ['dystopia', 'dystopian'],
        'fantasy': ['fantasy', 'magical realism'],
        'horror': ['horror'],
        'mystery': ['mystery', 'detective stories', 'detective fiction'],
        'thriller': ['thriller', 'thrillers', 'suspense fiction'],
        'romance': ['romance', 'love stories'],
        'historical fiction': ['historical fiction', 'fiction historical'],
        'memoir': ['memoir', 'memoirs', 'autobiography', 'autobiographies'],
        'biography': ['biography', 'biographies'],
        'self-help': ['self help', 'personal development'],
        'political fiction': ['political fiction', 'fiction political'],
        'psychological fiction': ['psychological fiction', 'fiction psychological'],
        'coming-of-age': ['coming of age', 'bildungsroman'],
        'satire': ['satire', 'satirical fiction'],
        'literary fiction': ['literary fiction', 'fiction literary'],
        'non-fiction': ['nonfiction', 'non fiction'],
    }
    normalized_subjects = [re.sub(r'[^a-z0-9]+', ' ', subject.lower()).strip() for subject in subjects]
    for genre, labels in subject_genres.items():
        if any(re.search(r'\b' + re.escape(label) + r'\b', subject)
               for label in labels for subject in normalized_subjects):
            return genre
    return ''


def classify_primary_genre(book_info: Dict[str, str], api_key: str) -> str:
    """
    Use catalog subjects, with model classification for unmatched titles.
    """
    catalog_genre = get_open_library_genre(book_info)
    if catalog_genre:
        return catalog_genre
    client = OpenAI(api_key=api_key, max_retries=0)

    prompt = f"""Based on this book information, what is the single most specific and meaningful literary genre?
Choose from these common book genres ONLY:
- coming-of-age
- psychological fiction
- historical fiction
- science fiction
- fantasy
- mystery
- thriller
- romance
- literary fiction
- dystopian
- horror
- memoir
- biography
- political fiction
- satire
- non-fiction
- self-help

Title: {book_info.get('title', '')}
Author: {book_info.get('author', '')}
Book type: {book_info.get('type', '')}
Description: {book_info.get('description', '')}
Goodreads genres: {book_info.get('raw_genres', [])}

Respond ONLY with the genre name, nothing else. Choose the MOST specific genre that best captures the book's primary theme."""

    try:
        # Use the new method for creating chat completions
        response = client.chat.completions.create(
            model=OPENAI_TEXT_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a literary expert who specializes in genre classification. "
                        "Respond only with the genre name, without explanation."
                    )
                },
                {"role": "user", "content": prompt},
            ],
            reasoning_effort="none",
            max_completion_tokens=32,
        )

        # Access the content differently in the new version
        genre = response.choices[0].message.content.strip().lower()
        return genre

    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        return "Unknown"

