const { Pool } = require('pg');

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: process.env.NODE_ENV === 'production' ? {
    rejectUnauthorized: false
  } : false
});

const migrations = [
  `CREATE TABLE IF NOT EXISTS books (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    rating FLOAT,
    read_date DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
  )`,
  // Add more migration SQL statements as needed
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
