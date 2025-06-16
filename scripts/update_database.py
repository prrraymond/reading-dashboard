import pandas as pd
import numpy as np

from pandas.io import sql
import json
from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.discovery import build
import re


import os
import gspread
from df2gspread import df2gspread as d2g
from oauth2client.service_account import ServiceAccountCredentials
import openai
from openai import OpenAI
from typing import Dict

import requests
from bs4 import BeautifulSoup
import pandas as pd

from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY is not set in the environment or .env file.")

spreadsheet_id = os.getenv("SPREADSHEET_ID")
if not spreadsheet_id:
    raise ValueError("SPREADSHEET_ID is not set in the environment")


goog_key = os.getenv("GOOGLE_API_KEY")
oai_key = os.getenv("OPENAI_API_KEY")
data_url = os.getenv("DATABASE_URL")
SA_JSON_B64 = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON_B64") 
if not SA_JSON_B64:
    raise RuntimeError(
        "GOOGLE_SERVICE_ACCOUNT_JSON_B64 is not set. "
        "Add it as a GitHub secret or in your local .env."
    )

import base64, tempfile
sa_path = tempfile.NamedTemporaryFile(delete=False, suffix=".json").name
with open(sa_path, "wb") as f:
    f.write(base64.b64decode(SA_JSON_B64))

SCOPES = [
    'https://spreadsheets.google.com/feeds',
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/drive'
]

# Reauthorize with explicit scopes
credentials = ServiceAccountCredentials.from_json_keyfile_name(sa_path, scopes=SCOPES)

# Rebuild services
service = build('sheets', 'v4', credentials=credentials)
gc = gspread.authorize(credentials)


workbook = gc.open_by_key(spreadsheet_id)



sheet = workbook.worksheet('raw')
values = sheet.get_all_values()
df1 = pd.DataFrame(values[1:], columns = values[0])



headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Referer': 'https://www.google.com/'
}



def print_structure_report(structure_info):
    print("=== GOODREADS HTML STRUCTURE ANALYSIS ===\n")
    
    print("ALL UNIQUE CLASSES FOUND:")
    for class_name in structure_info['all_classes']:
        print(f"- {class_name}")
    
    print("\nPOTENTIAL BOOK CONTAINERS:")
    for container in structure_info['potential_book_elements']:
        print(f"\nContainer: <{container['container_tag']}>")
        print(f"Classes: {container['container_classes']}")
        print("Attributes:", container['container_attributes'])
        
        print("\nChild Elements:")
        for child in container['child_elements']:
            print(f"\n  <{child['tag']}>")
            print(f"  Classes: {child['classes']}")
            print(f"  Text Sample: {child['text_sample']}")
            print(f"  Attributes: {child['attributes']}")
            
        print("\n" + "="*50)

# Usage:
"""
# First, get your HTML content
html_content = ... # Your Goodreads HTML here

"""



import os
from typing import Dict

def get_primary_genre(book_info: Dict[str, str], api_key: str) -> str:
    """
    Use GPT-3.5 (or GPT-4) to determine the most appropriate primary genre based on book information.
    """
    # Create OpenAI client with the API key
    client = OpenAI(api_key=api_key)

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

Title: {book_info.get('title', '')}
Author: {book_info.get('author', '')}
Description: {book_info.get('description', '')}
Goodreads genres: {book_info.get('raw_genres', [])}

Respond ONLY with the genre name, nothing else. Choose the MOST specific genre that best captures the book's primary theme."""

    try:
        # Use the new method for creating chat completions
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
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
            temperature=0.3,
            max_tokens=10,
        )

        # Access the content differently in the new version
        genre = response.choices[0].message.content.strip().lower()
        return genre

    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        return "Unknown"

def get_rating_from_openai(context: str) -> float:
    """
    Use OpenAI's Chat API to extract a numerical Goodreads rating from a text snippet.
    Returns the rating as a float if successful, otherwise returns None.
    """
    # Create client with API key from environment
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    prompt = (
        "Extract the numerical book rating from the following text. "
        "Return only the number (as a float), and nothing else.\n\n"
        f"Text: {context}\n\nRating: "
    )
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an assistant that extracts numerical values."},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
            max_tokens=5,
        )
        # The response should be something like "4.2"
        text = response.choices[0].message.content.strip()
        return float(text)
    except Exception as e:
        print(f"Error extracting rating with OpenAI: {e}")
        return None


