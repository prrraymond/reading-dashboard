import type { NextApiRequest, NextApiResponse } from 'next';
import pool from '../../utils/db';

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  try {
    const client = await pool.connect();
    
    // Fetch today's recommendation from the daily_recommendations table
    const result = await client.query(`
      SELECT 
        title,
        author,
        source,
        goodreads_rating,
        recommendation_score,
        reasoning,
        date,
        status,
        cover_url
      FROM daily_recommendations
      WHERE date = CURRENT_DATE
      ORDER BY created_at DESC
      LIMIT 1
    `);
    
    client.release();
    
    if (result.rows.length > 0) {
      res.status(200).json(result.rows[0]);
    } else {
      // Return a default/fallback recommendation if none exists for today
      res.status(200).json({
        title: "No recommendation available",
        author: "",
        source: "",
        goodreads_rating: 0,
        recommendation_score: 0,
        reasoning: "Run the update script to generate today's recommendation",
        status: "none"
      });
    }
  } catch (err) {
    console.error('Error fetching recommendation:', err);
    res.status(500).json({ error: 'Failed to fetch recommendation' });
  }
}