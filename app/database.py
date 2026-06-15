import sqlite3
from pathlib import Path

# Database file path relative to the project root
DATABASE = "database/app.db"


def get_db_connection():
    """Connect to SQLite and return a row_factory-enabled connection."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create the application tables and apply lightweight schema updates."""
    db_path = Path(DATABASE)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS politicians (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            party TEXT NOT NULL
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            firebase_uid TEXT UNIQUE,
            email TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS votes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            politician_id INTEGER,
            vote_type TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            user_id INTEGER
        )
        """
    )

    cur.execute("PRAGMA table_info(votes)")
    vote_columns = [row[1] for row in cur.fetchall()]
    if "user_id" not in vote_columns:
        cur.execute("ALTER TABLE votes ADD COLUMN user_id INTEGER")

    conn.commit()
    conn.close()


def seed_politicians():
    """Insert default politicians only when the table is empty."""
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute('SELECT COUNT(*) AS count FROM politicians')
    row = cur.fetchone()
    politician_count = row['count'] if row else 0

    if politician_count == 0:
        cur.executemany(
            'INSERT INTO politicians (name, party) VALUES (?, ?)',
            [
                ('Narendra Modi', 'BJP'),
                ('Rahul Gandhi', 'INC'),
            ]
        )
        conn.commit()

    conn.close()
