"""
Integration tests for editing routes — Issue #14 acceptance criteria.

Uses Flask test client with an in-memory SQLite database.
Routes tested:
  POST /editing/drafts      → 201 + {draft_id}
  GET  /editing/drafts/<id> → draft dict
  PUT  /editing/drafts/<id> → updates content + creates version
  GET  /editor?draft_id=<id>→ renders editor.html (400 when draft_id absent)

Tests are marked skip until the #14 implementation lands.
"""

import sqlite3
import pytest
from contextlib import contextmanager
from unittest.mock import patch

import db_service


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def mem_db():
    """In-memory SQLite with full db_service schema. Patches db_service.get_db."""
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


@pytest.fixture()
def client(mem_db):
    """Flask test client wired to the in-memory DB."""
    from web_app import app
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ── POST /editing/drafts ──────────────────────────────────────────────────────

@pytest.mark.skip(reason="Pending #14 implementation")
def test_post_editing_drafts_returns_201(client):
    """POST /editing/drafts with valid payload returns 201 and a draft_id."""
    resp = client.post(
        "/editing/drafts",
        json={
            "video_id": "vid-001",
            "video_name": "My Talk",
            "content": "# Blog\n\nHello world.",
        },
    )
    assert resp.status_code == 201
    data = resp.get_json()
    assert "draft_id" in data, "Response must include 'draft_id'"
    assert isinstance(data["draft_id"], int)


@pytest.mark.skip(reason="Pending #14 implementation")
def test_post_editing_drafts_missing_fields_returns_400(client):
    """POST /editing/drafts without required fields returns 400."""
    resp = client.post("/editing/drafts", json={})
    assert resp.status_code == 400


# ── GET /editing/drafts/<draft_id> ────────────────────────────────────────────

@pytest.mark.skip(reason="Pending #14 implementation")
def test_get_editing_draft_returns_draft_dict(client):
    """GET /editing/drafts/<id> returns the draft as a JSON dict."""
    # Create a draft first via the API
    post_resp = client.post(
        "/editing/drafts",
        json={"video_id": "vid-1", "video_name": "Talk", "content": "Hello."},
    )
    draft_id = post_resp.get_json()["draft_id"]

    get_resp = client.get(f"/editing/drafts/{draft_id}")
    assert get_resp.status_code == 200
    data = get_resp.get_json()
    assert data["id"] == draft_id
    assert data["content"] == "Hello."


@pytest.mark.skip(reason="Pending #14 implementation")
def test_get_editing_draft_unknown_id_returns_404(client):
    """GET /editing/drafts/<id> for non-existent draft returns 404."""
    resp = client.get("/editing/drafts/99999")
    assert resp.status_code == 404


# ── PUT /editing/drafts/<draft_id> ────────────────────────────────────────────

@pytest.mark.skip(reason="Pending #14 implementation")
def test_put_editing_draft_updates_content(client, mem_db):
    """PUT /editing/drafts/<id> persists the new content."""
    post_resp = client.post(
        "/editing/drafts",
        json={"video_id": "vid-2", "video_name": "Talk", "content": "Original."},
    )
    draft_id = post_resp.get_json()["draft_id"]

    put_resp = client.put(
        f"/editing/drafts/{draft_id}",
        json={"content": "Updated content."},
    )
    assert put_resp.status_code == 200

    # Verify the DB was updated
    draft = db_service.get_draft(draft_id)
    assert draft["content"] == "Updated content."


@pytest.mark.skip(reason="Pending #14 implementation")
def test_put_editing_draft_creates_version(client, mem_db):
    """PUT /editing/drafts/<id> inserts a row in draft_versions."""
    post_resp = client.post(
        "/editing/drafts",
        json={"video_id": "vid-3", "video_name": "Talk", "content": "v1."},
    )
    draft_id = post_resp.get_json()["draft_id"]

    client.put(f"/editing/drafts/{draft_id}", json={"content": "v2."})

    versions = db_service.list_draft_versions(draft_id)
    assert len(versions) >= 1, "PUT must create a draft_versions entry"


# ── GET /editor ───────────────────────────────────────────────────────────────

@pytest.mark.skip(reason="Pending #14 implementation")
def test_get_editor_renders_template(client):
    """GET /editor?draft_id=<id> renders editor.html (200)."""
    # Create a draft so the route has something to load
    post_resp = client.post(
        "/editing/drafts",
        json={"video_id": "vid-4", "video_name": "Talk", "content": "Draft."},
    )
    draft_id = post_resp.get_json()["draft_id"]

    resp = client.get(f"/editor?draft_id={draft_id}")
    assert resp.status_code == 200
    assert b"editor" in resp.data.lower(), (
        "Response should contain 'editor' — likely rendering editor.html"
    )


@pytest.mark.skip(reason="Pending #14 implementation")
def test_get_editor_without_draft_id_returns_400(client):
    """GET /editor without draft_id query param returns 400."""
    resp = client.get("/editor")
    assert resp.status_code == 400


@pytest.mark.skip(reason="Pending #14 implementation")
def test_get_editor_with_unknown_draft_id_returns_404(client):
    """GET /editor?draft_id=<nonexistent> returns 404."""
    resp = client.get("/editor?draft_id=99999")
    assert resp.status_code == 404
