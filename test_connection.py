#!/usr/bin/env python3
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "postgres")
DB_SSL = os.getenv("DB_SSL", "false").lower() == "true"

def main():
    print("Testing database connection...")
    print(f"Host: {DB_HOST}")
    print(f"Port: {DB_PORT}")
    print(f"User: {DB_USER}")
    print(f"Database: {DB_NAME}")
    print(f"SSL: {DB_SSL}")
    print()

    try:
        sslmode = "require" if DB_SSL else "disable"
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            dbname=DB_NAME,
            sslmode=sslmode
        )

        print("✅ Connected successfully!")
        print()

        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
        tables = cursor.fetchall()

        if tables:
            print(f"Found {len(tables)} tables:")
            for table in tables:
                print(f"  - {table['table_name']}")
        else:
            print("No tables found in public schema.")

        print()
        print("✅ Database connection test passed!")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"❌ Connection failed: {e}")
        exit(1)

if __name__ == "__main__":
    main()
