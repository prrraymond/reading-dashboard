import type { NextApiRequest, NextApiResponse } from 'next';
import pool from '../../utils/db';

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  try {
    const client = await pool.connect();
    const result = await client.query(`
      SELECT 
        title as "Title",
        author as "Author",
        type as "Type",
        genre as "Genre",
        year_read as "Year read",
        rating as "Rating",
        goodreads_rating as "Goodreads Rating",
        cover_url as "Cover_url",
        num_ratings as "num_ratings",
        num_editions as "num_editions",
        genres,
        type,
        ratings_gap as "Ratings gap",
        ratings_trend as "Ratings trend"
      FROM books_read_ratings
      ORDER BY year_read DESC, title ASC
    `);
    console.log('Database query result:', result.rows);
    client.release();
    
 
    

    res.status(200).json(result.rows);
  } catch (err) {
    console.error('Error:', err);
    res.status(500).json({ error: 'Failed to fetch book data' });
  }
}
