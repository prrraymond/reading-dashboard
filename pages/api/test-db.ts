import type { NextApiRequest, NextApiResponse } from 'next';
import { query } from '../../utils/db';

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  try {
    // Simple test query - adjust table name if different
    const result = await query('SELECT COUNT(*) FROM books_read_ratings');
    
    res.status(200).json({
      success: true,
      count: result.rows[0].count,
      environment: process.env.NODE_ENV
    });
  } catch (err) {
    console.error('Test connection error:', err);
    res.status(500).json({ 
      success: false, 
      error: 'Database connection failed',
      environment: process.env.NODE_ENV
    });
  }
}
