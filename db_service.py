"""
Video sync database service using SQLite.

This module manages the synchronization mapping between Reka videos and local files.
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
                reka_video_id TEXT UNIQUE NOT NULL,
                local_filename TEXT UNIQUE NOT NULL,
                video_name TEXT NOT NULL,
                reka_url TEXT,
                sync_status TEXT NOT NULL DEFAULT 'synced',
                reka_indexing_status TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_reka_video_id ON video_sync(reka_video_id)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_local_filename ON video_sync(local_filename)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_sync_status ON video_sync(sync_status)')
        conn.commit()


def add_sync(
    reka_video_id: str,
    local_filename: str,
    video_name: str,
    reka_url: Optional[str] = None,
    reka_indexing_status: Optional[str] = None,
    sync_status: str = 'synced'
) -> bool:
    """
    Add or update video sync record.
    
    Args:
        reka_video_id: UUID from Reka API
        local_filename: Filename in /app/uploads/
        video_name: Human-readable video name
        reka_url: CDN URL for downloading
        reka_indexing_status: indexed, indexing, failed
        sync_status: synced, downloading, uploading
        
    Returns:
        True if successful, False otherwise
    """
    with get_db() as conn:
        try:
            conn.execute('''
                INSERT OR REPLACE INTO video_sync 
                (reka_video_id, local_filename, video_name, reka_url, sync_status, reka_indexing_status, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (reka_video_id, local_filename, video_name, reka_url, sync_status, reka_indexing_status, datetime.now()))
            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Database error in add_sync: {e}")
            return False


def get_sync_by_reka_id(reka_video_id: str) -> Optional[Dict[str, Any]]:
    """Get sync info by Reka video ID."""
    with get_db() as conn:
        row = conn.execute(
            'SELECT * FROM video_sync WHERE reka_video_id = ?',
            (reka_video_id,)
        ).fetchone()
        return dict(row) if row else None


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


def update_reka_indexing_status(reka_video_id: str, status: str) -> bool:
    """Update indexing status for a Reka video."""
    with get_db() as conn:
        try:
            conn.execute(
                'UPDATE video_sync SET reka_indexing_status = ?, updated_at = ? WHERE reka_video_id = ?',
                (status, datetime.now(), reka_video_id)
            )
            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Database error in update_reka_indexing_status: {e}")
            return False


def delete_sync_by_reka_id(reka_video_id: str) -> bool:
    """Delete sync record by Reka video ID."""
    with get_db() as conn:
        try:
            conn.execute('DELETE FROM video_sync WHERE reka_video_id = ?', (reka_video_id,))
            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Database error in delete_sync_by_reka_id: {e}")
            return False


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


def check_duplicate(reka_video_id: Optional[str] = None, local_filename: Optional[str] = None) -> Dict[str, Any]:
    """
    Check if video already exists in sync table.
    
    Args:
        reka_video_id: Optional Reka video ID to check
        local_filename: Optional local filename to check
        
    Returns:
        {
            "is_duplicate": bool,
            "message": str (if duplicate),
            "existing_record": dict (if duplicate)
        }
    """
    with get_db() as conn:
        if reka_video_id:
            existing = conn.execute(
                'SELECT * FROM video_sync WHERE reka_video_id = ?',
                (reka_video_id,)
            ).fetchone()
            if existing:
                return {
                    'is_duplicate': True,
                    'message': f'This Reka video is already synced with local file: {existing["local_filename"]}. Delete one to continue.',
                    'existing_record': dict(existing)
                }
        
        if local_filename:
            existing = conn.execute(
                'SELECT * FROM video_sync WHERE local_filename = ?',
                (local_filename,)
            ).fetchone()
            if existing:
                return {
                    'is_duplicate': True,
                    'message': f'This local file is already synced with Reka video: {existing["video_name"]}. Delete one to continue.',
                    'existing_record': dict(existing)
                }
        
        return {'is_duplicate': False}