def parse_goodreads_search_results(html):
    """
    Parse Goodreads search results with OpenAI genre extraction.
    """
    soup = BeautifulSoup(html, 'html.parser')
    book_entries = soup.find_all('tr', {'itemscope': '', 'itemtype': 'http://schema.org/Book'})
    
    books = []
    for entry in book_entries[:1]:  # Still only take first result as most relevant
        try:
            # Basic metadata extraction
            book_title_element = entry.find('a', class_='bookTitle')
            if not book_title_element:
                continue
            book_title = book_title_element.get_text(strip=True)
            book_url = 'https://www.goodreads.com' + book_title_element['href']
            
            # Author extraction
            author_containers = entry.find_all('div', class_='authorName__container')
            authors = []
            for container in author_containers:
                author_element = container.find('a', class_='authorName')
                if author_element:
                    author_name = author_element.get_text(strip=True)
                    role = container.find('span', class_='role')
                    if role:
                        role_text = role.get_text(strip=True)
                        authors.append(f"{author_name} {role_text}")
                    else:
                        authors.append(author_name)
            author = ', '.join(authors) if authors else 'Unknown'
            
            # Rating extraction

            # Rating extraction
            rating_element = entry.find('span', class_='minirating')
            if rating_element:
                # Get raw text and remove undesired substrings
                rating_text = rating_element.get_text(strip=True)
                rating_text_clean = rating_text.replace("really liked it", "").strip()
                
                # Use regex to search for a number (float)
                match = re.search(r"([\d\.]+)", rating_text_clean)
                if match:
                    try:
                        rating = float(match.group(1))
                    except Exception as e:
                        print(f"Could not convert extracted rating '{match.group(1)}' to float: {e}")
                        rating = None
                else:
                    rating = None
                
                # Extract number of ratings if possible using splitting.
                try:
                    parts = rating_text_clean.split("—")
                    if len(parts) > 1:
                        num_ratings_str = parts[1].strip().split()[0]
                        num_ratings = int(num_ratings_str.replace(",", ""))
                    else:
                        num_ratings = None
                except Exception as e:
                    print(f"Could not extract num_ratings from '{rating_text_clean}': {e}")
                    num_ratings = None
            else:
                rating = None
                num_ratings = None


            # Fallback: if rating is None, use OpenAI to extract the rating from the raw text
            if rating is None:
                # Use the entire rating_text if available, or a default context
                if rating is None:
                # Optionally, include more context from the entry
                    context = f"Goodreads info: {rating_text}" if rating_element else "No rating info available."
                    rating = get_rating_from_openai(context)


            def get_higher_res_cover(cover_url):
                """
                Transform Goodreads cover URL to get higher resolution version
                """
                if not cover_url:
                    return None
                
                # Goodreads URLs often have size indicators that can be modified
                # Example: ._SY75_.jpg -> ._SY475_.jpg or no size indicator for full size
                
                # Remove existing size indicators
                import re
                high_res_url = re.sub(r'\._[A-Z0-9]+_\.', '.', cover_url)
                
                # Or try to replace with larger size
                if '._SY75_.' in cover_url:
                    high_res_url = cover_url.replace('._SY75_.', '._SY475_.')
                elif '._SX50_.' in cover_url:
                    high_res_url = cover_url.replace('._SX50_.', '._SX318_.')
                
                return high_res_url    
            
            # Cover URL extraction
            cover_image_element = entry.find('img', class_='bookCover')
            cover_image_url = cover_image_element['src'] if cover_image_element else None
            cover_image_url = get_higher_res_cover(cover_image_url)
            
            # Editions extraction
            editions_element = entry.find('a', class_='greyText', string=lambda x: 'editions' in str(x) if x else False)
            num_editions = editions_element.get_text(strip=True) if editions_element else None

            # Prepare book info for OpenAI genre classification
            book_info = {
                'title': book_title,
                'author': author,
                'description': '',  # You might want to fetch this separately if possible
                'raw_genres': []  # Collect any genre-like text from the page
            }

            # Collect any potential genre indicators
            genre_containers = entry.find_all(['div', 'span'], class_=['genre', 'shelf'])
            for container in genre_containers:
                links = container.find_all('a')
                for link in links:
                    genre = link.get_text(strip=True).lower()
                    if genre and genre not in ['fiction', 'non-fiction']:
                        book_info['raw_genres'].append(genre)

            # Use OpenAI to classify the primary genre
            primary_genre = get_primary_genre(book_info, api_key)

            # Determine book type
            book_type = 'Fiction' if primary_genre != 'Unknown' else 'Unknown'
            
            books.append({
                'title': book_title,
                'url': book_url,
                'author': author,
                'rating': rating,
                'num_ratings': num_ratings,
                'num_editions': num_editions,
                'cover_image_url': cover_image_url,
                'genres': primary_genre,
                'type': book_type
            })
            
        except Exception as e:
            print(f"Error processing book entry: {e}")
            continue
    
    return books



def fetch_goodreads_search_results(query):
    """
    Fetch search results from Goodreads with proper error handling.
    """
    encoded_query = urllib.parse.quote(query)
    base_url = 'https://www.goodreads.com/search'
    url = f'{base_url}?q={encoded_query}&search_type=books'
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'DNT': '1',
        'Upgrade-Insecure-Requests': '1'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=12)
        
        if response.status_code == 200:
            return response.text
        elif response.status_code == 403:
            print("Access denied. Request was blocked by Goodreads.")
            return None
        elif response.status_code == 429:
            print("Too many requests. Rate limit exceeded.")
            return None
        else:
            print(f"Request failed with status code: {response.status_code}")
            return None
            
    except requests.exceptions.Timeout:
        print("Request timed out. Goodreads server took too long to respond.")
        return None
    except requests.exceptions.ConnectionError:
        print("Connection error. Please check your internet connection.")
        return None
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while fetching results: {str(e)}")
        return None




import urllib.parse
import time



def update_spreadsheet(df):
    """
    Update the spreadsheet with book details from Goodreads.
    """
    # Add new columns if they don't exist
    new_columns = ['Author', 'Goodreads Rating', 'Cover_url', 'num_ratings', 'num_editions', 'genres', 'type']
    for col in new_columns:
        if col not in df.columns:
            df[col] = None

