import pg from 'pg';
import mysql from 'mysql2/promise';
import fs from 'fs';

const envContent = fs.readFileSync('.env', 'utf-8');
const env: Record<string, string> = {};
envContent.split('\n').forEach(line => {
  const [key, value] = line.split('=');
  if (key && value) {
    env[key.trim()] = value.trim();
  }
});

const DB_TYPE = env.DB_TYPE || 'mysql';
const DB_CONFIG = {
  host: env.DB_HOST || 'localhost',
  port: parseInt(env.DB_PORT || (DB_TYPE === 'postgres' ? '5432' : '3306')),
  user: env.DB_USER || 'root',
  password: env.DB_PASSWORD || 'yj1234',
  database: env.DB_NAME || 'text2sql_demo',
  ssl: env.DB_SSL === 'true' ? { rejectUnauthorized: false } : undefined,
};

async function testPostgres() {
  console.log('Testing PostgreSQL connection...');
  console.log('Config:', { ...DB_CONFIG, password: '***' });
  const pool = new pg.Pool(DB_CONFIG);
  const client = await pool.connect();
  try {
    const result = await client.query('SELECT COUNT(*) FROM products');
    console.log('\n✅ Connection successful!');
    console.log(`Number of products in database: ${result.rows[0].count}`);
    const tables = await client.query(`SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'`);
    console.log('\nTables found:');
    tables.rows.forEach(row => console.log(`  - ${row.table_name}`));
  } catch (error) {
    console.error('\n❌ Connection failed:', (error as Error).message);
    throw error;
  } finally {
    client.release();
    await pool.end();
  }
}

async function testMySQL() {
  console.log('Testing MySQL connection...');
  console.log('Config:', { ...DB_CONFIG, password: '***' });
  const connection = await mysql.createConnection(DB_CONFIG);
  try {
    const [rows] = await connection.query('SELECT COUNT(*) as count FROM products');
    console.log('\n✅ Connection successful!');
    console.log(`Number of products in database: ${(rows as any)[0].count}`);
    const [tables] = await connection.query(`SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA = ?`, [DB_CONFIG.database]);
    console.log('\nTables found:');
    (tables as any).forEach((row: any) => console.log(`  - ${row.TABLE_NAME}`));
  } catch (error) {
    console.error('\n❌ Connection failed:', (error as Error).message);
    throw error;
  } finally {
    await connection.end();
  }
}

if (DB_TYPE === 'postgres' || DB_TYPE === 'supabase') {
  testPostgres();
} else {
  testMySQL();
}
