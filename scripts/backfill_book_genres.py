"""Populate missing genres once and reuse saved classifications thereafter."""

import os
from contextlib import closing
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

from book_genres import classify_primary_genre, get_or_classify_genre, initialize_genre_store


def main():
    load_dotenv(Path(__file__).resolve().parents[1] / '.env')
    database_url = os.environ['DATABASE_URL']
    api_key = os.environ['OPENAI_API_KEY']

    with closing(psycopg2.connect(database_url)) as connection:
        with connection:
            print('Genre registry:', initialize_genre_store(connection), flush=True)
            with connection.cursor() as cursor:
                cursor.execute('SELECT title, author, type FROM books_read_ratings ORDER BY lower(title)')
                books = cursor.fetchall()

        for index, (title, author, book_type) in enumerate(books, start=1):
            book_info = {'title': title, 'author': author or '', 'type': book_type or ''}
            with connection:
                genre = get_or_classify_genre(
                    connection, book_info, lambda: classify_primary_genre(book_info, api_key)
                )
                if genre != 'Unknown':
                    with connection.cursor() as cursor:
                        cursor.execute('''
                            UPDATE books_read_ratings SET genres = %s
                            WHERE title = %s AND author IS NOT DISTINCT FROM %s
                        ''', (genre, title, author))
            print(f'{index}/{len(books)} {title}: {genre}', flush=True)

        with connection:
            print('Genre registry:', initialize_genre_store(connection), flush=True)


if __name__ == '__main__':
    main()
