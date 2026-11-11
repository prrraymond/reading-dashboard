import type { NextApiRequest, NextApiResponse } from 'next';
import pool from '../../utils/db';

async function findCover(title: string, author: string): Promise<string | null> {
  if (process.env.GOOGLE_API_KEY) {
    const query = new URLSearchParams({
      q: `intitle:${title}${author ? ` inauthor:${author}` : ''}`,
      maxResults: '1',
      key: process.env.GOOGLE_API_KEY,
    });
    try {
      const response = await fetch(`https://www.googleapis.com/books/v1/volumes?${query}`, {
        signal: AbortSignal.timeout(5000),
      });
      if (response.ok) {
        const data = await response.json();
        const images = data.items?.[0]?.volumeInfo?.imageLinks;
        const cover = images?.medium || images?.thumbnail || images?.smallThumbnail;
        if (typeof cover === 'string') {
          const url = new URL(cover);
          if (['books.google.com', 'books.googleusercontent.com'].includes(url.hostname)) {
            url.protocol = 'https:';
            return url.toString();
          }
        }
      }
    } catch {
      // Continue with Open Library when Google Books is unavailable.
    }
  }

  const params = new URLSearchParams({ title, fields: 'cover_i', limit: '1' });
  if (author) params.set('author', author);
  const response = await fetch(`https://openlibrary.org/search.json?${params}`, {
    headers: { 'User-Agent': 'BookRatingsDashboard/1.0 (https://book-ratings-dash-f20755edd755.herokuapp.com)' },
    signal: AbortSignal.timeout(10000),
  });
  if (!response.ok) throw new Error('Cover lookup failed');
  const data = await response.json();
  const coverId = data.docs?.[0]?.cover_i;
  return Number.isSafeInteger(coverId) && coverId > 0
    ? `https://covers.openlibrary.org/b/id/${coverId}-L.jpg?default=false`
    : null;
}

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'GET') {
    res.setHeader('Allow', 'GET');
    res.status(405).end();
    return;
  }

  const { title, author } = req.query;
  if (typeof title !== 'string' || !title.trim() || title.length > 300 ||
      (author !== undefined && (typeof author !== 'string' || author.length > 200))) {
    res.status(400).json({ error: 'A book title is required.' });
    return;
  }

  try {
    const result = await pool.query(`
      SELECT cover_url FROM books_read_ratings WHERE title = $1 AND cover_url <> ''
      UNION ALL
      SELECT cover_url FROM daily_recommendations WHERE title = $1 AND cover_url <> ''
      LIMIT 1
    `, [title.trim()]);
    const refresh = req.query.refresh === '1';
    const storedCover = refresh ? null : result.rows[0]?.cover_url;
    const cover = storedCover || await findCover(title.trim(), typeof author === 'string' ? author.trim() : '');
    if (!cover) {
      res.setHeader('Cache-Control', 'public, max-age=3600');
      res.status(404).end();
      return;
    }

    if (!storedCover) {
      await pool.query(`
        UPDATE books_read_ratings SET cover_url = $1
        WHERE title = $2 AND (cover_url IS NULL OR cover_url = '' OR $3)
      `, [cover, title.trim(), refresh]);
      await pool.query(`
        UPDATE daily_recommendations SET cover_url = $1
        WHERE title = $2 AND (cover_url IS NULL OR cover_url = '' OR $3)
      `, [cover, title.trim(), refresh]);
    }

    res.setHeader('Cache-Control', 'public, max-age=86400, stale-while-revalidate=604800');
    res.redirect(302, cover);
  } catch {
    res.status(502).end();
  }
}
