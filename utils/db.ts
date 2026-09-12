import { Pool, QueryResult } from 'pg';

// Use SSL for any non-local database (e.g. the hosted RDS/Heroku Postgres
// instance, which now rejects unencrypted connections) regardless of
// NODE_ENV, since `next dev` always runs with NODE_ENV=development.
const isLocalDb = /localhost|127\.0\.0\.1/.test(process.env.DATABASE_URL || '');

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: isLocalDb ? false : {
    rejectUnauthorized: false
  }
});

// Helper function to run queries
export async function query(text: string, params?: any[]): Promise<QueryResult> {
  try {
    return await pool.query(text, params);
  } catch (error) {
    console.error('Database query error', error);
    throw error;
  }
}

export default pool;
