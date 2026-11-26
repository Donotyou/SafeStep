import sqlite3
import os

DB_PATH = os.path.join("data", "safepath.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reported_problems (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            problem TEXT NOT NULL,
            description TEXT,          -- <-- اضفنا العمود هنا
            lat REAL NOT NULL,
            lon REAL NOT NULL,
            image_path TEXT,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()
