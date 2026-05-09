"""
Tests for drafts & draft_versions DB functions — Issue #13.

All tests run against an isolated in-memory SQLite database using the same
fixture pattern as test_db_service.py.
"""

import sqlite3
import pytest
from contextlib import contextmanager
from unittest.mock import patch

import db_service


# ── Fixture ───────────────────────────────────────────────────────────────────

@pytest.fixture()
def mem_db():
    """
    In-memory SQLite connection with the full db_service schema applied.
    Patches db_service.get_db so every db_service call uses this connection.
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


# ── Schema ────────────────────────────────────────────────────────────────────

def test_drafts_table_exists(mem_db):
    """init_db() must create the drafts table."""
    rows = mem_db.execute("PRAGMA table_info(drafts)").fetchall()
    names = [r["name"] for r in rows]
    for col in ("id", "video_id", "video_name", "content", "transcript",
                "created_at", "updated_at"):
        assert col in names, f"Column '{col}' missing from drafts table"


def test_draft_versions_table_exists(mem_db):
    """init_db() must create the draft_versions table."""
    rows = mem_db.execute("PRAGMA table_info(draft_versions)").fetchall()
    names = [r["name"] for r in rows]
    for col in ("id", "draft_id", "content", "skill_used", "created_at"):
        assert col in names, f"Column '{col}' missing from draft_versions table"


# ── create_draft ──────────────────────────────────────────────────────────────

def test_create_draft_returns_id(mem_db):
    """create_draft() should return a positive integer id."""
    draft_id = db_service.create_draft("vid-001", "My Video", "Hello world")
    assert isinstance(draft_id, int)
    assert draft_id > 0


def test_create_draft_persists_row(mem_db):
    """create_draft() should write the row to the database."""
    db_service.create_draft("vid-001", "My Video", "Hello world")
    row = mem_db.execute("SELECT * FROM drafts WHERE video_id = 'vid-001'").fetchone()
    assert row is not None
    assert row["video_name"] == "My Video"
    assert row["content"] == "Hello world"
    assert row["transcript"] is None


# ── get_draft ─────────────────────────────────────────────────────────────────

def test_get_draft_returns_dict(mem_db):
    """get_draft() should return a dict for an existing draft."""
    draft_id = db_service.create_draft("vid-002", "Talk", "Draft content")
    result = db_service.get_draft(draft_id)
    assert isinstance(result, dict)
    assert result["id"] == draft_id
    assert result["content"] == "Draft content"


def test_get_draft_returns_none_for_missing(mem_db):
    """get_draft() should return None when the id does not exist."""
    result = db_service.get_draft(99999)
    assert result is None


# ── update_draft ──────────────────────────────────────────────────────────────

def test_update_draft_changes_content(mem_db):
    """update_draft() should replace the draft content."""
    draft_id = db_service.create_draft("vid-003", "Video", "Original")
    db_service.update_draft(draft_id, "Updated content")
    result = db_service.get_draft(draft_id)
    assert result["content"] == "Updated content"


def test_update_draft_creates_version_entry(mem_db):
    """update_draft() must insert a row in draft_versions."""
    draft_id = db_service.create_draft("vid-003", "Video", "Original")
    db_service.update_draft(draft_id, "v2")
    versions = mem_db.execute(
        "SELECT * FROM draft_versions WHERE draft_id = ?", (draft_id,)
    ).fetchall()
    assert len(versions) == 1
    assert versions[0]["content"] == "v2"
    assert versions[0]["skill_used"] is None  # manual edit


def test_update_draft_with_transcript(mem_db):
    """update_draft() should persist transcript when provided."""
    draft_id = db_service.create_draft("vid-004", "Video", "Content")
    db_service.update_draft(draft_id, "New content", transcript="Speaker said hi")
    result = db_service.get_draft(draft_id)
    assert result["transcript"] == "Speaker said hi"


def test_update_draft_with_skill_used(mem_db):
    """update_draft() should record skill_used in draft_versions."""
    draft_id = db_service.create_draft("vid-005", "Video", "Content")
    db_service.update_draft(draft_id, "AI edit", skill_used="summarize")
    version = mem_db.execute(
        "SELECT skill_used FROM draft_versions WHERE draft_id = ?", (draft_id,)
    ).fetchone()
    assert version["skill_used"] == "summarize"


# ── list_draft_versions ───────────────────────────────────────────────────────

def test_list_draft_versions_returns_newest_first(mem_db):
    """list_draft_versions() should return versions ordered newest-first."""
    draft_id = db_service.create_draft("vid-006", "Video", "v1")
    db_service.update_draft(draft_id, "v2")
    db_service.update_draft(draft_id, "v3")
    versions = db_service.list_draft_versions(draft_id)
    assert len(versions) == 2
    assert versions[0]["content"] == "v3"
    assert versions[1]["content"] == "v2"


def test_list_draft_versions_empty_for_untouched_draft(mem_db):
    """A freshly created draft should have no versions."""
    draft_id = db_service.create_draft("vid-007", "Video", "Content")
    versions = db_service.list_draft_versions(draft_id)
    assert versions == []


# ── restore_draft_version ─────────────────────────────────────────────────────

def test_restore_draft_version_restores_content(mem_db):
    """restore_draft_version() should set draft content to the chosen version."""
    draft_id = db_service.create_draft("vid-008", "Video", "Original")
    db_service.update_draft(draft_id, "Edit 1")
    versions = db_service.list_draft_versions(draft_id)
    version_id = versions[0]["id"]

    db_service.update_draft(draft_id, "Edit 2")
    db_service.restore_draft_version(draft_id, version_id)

    result = db_service.get_draft(draft_id)
    assert result["content"] == "Edit 1"


def test_restore_creates_new_version_entry(mem_db):
    """restore_draft_version() must add a new draft_versions row with skill_used='restore'."""
    draft_id = db_service.create_draft("vid-009", "Video", "Original")
    db_service.update_draft(draft_id, "Edit 1")
    versions_before = db_service.list_draft_versions(draft_id)
    version_id = versions_before[0]["id"]

    db_service.restore_draft_version(draft_id, version_id)

    versions_after = db_service.list_draft_versions(draft_id)
    assert len(versions_after) == len(versions_before) + 1
    assert versions_after[0]["skill_used"] == "restore"


def test_restore_raises_for_invalid_version(mem_db):
    """restore_draft_version() should raise ValueError for unknown version_id."""
    draft_id = db_service.create_draft("vid-010", "Video", "Content")
    with pytest.raises(ValueError):
        db_service.restore_draft_version(draft_id, 99999)