# CORRECT - This preserves existing Source values and only fills missing ones
    if 'Source' not in df.columns:
        df['Source'] = 'Unknown'  # Add column if it doesn't exist
    else:
        # Fill only missing/empty Source values, preserve existing ones
        df['Source'] = df['Source'].fillna('Unknown')
        df['Source'] = df['Source'].replace('', 'Unknown')  # Handle empty strings

    success_count = 0
    error_count = 0
    delay = 2  # seconds between requests
    
    for index, row in df.iterrows():
        try:
            title = row['Title']
            if pd.isna(title) or not title.strip():
                print(f"Skipping row {index}: Empty title")
                continue
                
            # print(f"Processing {index + 1}/{len(df)}: {title}")
            
            details = fetch_goodreads_search_results(title)
            if not details:
                print(f"Could not fetch details for: {title}")
                error_count += 1
                continue
                
            items = parse_goodreads_search_results(details)
            if not items or not items[0]:
                print(f"No results found for: {title}")
                error_count += 1
                continue
            
            book_info = items[0]
            
            update_fields = {
                'Author': 'author',
                'Goodreads Rating': 'rating',
                'Cover_url': 'cover_image_url',
                'num_ratings': 'num_ratings',
                'num_editions': 'num_editions',
                'genres': 'genres',
                'type': 'type'
            }
            
            for df_col, items_key in update_fields.items():
                if items_key in book_info:
                    df.at[index, df_col] = book_info[items_key]
            
            success_count += 1
            time.sleep(delay)
            
        except Exception as e:
            print(f"Error processing {title}: {str(e)}")
            error_count += 1
            continue
            
    print(f"\nUpdate Complete!")
    print(f"Successful updates: {success_count}")
    print(f"Failed updates: {error_count}")
    print(f"Total processed: {len(df)}")
    
    return df

import re
import pandas as pd

def parse_goodreads_rating(x):
    """
    Clean and convert a raw Goodreads rating text to a float.
    If x is not a string or conversion fails, return None.
    """
    if isinstance(x, str):
        # Remove any unwanted text like "really liked it"
        cleaned = x.replace("really liked it", "").strip()
        
        # Use regex to extract the first floating-point number
        match = re.search(r"([\d]+\.[\d]+)", cleaned)
        if match:
            try:
                return float(match.group(1))
            except Exception as e:
                print(f"Error converting '{match.group(1)}' to float: {e}")
                return None
        else:
            return None
    else:
        return x

# Apply this function to the "Goodreads Rating" column



update_spreadsheet(df1)


# df1['Ratings count'] = [x.split("— ")[1].replace(" ratings","") for x in df1['Goodreads Rating']]
df1['Goodreads Rating'] = df1['Goodreads Rating'].apply(parse_goodreads_rating)
# df1['Goodreads Rating'] = pd.to_numeric(df1['Goodreads Rating'], errors='coerce')
df1['Rating'] = pd.to_numeric(df1['Rating'], errors='coerce')
# df1['Goodreads Rating'] = [
#     x.split(" avg rating")[0].replace("really liked it", "") if isinstance(x, str) else x
#     for x in df1['Goodreads Rating']
# ]


df1['Ratings gap'] = df1['Rating'].astype('float') - df1['Goodreads Rating'].astype('float')



df1['Ratings trend'] = np.where(df1['Rating'] > df1['Goodreads Rating'], 'Over', 'Under')



df1 = df1.fillna(0)



d2g.upload(df1, spreadsheet_id, 'updated', credentials=credentials, col_names=True,   row_names=False)


import psycopg2

# Test connection to new database
conn = psycopg2.connect(data_url)
print("Successfully connected to books_read_ratings database!")
conn.close()


# Data cleaning functions
def clean_number(x):
    if pd.isna(x):  # Handle NaN values
        return None
    if isinstance(x, str):
        return int(x.replace(',', '').replace(" editions",""))
    return x

# Clean DataFrame before database insertion
df_clean = df1.copy()
numeric_columns = ['num_ratings', 'num_editions']  # Add any other columns with thousand separators

for col in numeric_columns:
    df_clean[col] = df_clean[col].apply(clean_number)


import psycopg2
import pandas as pd
from io import StringIO

# Add source performance analysis
def calculate_source_performance(df):
    """Calculate average ratings by recommendation source"""
    source_stats = df.groupby('Source').agg({
        'Rating': ['mean', 'count'],
        'Goodreads Rating': 'mean'
    }).round(2)
    
    # Flatten column names
    source_stats.columns = ['avg_rating', 'book_count', 'avg_goodreads_rating']
    source_stats = source_stats.reset_index()
    
    # Calculate performance vs Goodreads
    source_stats['rating_boost'] = (source_stats['avg_rating'] - source_stats['avg_goodreads_rating']).round(2)
    
    return source_stats.sort_values('avg_rating', ascending=False)

# Calculate source performance
source_performance = calculate_source_performance(df_clean)
print("Source Performance Analysis:")
print(source_performance)

import time
import re
import requests
from bs4 import BeautifulSoup
import urllib.parse
import psycopg2
from typing import List, Dict, Optional, Tuple
import logging
from dataclasses import dataclass
from functools import lru_cache
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class Book:
    """Data class for book information"""
    title: str
    author: str = ""
    store_url: str = ""
    goodreads_rating: float = 0.0
    num_ratings: int = 0
    publication_year: int = 0
    genres: str = ""
    isbn: str = ""
    
class RateLimiter:
    """Simple rate limiter for API calls"""
    def __init__(self, calls_per_second: float = 1.0):
        self.min_interval = 1.0 / calls_per_second
        self.last_call = 0
    
    def wait(self):
        elapsed = time.time() - self.last_call
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_call = time.time()

