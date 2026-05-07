"""
Tests for db_service.py — Issue #22 acceptance criteria.

All tests use an in-memory SQLite database so no filesystem side-effects occur.
The fixture patches db_service.get_db and os.makedirs to stay fully in-memory.
"""

import sqlite3
import pytest
from contextlib import contextmanager
from unittest.mock import patch
from datetime import datetime

import db_service


# ── Fixture ───────────────────────────────────────────────────────────────────

@pytest.fixture()
def mem_db():
    """
    Provide an isolated in-memory SQLite connection with the db_service schema
    applied.  Patches db_service.get_db so every call inside db_service uses
    this same in-memory connection instead of the real DB_PATH file.
    """
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row

    @contextmanager
    def patched_get_db():
        yield conn

    with patch.object(db_service, "get_db", patched_get_db), \
         patch("os.makedirs"):
        db_service.init_db()
        yield conn

    conn.close()


def _get_column_names(conn, table="video_sync"):
    """Return list of column names for *table*."""
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return [row["name"] for row in rows]


# ── Schema: Reka columns must be gone ────────────────────────────────────────

def test_no_reka_columns_in_schema(mem_db):
    """After init_db, no Reka-era columns should exist in video_sync."""
    columns = _get_column_names(mem_db)
    reka_columns = {"reka_video_id", "reka_url", "reka_indexing_status"}
    present = reka_columns & set(columns)
    assert not present, (
        f"Reka columns still present in schema: {present}. "
        "Remove them as part of the Gemini migration."
    )


# ── Schema: Gemini columns must exist ────────────────────────────────────────

def test_gemini_columns_exist_in_schema(mem_db):
    """After init_db, gemini_file_uri and gemini_uploaded_at must be columns."""
    columns = _get_column_names(mem_db)
    assert "gemini_file_uri" in columns, (
        "'gemini_file_uri' column is missing from video_sync schema."
    )
    assert "gemini_uploaded_at" in columns, (
        "'gemini_uploaded_at' column is missing from video_sync schema."
    )


# ── update_gemini_upload ──────────────────────────────────────────────────────

def test_update_gemini_upload_stores_uri_and_timestamp(mem_db):
    """
    update_gemini_upload should persist the file URI and upload timestamp
    for the given filename.
    """
    # First, insert a base record so there's something to update.
    mem_db.execute(
        "INSERT INTO video_sync (local_filename, video_name) VALUES (?, ?)",
        ("talk.mp4", "My Talk"),
    )
    mem_db.commit()

    uri = "https://generativelanguage.googleapis.com/v1/files/xyz789"
    ts = datetime(2026, 5, 7, 12, 0, 0)

    db_service.update_gemini_upload("talk.mp4", uri, ts)

    row = mem_db.execute(
        "SELECT gemini_file_uri, gemini_uploaded_at FROM video_sync WHERE local_filename = ?",
        ("talk.mp4",),
    ).fetchone()

    assert row is not None, "Row not found after update_gemini_upload"
    assert row["gemini_file_uri"] == uri
    # Timestamp may be stored as string; compare as string prefix for flexibility.
    assert str(ts.date()) in str(row["gemini_uploaded_at"])


# ── get_gemini_file_info ──────────────────────────────────────────────────────

def test_get_gemini_file_info_returns_none_when_not_set(mem_db):
    """get_gemini_file_info should return None for an unknown filename."""
    result = db_service.get_gemini_file_info("nonexistent.mp4")
    assert result is None


def test_get_gemini_file_info_returns_dict_when_set(mem_db):
    """
    get_gemini_file_info should return a dict with 'gemini_file_uri' and
    'gemini_uploaded_at' when the file has been uploaded to Gemini.
    """
    mem_db.execute(
        "INSERT INTO video_sync (local_filename, video_name, gemini_file_uri, gemini_uploaded_at)"
        " VALUES (?, ?, ?, ?)",
        ("keynote.mp4", "Keynote 2026",
         "https://generativelanguage.googleapis.com/v1/files/kn2026",
         "2026-05-07 12:00:00"),
    )
    mem_db.commit()

    result = db_service.get_gemini_file_info("keynote.mp4")

    assert result is not None, "Expected a dict, got None"
    assert isinstance(result, dict)
    assert result["uri"] == "https://generativelanguage.googleapis.com/v1/files/kn2026"
    assert result["uploaded_at"] is not None
