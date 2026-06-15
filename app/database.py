import psycopg2
import psycopg2.extras
import os

DATABASE_URL = os.environ.get("DATABASE_URL")


def get_db_connection():
    """Connect to PostgreSQL and return dict-like rows."""
    conn = psycopg2.connect(
        DATABASE_URL,
        cursor_factory=psycopg2.extras.RealDictCursor
    )
    return conn


def init_db():
    """Create tables for PostgreSQL."""
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS politicians (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            party TEXT NOT NULL
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            firebase_uid TEXT UNIQUE,
            email TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS votes (
            id SERIAL PRIMARY KEY,
            politician_id INTEGER,
            vote_type TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            user_id INTEGER
        )
        """
    )

    conn.commit()
    conn.close()


def seed_politicians():
    """Insert default politicians only if table is empty."""
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) AS count FROM politicians")
    row = cur.fetchone()

    if row["count"] == 0:
        cur.executemany(
            "INSERT INTO politicians (name, party) VALUES (%s, %s)",
            [
                ("Narendra Modi", "BJP"),
                ("Rahul Gandhi", "INC"),
            ],
        )
        conn.commit()

    conn.close()