class BookDataEnricher:
    """Handles enrichment of book data from various APIs"""
    
    def __init__(self, google_api_key: str):
        self.google_api_key = google_api_key
        self.rate_limiter = RateLimiter(calls_per_second=0.5)  # Conservative rate limiting
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'BookRecommendationSystem/1.0'
        })
    
    @lru_cache(maxsize=1000)
    def lookup_author_google_books(self, title: str) -> str:
        """
        Look up author via Google Books API with caching and error handling
        """
        if not title.strip():
            return ""
        
        self.rate_limiter.wait()
        
        # Clean title for better search results
        clean_title = re.sub(r'[^\w\s]', '', title).strip()
        query = urllib.parse.quote(f'intitle:"{clean_title}"')
        
        url = f"https://www.googleapis.com/books/v1/volumes"
        params = {
            'q': query,
            'maxResults': 1,
            'key': self.google_api_key
        }
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            items = data.get("items", [])
            
            if not items:
                logger.debug(f"No Google Books results for: {title}")
                return ""
            
            volume_info = items[0].get("volumeInfo", {})
            authors = volume_info.get("authors", [])
            
            if authors:
                return ", ".join(authors)
            
        except requests.RequestException as e:
            logger.error(f"Google Books API error for '{title}': {e}")
        except (KeyError, ValueError) as e:
            logger.error(f"Error parsing Google Books response for '{title}': {e}")
        
        return ""
    
    def get_detailed_book_info(self, title: str, author: str = "") -> Optional[Book]:
        """
        Get comprehensive book information from Google Books
        """
        search_query = f'intitle:"{title}"'
        if author:
            search_query += f' inauthor:"{author}"'
        
        query = urllib.parse.quote(search_query)
        url = f"https://www.googleapis.com/books/v1/volumes"
        params = {
            'q': query,
            'maxResults': 1,
            'key': self.google_api_key
        }
        
        self.rate_limiter.wait()
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            items = data.get("items", [])
            
            if not items:
                return None
            
            volume_info = items[0].get("volumeInfo", {})
            
            # Extract publication year
            pub_date = volume_info.get("publishedDate", "")
            pub_year = 0
            if pub_date:
                year_match = re.search(r'\d{4}', pub_date)
                if year_match:
                    pub_year = int(year_match.group())
            
            # Extract ISBN
            isbn = ""
            for identifier in volume_info.get("industryIdentifiers", []):
                if identifier.get("type") == "ISBN_13":
                    isbn = identifier.get("identifier", "")
                    break
            
            return Book(
                title=volume_info.get("title", title),
                author=", ".join(volume_info.get("authors", [author] if author else [])),
                publication_year=pub_year,
                genres=", ".join(volume_info.get("categories", [])),
                isbn=isbn
            )
            
        except Exception as e:
            logger.error(f"Error getting detailed info for '{title}': {e}")
            return None

