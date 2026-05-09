"""
Video database service using SQLite.

This module manages local video metadata and Gemini file upload tracking.
"""

import sqlite3
import os
from typing import Optional, Dict, List, Any
from contextlib import contextmanager
from datetime import datetime

# Database path - will be in /app/data in container
DB_PATH = os.environ.get('DB_PATH', '/app/data/video_sync.db')


@contextmanager
def get_db():
    """Context manager for database connections."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Return dict-like rows
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    """Initialize database and create tables if they don't exist."""
    # Ensure directory exists
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    with get_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS video_sync (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                local_filename TEXT UNIQUE NOT NULL,
                video_name TEXT NOT NULL,
                sync_status TEXT NOT NULL DEFAULT 'synced',
                gemini_file_uri TEXT,
                gemini_uploaded_at TIMESTAMP,
                source_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_local_filename ON video_sync(local_filename)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_sync_status ON video_sync(sync_status)')
        # Migrate existing databases that lack the source_url column
        try:
            conn.execute('ALTER TABLE video_sync ADD COLUMN source_url TEXT')
        except Exception:
            pass  # Column already exists
        conn.execute('CREATE INDEX IF NOT EXISTS idx_source_url ON video_sync(source_url)')
        conn.commit()


def add_sync(
    local_filename: str,
    video_name: str,
    sync_status: str = 'synced',
    source_url: Optional[str] = None,
    **_ignored
) -> bool:
    """
    Add or update a video record.

    Args:
        local_filename: Filename in /app/uploads/ (or a pseudo-filename for URL videos).
        video_name: Human-readable video name.
        sync_status: synced, downloading, uploading.
        source_url: Original source URL for URL-based videos (no local file).

    Returns:
        True if successful, False otherwise
    """
    with get_db() as conn:
        try:
            conn.execute('''
                INSERT OR REPLACE INTO video_sync
                (local_filename, video_name, sync_status, source_url, updated_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (local_filename, video_name, sync_status, source_url, datetime.now()))
            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Database error in add_sync: {e}")
            return False


def get_sync_by_filename(filename: str) -> Optional[Dict[str, Any]]:
    """Get sync info by local filename."""
    with get_db() as conn:
        row = conn.execute(
            'SELECT * FROM video_sync WHERE local_filename = ?',
            (filename,)
        ).fetchone()
        return dict(row) if row else None


def list_all_syncs() -> List[Dict[str, Any]]:
    """Get all sync records ordered by most recent first."""
    with get_db() as conn:
        rows = conn.execute('SELECT * FROM video_sync ORDER BY updated_at DESC').fetchall()
        return [dict(row) for row in rows]


def update_gemini_upload(filename: str, uri: str, timestamp: str) -> None:
    """
    Record a successful Gemini Files API upload against a local video.

    Args:
        filename: Local filename used as the table key.
        uri: Gemini file URI returned by the Files API.
        timestamp: ISO-8601 timestamp of when the upload completed.

    Raises:
        sqlite3.Error: On database failure.
    """
    with get_db() as conn:
        conn.execute(
            '''UPDATE video_sync
               SET gemini_file_uri = ?, gemini_uploaded_at = ?, updated_at = ?
               WHERE local_filename = ?''',
            (uri, timestamp, datetime.now(), filename)
        )
        conn.commit()


def get_gemini_file_info(filename: str) -> Optional[Dict[str, str]]:
    """
    Return Gemini upload metadata for a local video, or None if not uploaded.

    Args:
        filename: Local filename to look up.

    Returns:
        {"uri": str, "uploaded_at": str} or None.
    """
    with get_db() as conn:
        row = conn.execute(
            'SELECT gemini_file_uri, gemini_uploaded_at FROM video_sync WHERE local_filename = ?',
            (filename,)
        ).fetchone()
        if row and row["gemini_file_uri"]:
            return {"uri": row["gemini_file_uri"], "uploaded_at": row["gemini_uploaded_at"]}
        return None


def delete_sync_by_filename(filename: str) -> bool:
    """Delete sync record by local filename."""
    with get_db() as conn:
        try:
            conn.execute('DELETE FROM video_sync WHERE local_filename = ?', (filename,))
            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Database error in delete_sync_by_filename: {e}")
            return False


def check_duplicate(local_filename: Optional[str] = None) -> Dict[str, Any]:
    """
    Check if a video already exists in the sync table.

    Args:
        local_filename: Optional local filename to check.

    Returns:
        {"is_duplicate": bool, "message": str, "existing_record": dict} or
        {"is_duplicate": False}
    """
    with get_db() as conn:
        if local_filename:
            existing = conn.execute(
                'SELECT * FROM video_sync WHERE local_filename = ?',
                (local_filename,)
            ).fetchone()
            if existing:
                return {
                    'is_duplicate': True,
                    'message': f'This local file is already synced: {existing["video_name"]}. Delete it to continue.',
                    'existing_record': dict(existing)
                }

        return {'is_duplicate': False}


def convert_url_video_to_local(url_filename: str, local_filename: str) -> None:
    """Update a URL-based video record to reflect a local download.

    Args:
        url_filename: The pseudo-filename (e.g. "url-<hash>") stored in DB.
        local_filename: The real local filename after yt-dlp download.
    """
    with get_db() as conn:
        conn.execute(
            "UPDATE video_sync SET local_filename = ? WHERE local_filename = ?",
            (local_filename, url_filename)
        )
        conn.commit()


def get_video_by_url(url: str) -> Optional[Dict[str, Any]]:
    """
    Return the video_sync record for a URL-based video, or None if not found.

    Args:
        url: The original source URL used during upload.

    Returns:
        Row dict or None.
    """
    with get_db() as conn:
        row = conn.execute(
            'SELECT * FROM video_sync WHERE source_url = ?',
            (url,)
        ).fetchone()
        return dict(row) if row else None
