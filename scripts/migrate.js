const { Pool } = require('pg');

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: process.env.NODE_ENV === 'production' ? {
    rejectUnauthorized: false
  } : false
});

const migrations = [
  `CREATE TABLE IF NOT EXISTS books_read_ratings (
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
  )`
];

async function runMigrations() {
  const client = await pool.connect();
  try {
    for (const migration of migrations) {
      await client.query(migration);
      console.log('Migration applied successfully');
    }
  } catch (err) {
    console.error('Error running migrations', err);
    process.exit(1);
  } finally {
    client.release();
  }
}

runMigrations().then(() => pool.end());