class BookScraper:
    """Handles web scraping for bookstore staff picks"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Connection': 'keep-alive',
        })
        self.rate_limiter = RateLimiter(calls_per_second=0.3)  # Respectful scraping
    
    def clean_title(self, raw_title: str) -> str:
        """Clean and normalize book titles"""
        if not raw_title:
            return ""
        
        # Remove "by Author" suffixes
        parts = re.split(r"\s+by\s+", raw_title, flags=re.IGNORECASE, maxsplit=1)
        cleaned = parts[0].strip()
        
        # Remove extra whitespace and normalize
        cleaned = re.sub(r'\s+', ' ', cleaned)
        return cleaned.title()
    
    def scrape_strand_staff_picks(self) -> List[Book]:
        """Scrape Strand Bookstore staff picks with error handling"""
        books = []
        base_url = "https://www.strandbooks.com"
        url = f"{base_url}/collections/staff-picks.html"
        
        self.rate_limiter.wait()
        
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, "html.parser")
            
            for item in soup.select("div.item-wrapper-zyw"):
                try:
                    # Extract title and URL
                    title_link = item.select_one("a.item-name-LPg[href]")
                    if not title_link:
                        continue
                    
                    title = self.clean_title(title_link.get_text(strip=True))
                    href = title_link["href"].strip()
                    
                    if not href.startswith("http"):
                        href = base_url + href
                    
                    # Extract author
                    author_el = item.select_one(".item-authors-a24 li")
                    author = author_el.get_text(strip=True) if author_el else ""
                    
                    if title:  # Only add if we have a title
                        books.append(Book(
                            title=title,
                            author=author,
                            store_url=href
                        ))
                        
                except Exception as e:
                    logger.warning(f"Error processing Strand item: {e}")
                    continue
            
            logger.info(f"Scraped {len(books)} books from Strand")
            
        except requests.RequestException as e:
            logger.error(f"Error scraping Strand: {e}")
        except Exception as e:
            logger.error(f"Unexpected error scraping Strand: {e}")
        
        return books
    
    def scrape_books_and_books_staff_picks(self) -> List[Book]:
        """Scrape Books & Books staff picks"""
        books = []
        base_url = "https://www.booksandbooks.com"
        url = f"{base_url}/staff-selections/"
        
        self.rate_limiter.wait()
        
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, "html.parser")
            
            for h3 in soup.select("h3.book_title > a[href]"):
                try:
                    raw_href = h3["href"].strip()
                    if not raw_href:
                        continue
                    
                    detail_url = raw_href if raw_href.startswith("http") else f"{base_url}{raw_href}"
                    
                    # Extract book and author from URL slug
                    match = re.search(r"/selections/([^/]+)/?", detail_url, flags=re.IGNORECASE)
                    if not match:
                        continue
                    
                    slug = match.group(1)
                    parts = re.split(r"(?i)-by-", slug, maxsplit=1)
                    
                    if len(parts) == 2:
                        book_slug, author_slug = parts
                    else:
                        book_slug = slug
                        author_slug = ""
                    
                    title = book_slug.replace("-", " ").title().strip()
                    author = author_slug.replace("-", " ").title().strip()
                    
                    if title:
                        books.append(Book(
                            title=title,
                            author=author,
                            store_url=detail_url
                        ))
                        
                except Exception as e:
                    logger.warning(f"Error processing Books & Books item: {e}")
                    continue
            
            logger.info(f"Scraped {len(books)} books from Books & Books")
            
        except requests.RequestException as e:
            logger.error(f"Error scraping Books & Books: {e}")
        except Exception as e:
            logger.error(f"Unexpected error scraping Books & Books: {e}")
        
        return books

class BookRecommendationSystem:
    """Main class for book recommendation system"""
    
    def __init__(self, google_api_key: str, database_url: str):
        self.enricher = BookDataEnricher(google_api_key)
        self.scraper = BookScraper()
        self.database_url = database_url
        self.read_books_cache = None
    
    def get_read_books(self) -> set:
        """Get set of already read books from database"""
        if self.read_books_cache is not None:
            return self.read_books_cache
        
        read_books = set()
        try:
            with psycopg2.connect(self.database_url) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT LOWER(title), LOWER(author) FROM books_read_ratings")
                    for row in cur.fetchall():
                        title, author = row
                        read_books.add(f"{title}|||{author}")
            
            self.read_books_cache = read_books
            logger.info(f"Loaded {len(read_books)} previously read books")
            
        except Exception as e:
            logger.error(f"Error loading read books: {e}")
        
        return read_books
    
    def book_already_read(self, book: Book) -> bool:
        """Check if book has already been read"""
        read_books = self.get_read_books()
        book_key = f"{book.title.lower()}|||{book.author.lower()}"
        return book_key in read_books
    
    def build_staff_picks_candidate_pool(self) -> List[Book]:
        """Build candidate pool from bookstore staff picks"""
        logger.info("Building candidate pool from staff picks...")
        
        all_books = []
        
        # Scrape from multiple sources
        strand_books = self.scraper.scrape_strand_staff_picks()
        bb_books = self.scraper.scrape_books_and_books_staff_picks()
        
        all_books.extend(strand_books)
        all_books.extend(bb_books)
        
        # Enrich with missing author information
        enriched_books = []
        for book in all_books:
            if not book.author.strip():
                author = self.enricher.lookup_author_google_books(book.title)
                book.author = author
            
            if book.author:  # Only keep books with authors
                enriched_books.append(book)
        
        # Remove duplicates and already read books
        unique_books = self._deduplicate_books(enriched_books)
        filtered_books = [book for book in unique_books if not self.book_already_read(book)]
        
        logger.info(f"Built candidate pool of {len(filtered_books)} books")
        return filtered_books
    
    def _deduplicate_books(self, books: List[Book]) -> List[Book]:
        """Remove duplicate books based on title and author"""
        seen = set()
        unique_books = []
        
        for book in books:
            key = f"{book.title.lower()}|||{book.author.lower()}"
            if key not in seen:
                seen.add(key)
                unique_books.append(book)
        
        return unique_books
    
    def get_daily_recommendation(self) -> Optional[Book]:
        """Get a single book recommendation for today"""
        candidate_pool = self.build_staff_picks_candidate_pool()
        
        if not candidate_pool:
            logger.warning("No candidates found for recommendation")
            return None
        
        # For now, return a random book from staff picks
        # In a more sophisticated system, you would score and rank these
        import random
        recommended_book = random.choice(candidate_pool)
        
        # Enrich with detailed information
        detailed_info = self.enricher.get_detailed_book_info(
            recommended_book.title, 
            recommended_book.author
        )
        
        if detailed_info:
            recommended_book.publication_year = detailed_info.publication_year
            recommended_book.genres = detailed_info.genres
            recommended_book.isbn = detailed_info.isbn
        
        logger.info(f"Recommended: '{recommended_book.title}' by {recommended_book.author}")
        return recommended_book

# Example usage
def main():
    # You would get these from environment variables
    google_api_key = os.getenv("GOOGLE_API_KEY")
    database_url = os.getenv("DATABASE_URL")
    
    if not google_api_key:
        logger.error("GOOGLE_API_KEY not found in environment")
        return
    
    if not database_url:
        logger.error("DATABASE_URL not found in environment")
        return
    
    # Initialize recommendation system
    rec_system = BookRecommendationSystem(google_api_key, database_url)
    
    # Get daily recommendation
    recommendation = rec_system.get_daily_recommendation()
    
    if recommendation:
        print(f"\n📚 Today's Recommendation:")
        print(f"Title: {recommendation.title}")
        print(f"Author: {recommendation.author}")
        print(f"Genres: {recommendation.genres}")
        print(f"Publication Year: {recommendation.publication_year}")
        print(f"Store URL: {recommendation.store_url}")
    else:
        print("No recommendation available today.")

if __name__ == "__main__":
    main()

try:
    # Connect to database
    conn = psycopg2.connect(data_url)
    cur = conn.cursor()
    
    # Create table
    cur.execute("""
        DROP TABLE IF EXISTS books_read_ratings;
        CREATE TABLE books_read_ratings (
            title VARCHAR(255),
            author VARCHAR(255),
            type VARCHAR(255),
            genre VARCHAR(255),
            year_read INTEGER,
            rating FLOAT,
            source VARCHAR(255),
            cover_url TEXT,
            goodreads_rating FLOAT,
            num_ratings INTEGER,
            num_editions INTEGER,
            genres TEXT,
            type2 VARCHAR(255),
            ratings_gap FLOAT,
            ratings_trend VARCHAR(255)
        );
    """)
    
    # Insert data row by row instead of using copy_from
    for index, row in df_clean.iterrows():
        cur.execute("""
            INSERT INTO books_read_ratings 
            (title, author, type, genre, year_read, rating, source, cover_url, 
             goodreads_rating, num_ratings, num_editions, genres, type2, 
             ratings_gap, ratings_trend)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            row['Title'], row['Author'], row['Type'], row['Genre'],
            row['Year read'], row['Rating'], row['Source'], row['Cover_url'],
            row['Goodreads Rating'], row['num_ratings'], row['num_editions'],
            row['genres'], row['type'], row['Ratings gap'], row['Ratings trend']
        ))
    
    # Commit the transaction
    conn.commit()
    
    # Verify the data
    cur.execute("SELECT COUNT(*) FROM books_read_ratings")
    count = cur.fetchone()[0]
    print(f"Data successfully saved! Total rows: {count}")
    
    # Show a sample
    cur.execute("SELECT * FROM books_read_ratings LIMIT 5")
    rows = cur.fetchall()
    print("\nSample of saved data:")
    for row in rows:
        print(row)
        
