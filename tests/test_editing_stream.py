"""
Tests for editing_service.py and the POST /editing/stream SSE endpoint — Issue #16.

Unit tests verify:
  is_configured()  — True when EDITING_API_KEY is set, False otherwise
  get_provider()   — returns "anthropic" or "openai" based on EDITING_PROVIDER

Integration tests verify:
  POST /editing/stream returns SSE response headers and valid JSON chunks

All tests are marked skip until the #16 implementation lands.
"""

import json
import sqlite3
import pytest
from contextlib import contextmanager
from unittest.mock import patch, MagicMock

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


# ── is_configured ─────────────────────────────────────────────────────────────

def test_is_configured_false_when_no_api_key(monkeypatch):
    """is_configured() returns False when EDITING_API_KEY is not set."""
    monkeypatch.delenv("EDITING_API_KEY", raising=False)

    import editing_service
    assert editing_service.is_configured() is False


def test_is_configured_true_when_api_key_set(monkeypatch):
    """is_configured() returns True when EDITING_API_KEY has a non-empty value."""
    monkeypatch.setenv("EDITING_API_KEY", "sk-test-key")

    import editing_service
    assert editing_service.is_configured() is True


def test_is_configured_false_when_api_key_empty_string(monkeypatch):
    """is_configured() returns False when EDITING_API_KEY is set to empty string."""
    monkeypatch.setenv("EDITING_API_KEY", "")

    import editing_service
    assert editing_service.is_configured() is False


# ── get_provider ──────────────────────────────────────────────────────────────

def test_get_provider_returns_anthropic_by_default(monkeypatch):
    """get_provider() returns 'anthropic' when EDITING_PROVIDER is not set."""
    monkeypatch.delenv("EDITING_PROVIDER", raising=False)

    import editing_service
    assert editing_service.get_provider() == "anthropic"


def test_get_provider_returns_anthropic_when_set(monkeypatch):
    """get_provider() returns 'anthropic' when EDITING_PROVIDER=anthropic."""
    monkeypatch.setenv("EDITING_PROVIDER", "anthropic")

    import editing_service
    assert editing_service.get_provider() == "anthropic"


def test_get_provider_returns_openai_when_set(monkeypatch):
    """get_provider() returns 'openai' when EDITING_PROVIDER=openai."""
    monkeypatch.setenv("EDITING_PROVIDER", "openai")

    import editing_service
    assert editing_service.get_provider() == "openai"


def test_get_provider_normalizes_to_lowercase(monkeypatch):
    """get_provider() normalizes the env var value to lowercase."""
    monkeypatch.setenv("EDITING_PROVIDER", "Anthropic")

    import editing_service
    assert editing_service.get_provider() == "anthropic"


# ── POST /editing/stream — SSE response ───────────────────────────────────────

def test_post_editing_stream_returns_sse_content_type(client, mem_db, monkeypatch):
    """POST /editing/stream must return Content-Type: text/event-stream."""
    monkeypatch.setenv("EDITING_API_KEY", "sk-test-key")
    monkeypatch.setenv("EDITING_PROVIDER", "anthropic")

    # Create a draft for the stream to reference
    draft_id = db_service.create_draft("vid-1", "Talk", "Draft content.")

    # Patch the editing_service.stream_edit to yield controlled chunks
    mock_chunks = [
        b'data: {"delta": "Hello", "done": false}\n\n',
        b'data: {"delta": " world", "done": false}\n\n',
        b'data: {"done": true}\n\n',
    ]

    with patch("editing_service.stream_edit", return_value=iter(mock_chunks)):
        resp = client.post(
            "/editing/stream",
            json={
                "draft_id": draft_id,
                "skill_name": "edit-video-blog",
                "messages": [],
            },
        )

    assert resp.status_code == 200
    assert "text/event-stream" in resp.content_type


def test_post_editing_stream_yields_valid_json_chunks(client, mem_db, monkeypatch):
    """POST /editing/stream chunks must be valid JSON with 'delta' or 'done' keys."""
    monkeypatch.setenv("EDITING_API_KEY", "sk-test-key")
    monkeypatch.setenv("EDITING_PROVIDER", "anthropic")

    draft_id = db_service.create_draft("vid-2", "Talk", "Draft.")

    mock_chunks = [
        b'data: {"delta": "Word", "done": false}\n\n',
        b'data: {"done": true}\n\n',
    ]

    with patch("editing_service.stream_edit", return_value=iter(mock_chunks)):
        resp = client.post(
            "/editing/stream",
            json={"draft_id": draft_id, "skill_name": "edit-video-blog", "messages": []},
        )

    raw = resp.data.decode()
    for line in raw.splitlines():
        if line.startswith("data: "):
            payload = json.loads(line[len("data: "):])
            assert "delta" in payload or "done" in payload, (
                f"SSE chunk must contain 'delta' or 'done': {payload}"
            )


def test_post_editing_stream_ends_with_done_true(client, mem_db, monkeypatch):
    """The final SSE chunk from POST /editing/stream must be {\"done\": true}."""
    monkeypatch.setenv("EDITING_API_KEY", "sk-test-key")
    monkeypatch.setenv("EDITING_PROVIDER", "anthropic")

    draft_id = db_service.create_draft("vid-3", "Talk", "Draft.")

    mock_chunks = [
        b'data: {"delta": "First", "done": false}\n\n',
        b'data: {"done": true}\n\n',
    ]

    with patch("editing_service.stream_edit", return_value=iter(mock_chunks)):
        resp = client.post(
            "/editing/stream",
            json={"draft_id": draft_id, "skill_name": "edit-video-blog", "messages": []},
        )

    raw = resp.data.decode()
    data_lines = [
        line[len("data: "):]
        for line in raw.splitlines()
        if line.startswith("data: ")
    ]
    assert len(data_lines) >= 1
    last_chunk = json.loads(data_lines[-1])
    assert last_chunk.get("done") is True, (
        "Last SSE chunk must be {\"done\": true}"
    )


def test_post_editing_stream_requires_draft_id(client, monkeypatch):
    """POST /editing/stream without draft_id returns 400."""
    monkeypatch.setenv("EDITING_API_KEY", "sk-test-key")

    resp = client.post(
        "/editing/stream",
        json={"skill_name": "edit-video-blog", "messages": []},
    )
    assert resp.status_code == 400


def test_post_editing_stream_returns_503_when_not_configured(client, monkeypatch):
    """POST /editing/stream returns 503 when EDITING_API_KEY is not set."""
    monkeypatch.delenv("EDITING_API_KEY", raising=False)

    resp = client.post(
        "/editing/stream",
        json={"draft_id": 1, "skill_name": "edit-video-blog", "messages": []},
    )
    assert resp.status_code == 503
