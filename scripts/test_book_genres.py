"""Integration checks use transaction-local tables and never change production rows."""

import os
import unittest
from pathlib import Path
from unittest.mock import Mock

import psycopg2
from dotenv import load_dotenv

from book_genres import SCHEMA_SQL, get_or_classify_genre, initialize_genre_store


class BookGenreStoreTests(unittest.TestCase):
    def setUp(self):
        load_dotenv(Path(__file__).resolve().parents[1] / '.env')
        self.connection = psycopg2.connect(os.environ['DATABASE_URL'])
        with self.connection.cursor() as cursor:
            cursor.execute('CREATE TEMP TABLE books_read_ratings AS SELECT * FROM public.books_read_ratings WITH NO DATA')
            cursor.execute(SCHEMA_SQL.replace('CREATE TABLE IF NOT EXISTS', 'CREATE TEMP TABLE'))

    def tearDown(self):
        self.connection.rollback()
        self.connection.close()

    def test_classifies_once_and_reuses_normalized_identity(self):
        classifier = Mock(return_value='historical fiction')
        first = get_or_classify_genre(self.connection, {'title': 'A Book', 'author': 'An Author'}, classifier)
        second = get_or_classify_genre(self.connection, {'title': ' a  book ', 'author': 'AN AUTHOR, A Translator'}, classifier)
        self.assertEqual(first, 'historical fiction')
        self.assertEqual(second, first)
        classifier.assert_called_once()

    def test_saved_genre_survives_ratings_refresh_and_remains_authoritative(self):
        with self.connection.cursor() as cursor:
            cursor.execute("INSERT INTO books_read_ratings (title, author, genres) VALUES ('A Book', 'An Author', 'historical fiction')")
        initialize_genre_store(self.connection)
        with self.connection.cursor() as cursor:
            cursor.execute('SELECT id, genre, classified_at FROM book_genres')
            original = cursor.fetchone()
            cursor.execute('DROP TABLE pg_temp.books_read_ratings')
            cursor.execute('CREATE TEMP TABLE books_read_ratings AS SELECT * FROM public.books_read_ratings WITH NO DATA')
            cursor.execute("INSERT INTO books_read_ratings (title, author, genres) VALUES ('A Book', 'An Author', 'romance')")
        initialize_genre_store(self.connection)
        classifier = Mock(side_effect=AssertionError('A saved genre must bypass classification'))
        self.assertEqual(get_or_classify_genre(self.connection, {'title': 'A Book', 'author': 'An Author'}, classifier), 'historical fiction')
        with self.connection.cursor() as cursor:
            cursor.execute('SELECT id, genre, classified_at FROM book_genres')
            self.assertEqual(cursor.fetchone(), original)
            api_file = Path(__file__).resolve().parents[1] / 'pages/api/book-ratings.ts'
            query = api_file.read_text().split('await pool.query(`', 1)[1].split('`);', 1)[0]
            cursor.execute(query)
            columns = [column.name for column in cursor.description]
            row = dict(zip(columns, cursor.fetchone()))
            self.assertEqual(row['genres'], 'historical fiction')

    def test_failed_classification_can_be_retried(self):
        book = {'title': 'A Book', 'author': 'An Author'}
        self.assertEqual(get_or_classify_genre(self.connection, book, lambda: 'Unknown'), 'Unknown')
        with self.connection.cursor() as cursor:
            cursor.execute('SELECT genre, classified_at FROM book_genres')
            self.assertEqual(cursor.fetchone(), (None, None))
        self.assertEqual(get_or_classify_genre(self.connection, book, lambda: 'literary fiction'), 'literary fiction')

    def test_different_authors_with_same_title_keep_distinct_genres(self):
        first = {'title': 'My Friends', 'author': 'First Author'}
        second = {'title': 'My Friends', 'author': 'Second Author'}
        get_or_classify_genre(self.connection, first, lambda: 'historical fiction')
        get_or_classify_genre(self.connection, second, lambda: 'literary fiction')
        classifier = Mock(side_effect=AssertionError('Existing books must keep their genres'))
        self.assertEqual(get_or_classify_genre(self.connection, first, classifier), 'historical fiction')
        self.assertEqual(get_or_classify_genre(self.connection, second, classifier), 'literary fiction')

    def test_author_can_be_filled_without_changing_genre(self):
        get_or_classify_genre(self.connection, {'title': 'A Book'}, lambda: 'historical fiction')
        classifier = Mock(side_effect=AssertionError('Author metadata must not trigger reclassification'))
        self.assertEqual(get_or_classify_genre(self.connection, {'title': 'A Book', 'author': 'An Author'}, classifier), 'historical fiction')
        with self.connection.cursor() as cursor:
            cursor.execute('SELECT COUNT(*), MAX(author) FROM book_genres')
            self.assertEqual(cursor.fetchone(), (1, 'An Author'))


if __name__ == '__main__':
    unittest.main()