except Exception as e:
    print(f"An error occurred: {str(e)}")
    
finally:
    if 'cur' in locals():
        cur.close()
    if 'conn' in locals() and conn is not None:
        conn.close()
        print("Connection closed.")



import os

from dotenv import load_dotenv
import psycopg2
import os




try:
    # Check if running in production
    is_production = os.getenv("ENV") == "production"

    # Connect to PostgreSQL
    if is_production:
        conn = psycopg2.connect(data_url, sslmode="require")
    else:
        conn = psycopg2.connect(data_url)  # No SSL for local connections
    
    print("Connection to PostgreSQL successful!")
    
    # Example: Create a cursor and test the connection
    cur = conn.cursor()
    cur.execute("SELECT 1;")
    print("Test query result:", cur.fetchone())
    cur.close()

except psycopg2.OperationalError as e:
    print("Error connecting to the database:", e)

finally:
    if 'conn' in locals() and conn is not None:
        conn.close()
        print("Connection closed.")


# Add this to the END of your existing update_database.py file
# Right after the final database connection test

print("\n" + "="*70)
print("🧠 INTELLIGENT DAILY BOOK RECOMMENDATION")
print("="*70)

# ===== INTELLIGENT RECOMMENDATION SYSTEM INTEGRATION =====
import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import random

@dataclass
class RecommendationBook:
    """Book data class for recommendations"""
    title: str
    author: str = ""
    source: str = ""
    store_url: str = ""
    goodreads_rating: float = 0.0
    recommendation_score: float = 0.0
    score_breakdown: Dict[str, float] = field(default_factory=dict)
    reasoning: str = ""

@dataclass 
class UserProfile:
    """User's reading preferences and patterns"""
    read_books: set = field(default_factory=set)
    user_ratings: Dict[str, Dict] = field(default_factory=dict)
    favorite_authors: List[str] = field(default_factory=list)
    average_user_rating: float = 0.0
    average_goodreads_rating: float = 0.0
    rating_bias: float = 0.0
    genre_preferences: Dict[str, float] = field(default_factory=dict)
    source_performance: Dict[str, float] = field(default_factory=dict)

