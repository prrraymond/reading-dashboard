import ast
import re
import unittest
import urllib.parse
from pathlib import Path
from typing import Dict
from unittest.mock import Mock, patch

from bs4 import BeautifulSoup


class GoodreadsParserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = ast.parse(Path(__file__).with_name('update_database.py').read_text())
        functions = ast.Module(body=[
            node for node in source.body
            if isinstance(node, ast.FunctionDef)
            and node.name in ('parse_goodreads_count', 'parse_goodreads_search_results')
        ], type_ignores=[])
        genre_source = ast.parse(Path(__file__).with_name('book_genres.py').read_text())
        functions.body.extend(node for node in genre_source.body
                              if isinstance(node, ast.FunctionDef) and node.name == 'get_open_library_genre')
        cls.namespace = {
            'BeautifulSoup': BeautifulSoup, 're': re, 'urllib': urllib,
            'api_key': '', 'get_primary_genre': lambda *_: 'historical fiction',
            'get_rating_from_openai': lambda *_: None,
            'Dict': Dict, 'requests': Mock(),
        }
        exec(compile(functions, 'goodreads_parser', 'exec'), cls.namespace)

    def parse(self, html):
        return self.namespace['parse_goodreads_search_results'](html)

    def test_new_search_layout(self):
        books = self.parse('''
            <div class="Book" data-testid="book-item-123">
              <span data-testid="book-item-title"><a href="/book/show/123">Hamnet</a></span>
              <span data-testid="name">Maggie O'Farrell</span>
              <span data-testid="book-item-rating">4.20</span>
              <span data-testid="book-item-ratings-count">528k ratings</span>
              <span data-testid="book-item-editions-count">134 Editions</span>
              <div aria-label="Rate Hamnet"><span aria-label="Rating 0 out of 5"></span></div>
            </div>
        ''')
        self.assertEqual(len(books), 1)
        self.assertEqual(books[0]['rating'], 4.2)
        self.assertEqual(books[0]['author'], "Maggie O'Farrell")
        self.assertEqual(books[0]['num_ratings'], 528000)
        self.assertEqual(books[0]['num_editions'], 134)
        self.assertEqual(books[0]['url'], 'https://www.goodreads.com/book/show/123')

    def test_old_search_layout(self):
        books = self.parse('''
            <table><tr itemscope="" itemtype="http://schema.org/Book">
              <td><a class="bookTitle" href="/book/show/123">Hamnet</a>
                <div class="authorName__container"><a class="authorName">Maggie O'Farrell</a></div>
                <span class="minirating">really liked it 4.20 avg rating — 528,000 ratings</span>
              </td>
            </tr></table>
        ''')
        self.assertEqual(books[0]['rating'], 4.2)
        self.assertEqual(books[0]['num_ratings'], 528000)

    def test_unrated_book_remains_missing(self):
        books = self.parse('''
            <div class="Book" data-testid="book-item-123">
              <span data-testid="book-item-title"><a href="/book/show/123">Unrated book</a></span>
              <span aria-label="Rating 0 out of 5"></span>
            </div>
        ''')
        self.assertIsNone(books[0]['rating'])
        self.assertIsNone(books[0]['num_ratings'])

    def test_no_results(self):
        self.assertEqual(self.parse('<h1>No results found</h1>'), [])

    def test_rating_refresh_can_skip_genre_classification(self):
        classifier = Mock(side_effect=AssertionError('Ratings refresh must not reclassify genres'))
        with patch.dict(self.namespace, {'get_primary_genre': classifier}):
            books = self.namespace['parse_goodreads_search_results']('''
                <div class="Book" data-testid="book-item-123">
                  <span data-testid="book-item-title"><a href="/book/show/123">Hamnet</a></span>
                  <span data-testid="book-item-rating">4.20</span>
                </div>
            ''', include_genre=False)
        self.assertEqual(books[0]['rating'], 4.2)
        classifier.assert_not_called()

    def test_abbreviated_counts(self):
        parse = self.namespace['parse_goodreads_count']
        for text, expected in [('528k ratings', 528000), ('1.2m ratings', 1200000), ('1,234 ratings', 1234)]:
            with self.subTest(text=text):
                self.assertEqual(parse(text), expected)

    def test_catalog_genres(self):
        lookup = self.namespace['get_open_library_genre']
        response = self.namespace['requests'].get.return_value
        for subjects, expected in [
            (['FICTION / Historical / General', 'FICTION / Literary'], 'historical fiction'),
            (['Fiction', 'Fantasy fiction'], 'fantasy'),
            (['nonfiction', 'psychology'], 'non-fiction'),
            (['Fiction', 'Detective and mystery stories'], 'mystery'),
            (['Fiction', 'Libraries'], ''),
        ]:
            with self.subTest(subjects=subjects):
                response.json.return_value = {'docs': [{'subject': subjects}]}
                self.assertEqual(lookup({'title': 'A book'}), expected)

    def test_catalog_query_uses_primary_author_and_cleans_title(self):
        lookup = self.namespace['get_open_library_genre']
        self.namespace['requests'].get.return_value.json.return_value = {'docs': []}
        lookup({'title': 'My Friends', 'author': 'Fredrik Backman, Neil Smith'})
        params = self.namespace['requests'].get.call_args.kwargs['params']
        self.assertEqual(params['author'], 'Fredrik Backman')
        lookup({'title': 'James By Percival Everett', 'author': 'SuperSummary'})
        params = self.namespace['requests'].get.call_args.kwargs['params']
        self.assertEqual(params['title'], 'James')
        self.assertEqual(params['author'], 'Percival Everett')


if __name__ == '__main__':
    unittest.main()
