"""
database.py
Handles all SQLite operations for the content search bot.
Each deployed bot instance has its own local database file (data.db).
"""

import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "data.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Creates the content table if it doesn't already exist. Safe to call every startup."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS content (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            season TEXT,
            episode TEXT,
            language TEXT,
            link TEXT NOT NULL,
            added_date TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


def add_entry(title: str, season: str, episode: str, language: str, link: str) -> int:
    """Inserts a new content entry. Returns the new row's id."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO content (title, season, episode, language, link, added_date)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (title, season, episode, language, link, datetime.utcnow().isoformat()),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def update_link(entry_id: int, new_link: str) -> bool:
    """Updates the link for an existing entry. Returns True if a row was changed."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE content SET link = ? WHERE id = ?", (new_link, entry_id))
    conn.commit()
    changed = cur.rowcount > 0
    conn.close()
    return changed


def delete_entry(entry_id: int) -> bool:
    """Deletes an entry by id. Returns True if a row was removed."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM content WHERE id = ?", (entry_id,))
    conn.commit()
    deleted = cur.rowcount > 0
    conn.close()
    return deleted


def list_all():
    """Returns every entry, most recently added first. Used by /list for admins."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM content ORDER BY id DESC")
    rows = cur.fetchall()
    conn.close()
    return rows


def _normalize_word(word: str) -> str:
    """
    Strips common season/episode prefixes so queries like 's4', 'season4',
    or 'e5' match stored numeric values like '4' and '5'.
    """
    word = word.lower()
    for prefix in ("season", "s", "episode", "ep", "e"):
        if word.startswith(prefix) and word[len(prefix):].isdigit():
            return word[len(prefix):]
    return word


def search(query: str):
    """
    Simple, dependency-free fuzzy search:
    splits the query into words and returns entries where ALL words
    appear somewhere in the combined title/season/episode/language text.
    This avoids needing an external fuzzy-matching library.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM content")
    rows = cur.fetchall()
    conn.close()

    words = [_normalize_word(w) for w in query.split() if w.strip()]
    if not words:
        return []

    results = []
    for row in rows:
        haystack = " ".join(
            str(row[field] or "") for field in ("title", "season", "episode", "language")
        ).lower()
        if all(word in haystack for word in words):
            results.append(row)

    return results
