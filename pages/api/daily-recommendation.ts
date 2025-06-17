import type { NextApiRequest, NextApiResponse } from 'next';
import pool from '../../utils/db';

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  try {
    const client = await pool.connect();
    
    // Debug: Check what date the database thinks it is
    const dateCheck = await client.query('SELECT CURRENT_DATE as today');
    console.log('Database current date:', dateCheck.rows[0].today);
    
    // More flexible query - get the most recent recommendation
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
      ORDER BY date DESC
      LIMIT 1
    `);
    
    client.release();
    
    console.log('Query result:', result.rows);
    
    if (result.rows.length > 0) {
      res.status(200).json(result.rows[0]);
    } else {
      res.status(404).json({
        error: 'No recommendation found',
        message: 'Run the update script to generate today\'s recommendation'
      });
    }
  } catch (err) {
    console.error('Error fetching recommendation:', err);
    res.status(500).json({ error: 'Failed to fetch recommendation' });
  }
}