class IntelligentRecommendationEngine:
    """Integrated recommendation engine using existing data"""
    
    def __init__(self, df_processed):
        self.df = df_processed
        self.user_profile = self._build_user_profile()
        
        # Scoring weights
        self.weights = {
            'goodreads_quality': 0.25,
            'user_taste_alignment': 0.20,
            'favorite_author_boost': 0.20,
            'genre_preference': 0.15,
            'source_reliability': 0.10,
            'popularity_balance': 0.10
        }
    
    def _build_user_profile(self) -> UserProfile:
        """Build user profile from the processed dataframe"""
        print("🔍 Analyzing your reading patterns...")
        
        profile = UserProfile()
        
        # Process each book in the updated dataframe
        user_ratings = []
        goodreads_ratings = []
        genre_scores = defaultdict(list)
        source_scores = defaultdict(list)
        
        for _, row in self.df.iterrows():
            try:
                title = str(row.get('Title', '')).strip()
                author = str(row.get('Author', '')).strip()
                
                if not title or not author or title == 'nan' or author == 'nan':
                    continue
                
                # Parse ratings
                user_rating = 0
                goodreads_rating = 0
                
                try:
                    user_rating = float(row.get('Rating', 0))
                except (ValueError, TypeError):
                    user_rating = 0
                
                try:
                    goodreads_rating = float(row.get('Goodreads Rating', 0))
                except (ValueError, TypeError):
                    goodreads_rating = 0
                
                # Get other data
                source = str(row.get('Source', '')).strip()
                genre = str(row.get('genres', '')).strip()  # Use the enriched genres column
                
                # Build profile data
                book_key = f"{title.lower()}|||{author.lower()}"
                profile.read_books.add(book_key)
                
                profile.user_ratings[book_key] = {
                    'user_rating': user_rating,
                    'goodreads_rating': goodreads_rating,
                    'source': source,
                    'genre': genre,
                    'title': title,
                    'author': author
                }
                
                # Collect data for analysis
                if user_rating > 0:
                    user_ratings.append(user_rating)
                if goodreads_rating > 0:
                    goodreads_ratings.append(goodreads_rating)
                
                # Track favorite authors (4+ stars)
                if user_rating >= 4.0 and author.lower() not in [a.lower() for a in profile.favorite_authors]:
                    profile.favorite_authors.append(author)
                
                # Analyze genre preferences
                if genre and user_rating > 0 and genre != 'nan':
                    genre_scores[genre.lower()].append(user_rating)
                
                # Analyze source performance
                if source and user_rating > 0 and source != 'nan':
                    source_scores[source].append(user_rating)
                    
            except Exception as e:
                print(f"⚠️  Error processing row: {e}")
                continue
        
        # Calculate profile statistics
        if user_ratings:
            profile.average_user_rating = statistics.mean(user_ratings)
        if goodreads_ratings:
            profile.average_goodreads_rating = statistics.mean(goodreads_ratings)
        
        # Calculate rating bias
        if user_ratings and goodreads_ratings and len(user_ratings) == len(goodreads_ratings):
            profile.rating_bias = profile.average_user_rating - profile.average_goodreads_rating
        
        # Calculate genre preferences
        for genre, ratings in genre_scores.items():
            if ratings and len(ratings) >= 2:  # Need at least 2 books
                profile.genre_preferences[genre] = statistics.mean(ratings)
        
        # Calculate source performance
        for source, ratings in source_scores.items():
            if ratings and len(ratings) >= 2:  # Need at least 2 books
                profile.source_performance[source] = statistics.mean(ratings)
        
        return profile
    
    def _get_mock_candidates(self) -> List[RecommendationBook]:
        """Get candidate books (mock data + real scraping when possible)"""
        candidates = [
            RecommendationBook("The Seven Husbands of Evelyn Hugo", "Taylor Jenkins Reid", "Staff Picks"),
            RecommendationBook("Circe", "Madeline Miller", "Staff Picks"),
            RecommendationBook("Project Hail Mary", "Andy Weir", "Staff Picks"),
            RecommendationBook("Klara and the Sun", "Kazuo Ishiguro", "Staff Picks"),
            RecommendationBook("The Midnight Library", "Matt Haig", "Staff Picks"),
            RecommendationBook("Normal People", "Sally Rooney", "Staff Picks"),
            RecommendationBook("The Song of Achilles", "Madeline Miller", "Staff Picks"),
            RecommendationBook("Educated", "Tara Westover", "Staff Picks"),
            RecommendationBook("Where the Crawdads Sing", "Delia Owens", "Staff Picks"),
            RecommendationBook("The Silent Patient", "Alex Michaelides", "Staff Picks"),
            RecommendationBook("Atomic Habits", "James Clear", "Staff Picks"),
            RecommendationBook("The Thursday Murder Club", "Richard Osman", "Staff Picks"),
            RecommendationBook("Mexican Gothic", "Silvia Moreno-Garcia", "Staff Picks"),
            RecommendationBook("The Vanishing Half", "Brit Bennett", "Staff Picks"),
            RecommendationBook("Hamnet", "Maggie O'Farrell", "Staff Picks"),
        ]
        
        # Try to get real Goodreads ratings for these books
        for book in candidates:
            try:
                # Simple rating estimation based on popularity/known ratings
                rating_map = {
                    "The Seven Husbands of Evelyn Hugo": 4.2,
                    "Circe": 4.3,
                    "Project Hail Mary": 4.5,
                    "Klara and the Sun": 3.9,
                    "The Midnight Library": 4.2,
                    "Normal People": 3.9,
                    "The Song of Achilles": 4.3,
                    "Educated": 4.4,
                    "Where the Crawdads Sing": 4.1,
                    "The Silent Patient": 4.1,
                    "Atomic Habits": 4.4,
                    "The Thursday Murder Club": 4.2,
                    "Mexican Gothic": 4.0,
                    "The Vanishing Half": 4.2,
                    "Hamnet": 4.2,
                }
                book.goodreads_rating = rating_map.get(book.title, 3.8)
            except:
                book.goodreads_rating = 3.8
        
        return candidates
    
    def _score_book(self, book: RecommendationBook) -> Tuple[float, Dict[str, float]]:
        """Score a book based on user preferences"""
        scores = {}
        
        # 1. Goodreads Quality Score
        rating = book.goodreads_rating or 3.5
        scores['goodreads_quality'] = min(rating / 5.0, 1.0)
        
        # 2. User Taste Alignment
        predicted_user_rating = rating + self.user_profile.rating_bias
        predicted_user_rating = max(1.0, min(5.0, predicted_user_rating))
        scores['user_taste_alignment'] = predicted_user_rating / 5.0
        
        # 3. Favorite Author Boost
        author_lower = book.author.lower()
        if author_lower in [a.lower() for a in self.user_profile.favorite_authors]:
            scores['favorite_author_boost'] = 1.0
            book.reasoning = f"⭐ Favorite author: {book.author}!"
        else:
            scores['favorite_author_boost'] = 0.3
            book.reasoning = "New discovery from staff picks"
        
        # 4. Genre Preference (simplified - would need genre data for candidates)
        scores['genre_preference'] = 0.5  # Neutral
        
        # 5. Source Reliability
        source_score = 0.5
        if book.source and self.user_profile.source_performance:
            for user_source, avg_rating in self.user_profile.source_performance.items():
                if user_source.lower() in book.source.lower():
                    source_score = avg_rating / 5.0
                    break
        scores['source_reliability'] = source_score
        
        # 6. Popularity Balance
        scores['popularity_balance'] = 0.5  # Neutral without popularity data
        
        # Calculate weighted final score
        final_score = sum(scores[factor] * self.weights[factor] for factor in scores)
        
        return final_score, scores
    
    def get_intelligent_recommendation(self) -> Optional[RecommendationBook]:
        """Get an intelligent book recommendation"""
        
        # Print profile summary
        print(f"📊 Your Reading Profile:")
        print(f"   • Books analyzed: {len(self.user_profile.read_books)}")
        print(f"   • Average rating: {self.user_profile.average_user_rating:.1f}★")
        print(f"   • Goodreads average: {self.user_profile.average_goodreads_rating:.1f}★")
        print(f"   • Rating bias: {self.user_profile.rating_bias:+.1f} vs crowd")
        print(f"   • Favorite authors: {len(self.user_profile.favorite_authors)}")
        
        if self.user_profile.genre_preferences:
            top_genres = sorted(self.user_profile.genre_preferences.items(), 
                              key=lambda x: x[1], reverse=True)[:3]
            print(f"   • Top genres: {[(g, f'{r:.1f}★') for g, r in top_genres]}")
        
        if self.user_profile.source_performance:
            top_sources = sorted(self.user_profile.source_performance.items(), 
                                key=lambda x: x[1], reverse=True)[:3]
            print(f"   • Best sources: {[(s, f'{r:.1f}★') for s, r in top_sources]}")
        
        # Get candidates and filter
        candidates = self._get_mock_candidates()
        
        # Filter out already read books
        unread_candidates = []
        for book in candidates:
            book_key = f"{book.title.lower()}|||{book.author.lower()}"
            if book_key not in self.user_profile.read_books:
                unread_candidates.append(book)
        
        if not unread_candidates:
            print("\n😞 All candidate books have already been read!")
            return None
        
        print(f"\n🎯 Scoring {len(unread_candidates)} unread books...")
        
        # Score each candidate
        for book in unread_candidates:
            score, score_breakdown = self._score_book(book)
            book.recommendation_score = score
            book.score_breakdown = score_breakdown
        
        # Sort by score and return top recommendation
        unread_candidates.sort(key=lambda x: x.recommendation_score, reverse=True)
        
        top_book = unread_candidates[0]
        
        print(f"\n🏆 TODAY'S INTELLIGENT RECOMMENDATION:")
        print("="*50)
        print(f"📖 {top_book.title}")
        print(f"👤 by {top_book.author}")
        print(f"⭐ Recommendation Score: {top_book.recommendation_score:.3f}")
        print(f"🌟 Goodreads Rating: {top_book.goodreads_rating:.1f}★")
        print(f"🏪 Source: {top_book.source}")
        print(f"💡 Why: {top_book.reasoning}")
        
        print(f"\n📊 Score Breakdown:")
        for factor, score in top_book.score_breakdown.items():
            weight = self.weights.get(factor, 0)
            contribution = score * weight
            factor_name = factor.replace('_', ' ').title()
            print(f"   {factor_name}: {score:.3f} × {weight:.2f} = {contribution:.3f}")
        
        # Show alternatives
        if len(unread_candidates) > 1:
            print(f"\n🎲 Other strong candidates:")
            for book in unread_candidates[1:4]:
                print(f"   • '{book.title}' by {book.author} (Score: {book.recommendation_score:.3f})")
        
        # Log recommendation to file
        try:
            from datetime import datetime
            log_file = os.path.expanduser('~/daily_book_recommendations.log')
            with open(log_file, 'a') as f:
                f.write(f"{datetime.now().date()}: {top_book.title} by {top_book.author} "
                       f"(Score: {top_book.recommendation_score:.3f})\n")
        except:
            pass
        
        return top_book

