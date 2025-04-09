

import pandas as pd
import numpy as np

from pandas.io import sql
import json
from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.discovery import build



import os
import gspread
from df2gspread import df2gspread as d2g
from oauth2client.service_account import ServiceAccountCredentials
import openai
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
from openai import OpenAI
from typing import Dict

def get_primary_genre(book_info: Dict[str, str], api_key: str) -> str:
    """
    Use GPT-3.5 (or GPT-4) to determine the most appropriate primary genre based on book information.
    """
    # Create OpenAI client with the API key
    client = OpenAI(api_key=oai_key)

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

if __name__ == "__main__":
    # Prefer using environment variables for API keys
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("Please set the OPENAI_API_KEY environment variable.")

    book_info = {
        "title": "Normal People",
        "author": "Sally Rooney",
        "description": "At school Connell and Marianne pretend not to know each other...",
        "raw_genres": ["Fiction", "Contemporary", "Literary Fiction", "Ireland"],
    }

    genre = get_primary_genre(book_info, api_key)
    print(f"Primary genre: {genre}")



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
            rating_element = entry.find('span', class_='minirating')
            if rating_element:
                rating_text = rating_element.get_text(strip=True)
                rating = rating_text.split('avg rating')[0].strip()
                num_ratings = rating_text.split('—')[1].strip().split(' ')[0]
            else:
                rating = None
                num_ratings = None
            
            # Cover URL extraction
            cover_image_element = entry.find('img', class_='bookCover')
            cover_image_url = cover_image_element['src'] if cover_image_element else None
            
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



update_spreadsheet(df1)


# df1['Ratings count'] = [x.split("— ")[1].replace(" ratings","") for x in df1['Goodreads Rating']]
df1['Goodreads Rating'] = [x.split(" avg rating")[0].replace("really liked it","") for x in df1['Goodreads Rating']]

df1['Ratings gap'] = df1['Rating'].astype('float') - df1['Goodreads Rating'].astype('float')



df1['Ratings trend'] = np.where(df1['Rating'] > df1['Goodreads Rating'], 'Over', 'Under')



df1 = df1.fillna(0)


SCOPES = [
    'https://spreadsheets.google.com/feeds',
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/drive'
]

# Reauthorize with explicit scopes
credentials = ServiceAccountCredentials.from_json_keyfile_name(
    '/Users/paulraymond/Documents/Jupyter and Google Sheets-921203c5db23.json', 
    scopes=SCOPES
)

# Rebuild services
service = build('sheets', 'v4', credentials=credentials)
gc = gspread.authorize(credentials)


d2g.upload(df1, spreadsheet_id, 'updated', credentials=credentials, col_names=True,   row_names=False)


import psycopg2

# Test connection to new database
conn = psycopg2.connect(
    dbname="books_read_ratings",  # Note: using the new database name
    user="postgres",
    password="28cottage",
    host="127.0.0.1"
)
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

# Connection parameters
params = {
    'dbname': 'books_read_ratings',
    'user': 'postgres',
    'password': '28cottage',
    'host': '127.0.0.1',
    'port': '5432'
}

try:
    # Connect to database
    conn = psycopg2.connect(**params)
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
            (title, author, type, genre, year_read, rating, cover_url, 
             goodreads_rating, num_ratings, num_editions, genres, type2, 
             ratings_gap, ratings_trend)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            row['Title'], row['Author'], row['Type'], row['Genre'],
            row['Year read'], row['Rating'], row['Cover_url'],
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
    if 'conn' in locals():
        conn.close()



import os

from dotenv import load_dotenv
import psycopg2
import os

# Load environment variables
load_dotenv()

# Get the DATABASE_URL
DATABASE_URL = os.getenv("DATABASE_URL")


try:
    # Check if running in production
    is_production = os.getenv("ENV") == "production"

    # Connect to PostgreSQL
    if is_production:
        conn = psycopg2.connect(DATABASE_URL, sslmode="require")
    else:
        conn = psycopg2.connect(DATABASE_URL)  # No SSL for local connections
    
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



# Load environment variables
load_dotenv()

# Get the DATABASE_URL
DATABASE_URL = os.getenv("DATABASE_URL")


try:
    conn = psycopg2.connect(DATABASE_URL)
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
            (title, author, type, genre, year_read, rating, cover_url, 
             goodreads_rating, num_ratings, num_editions, genres, type2, 
             ratings_gap, ratings_trend)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            row['Title'], row['Author'], row['Type'], row['Genre'],
            row['Year read'], row['Rating'], row['Cover_url'],
            row['Goodreads Rating'], row['num_ratings'], row['num_editions'],
            row['genres'], row['type'], row['Ratings gap'], row['Ratings trend']
        ))
        
    conn.commit()
    print("Table created successfully!")

    cur.close()
    conn.close()
except Exception as e:
    print("Error:", e)


