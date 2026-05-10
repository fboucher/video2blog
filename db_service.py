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
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    with get_db() as conn:
        # 1. Create table if fresh DB
        conn.execute('''CREATE TABLE IF NOT EXISTS video_sync (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            local_filename TEXT UNIQUE NOT NULL,
            video_name TEXT NOT NULL,
            sync_status TEXT NOT NULL DEFAULT 'synced',
            gemini_file_uri TEXT,
            gemini_uploaded_at TIMESTAMP,
            source_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')

        # 2. Detect old Reka schema and migrate
        cols = [row[1] for row in conn.execute("PRAGMA table_info(video_sync)").fetchall()]
        if 'reka_video_id' in cols:
            # Full table rebuild to remove Reka columns and NOT NULL constraint
            conn.execute("ALTER TABLE video_sync RENAME TO video_sync_old")
            conn.execute('''CREATE TABLE video_sync (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                local_filename TEXT UNIQUE NOT NULL,
                video_name TEXT NOT NULL,
                sync_status TEXT NOT NULL DEFAULT 'synced',
                gemini_file_uri TEXT,
                gemini_uploaded_at TIMESTAMP,
                source_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')
            conn.execute('''
                INSERT INTO video_sync (id, local_filename, video_name, sync_status, created_at, updated_at)
                SELECT id, local_filename, video_name, 'synced', created_at, updated_at
                FROM video_sync_old
            ''')
            conn.execute("DROP TABLE video_sync_old")

        # 3. Create indexes (safe to run after migration)
        conn.execute('CREATE INDEX IF NOT EXISTS idx_local_filename ON video_sync(local_filename)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_sync_status ON video_sync(sync_status)')

        # 4. Incremental column migrations (for partial Gemini schema DBs)
        for ddl in [
            'ALTER TABLE video_sync ADD COLUMN source_url TEXT',
            'ALTER TABLE video_sync ADD COLUMN gemini_file_uri TEXT',
            'ALTER TABLE video_sync ADD COLUMN gemini_uploaded_at TIMESTAMP',
        ]:
            try:
                conn.execute(ddl)
            except Exception:
                pass  # Column already exists

        # 5. Index for source_url (after the column is guaranteed to exist)
        conn.execute('CREATE INDEX IF NOT EXISTS idx_source_url ON video_sync(source_url)')

        # 6. Drafts and version history tables
        conn.execute('''CREATE TABLE IF NOT EXISTS drafts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id TEXT NOT NULL,
            video_name TEXT NOT NULL,
            content TEXT NOT NULL,
            transcript TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')

        conn.execute('''CREATE TABLE IF NOT EXISTS draft_versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            draft_id INTEGER NOT NULL REFERENCES drafts(id) ON DELETE CASCADE,
            content TEXT NOT NULL,
            skill_used TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')

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


# ── Drafts ────────────────────────────────────────────────────────────────────

def create_draft(video_id: str, video_name: str, content: str) -> int:
    """
    Insert a new draft and return its id.

    Args:
        video_id: Identifier of the source video (local_filename or URL key).
        video_name: Human-readable video name.
        content: Initial blog post content.

    Returns:
        The auto-assigned draft id.
    """
    with get_db() as conn:
        cursor = conn.execute(
            '''INSERT INTO drafts (video_id, video_name, content)
               VALUES (?, ?, ?)''',
            (video_id, video_name, content),
        )
        conn.commit()
        return cursor.lastrowid


def get_draft(draft_id: int) -> Optional[Dict[str, Any]]:
    """
    Return a draft by id, or None if not found.

    Args:
        draft_id: Primary key of the draft.

    Returns:
        Row dict or None.
    """
    with get_db() as conn:
        row = conn.execute(
            'SELECT * FROM drafts WHERE id = ?',
            (draft_id,),
        ).fetchone()
        return dict(row) if row else None


def get_latest_draft_by_video_id(video_id: str) -> Optional[Dict[str, Any]]:
    """
    Return the most recently updated draft for a video, or None.

    Args:
        video_id: The video identifier (local_filename or URL key).

    Returns:
        Row dict with at minimum 'id', or None if no draft exists.
    """
    with get_db() as conn:
        row = conn.execute(
            'SELECT id FROM drafts WHERE video_id = ? ORDER BY updated_at DESC LIMIT 1',
            (video_id,),
        ).fetchone()
        return dict(row) if row else None


def update_draft(
    draft_id: int,
    content: str,
    transcript: Optional[str] = None,
    skill_used: Optional[str] = None,
) -> None:
    """
    Update draft content (and optionally transcript), then snapshot the new
    content as a new draft_versions row.

    Args:
        draft_id: Primary key of the draft to update.
        content: Replacement blog post content.
        transcript: Optional replacement transcript.
        skill_used: Label for the AI skill that produced the edit, or None for
                    manual edits.
    """
    with get_db() as conn:
        if transcript is not None:
            conn.execute(
                '''UPDATE drafts
                   SET content = ?, transcript = ?, updated_at = ?
                   WHERE id = ?''',
                (content, transcript, datetime.now(), draft_id),
            )
        else:
            conn.execute(
                '''UPDATE drafts
                   SET content = ?, updated_at = ?
                   WHERE id = ?''',
                (content, datetime.now(), draft_id),
            )
        conn.execute(
            '''INSERT INTO draft_versions (draft_id, content, skill_used)
               VALUES (?, ?, ?)''',
            (draft_id, content, skill_used),
        )
        conn.commit()


def list_draft_versions(draft_id: int) -> List[Dict[str, Any]]:
    """
    Return all versions for a draft, newest first.

    Args:
        draft_id: Primary key of the draft.

    Returns:
        List of row dicts ordered by created_at DESC.
    """
    with get_db() as conn:
        rows = conn.execute(
            '''SELECT * FROM draft_versions
               WHERE draft_id = ?
               ORDER BY id DESC''',
            (draft_id,),
        ).fetchall()
        return [dict(row) for row in rows]


def restore_draft_version(draft_id: int, version_id: int) -> None:
    """
    Copy the content of a previous version back to the draft and record the
    restore as a new version entry with skill_used='restore'.

    Args:
        draft_id: Primary key of the draft.
        version_id: Primary key of the draft_versions row to restore from.
    """
    with get_db() as conn:
        row = conn.execute(
            'SELECT content FROM draft_versions WHERE id = ? AND draft_id = ?',
            (version_id, draft_id),
        ).fetchone()
        if row is None:
            raise ValueError(
                f"Version {version_id} not found for draft {draft_id}"
            )
        content = row["content"]
        conn.execute(
            'UPDATE drafts SET content = ?, updated_at = ? WHERE id = ?',
            (content, datetime.now(), draft_id),
        )
        conn.execute(
            '''INSERT INTO draft_versions (draft_id, content, skill_used)
               VALUES (?, ?, 'restore')''',
            (draft_id, content),
        )
        conn.commit()