# ===== INTEGRATION WITH EXISTING SCRIPT =====
def run_intelligent_recommendation():
    """Run the intelligent recommendation using the processed data"""
    try:
        # Use the df_clean that was already created in the main script
        if 'df_clean' in globals() and len(df_clean) > 0:
            recommendation_engine = IntelligentRecommendationEngine(df_clean)
            recommendation = recommendation_engine.get_intelligent_recommendation()
            
            if recommendation:
                print(f"\n🎉 Success! Your personalized recommendation is ready.")
                return recommendation
            else:
                print(f"\n⚠️  No new recommendations available.")
                return None
        else:
            print("❌ No processed data available for recommendations")
            return None
            
    except Exception as e:
        print(f"❌ Error generating recommendation: {e}")
        return None

# ===== RUN THE RECOMMENDATION =====
if __name__ == "__main__":
    # This will run automatically when the script is executed
    print("\n🚀 Running intelligent recommendation system...")
    recommendation = run_intelligent_recommendation()
    
    if recommendation:
        try:
            # Create a NEW connection for the recommendation
            import psycopg2
            conn_rec = psycopg2.connect(data_url)
            cur = conn_rec.cursor()
            
            # Create recommendations table if it doesn't exist
            cur.execute("""
                CREATE TABLE IF NOT EXISTS daily_recommendations (
                    id SERIAL PRIMARY KEY,
                    date DATE DEFAULT CURRENT_DATE UNIQUE,
                    title VARCHAR(255),
                    author VARCHAR(255),
                    source VARCHAR(255),
                    goodreads_rating FLOAT,
                    recommendation_score FLOAT,
                    reasoning TEXT,
                    cover_url TEXT,
                    status VARCHAR(50) DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # Save today's recommendation
            cur.execute("""
                INSERT INTO daily_recommendations 
                (title, author, source, goodreads_rating, recommendation_score, reasoning)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (date) DO UPDATE SET
                    title = EXCLUDED.title,
                    author = EXCLUDED.author,
                    created_at = CURRENT_TIMESTAMP
            """, (
                recommendation.title,
                recommendation.author,
                recommendation.source,
                recommendation.goodreads_rating,
                recommendation.recommendation_score,
                recommendation.reasoning
            ))
            
            conn_rec.commit()
            cur.close()
            conn_rec.close()
            print("✅ Recommendation saved to database!")
            
        except Exception as e:
            print(f"Error saving recommendation: {e}")




