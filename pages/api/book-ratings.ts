import type { NextApiRequest, NextApiResponse } from 'next';
import pool from '../../utils/db';

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  try {
    const result = await pool.query(`
      WITH rated_books AS (
        SELECT books.*,
          lower(btrim(regexp_replace(title, '[[:space:]]+', ' ', 'g'))) AS genre_title_key,
          lower(btrim(regexp_replace(split_part(COALESCE(author, ''), ',', 1), '[[:space:]]+', ' ', 'g'))) AS genre_author_key
        FROM books_read_ratings books
      )
      SELECT 
        books.title as "Title",
        books.author as "Author",
        books.type as "Type",
        books.genre as "Genre",
        books.year_read as "Year read",
        books.rating as "Rating",
        books.source as "Source",
        books.goodreads_rating as "Goodreads Rating",
        books.cover_url as "Cover_url",
        books.num_ratings as "num_ratings",
        books.num_editions as "num_editions",
        COALESCE(saved.genre, NULLIF(books.genres, '')) AS genres,
        books.type,
        books.ratings_gap as "Ratings gap",
        books.ratings_trend as "Ratings trend"
      FROM rated_books books
      LEFT JOIN book_genres saved ON saved.title_key = books.genre_title_key
        AND (
          saved.author_key = books.genre_author_key
          OR ((saved.author_key = '' OR books.genre_author_key = '') AND NOT EXISTS (
            SELECT 1 FROM book_genres other
            WHERE other.title_key = saved.title_key AND other.id <> saved.id
          ))
        )
      ORDER BY books.year_read DESC, books.title ASC
    `);
 
    console.log('Database query result:', result.rows);
    
 
    

    res.status(200).json(result.rows);
  } catch (err) {
    console.error('Error:', err);
    res.status(500).json({ error: 'Failed to fetch book data' });
  }
}
