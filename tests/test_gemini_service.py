"""
Tests for gemini_service.py — Issue #22 acceptance criteria.

All external calls to google.generativeai are mocked via conftest.py so the
tests run without network access or a real API key.
"""

import os
import pytest
from unittest.mock import MagicMock, patch

# conftest.py injects a MagicMock for google / google.generativeai before
# collection, so this import succeeds even without the real package installed.
import gemini_service  # written by Ripley on squad/22


# ── Helpers ──────────────────────────────────────────────────────────────────

def _chat_mock(text="mock response"):
    """
    Build a model mock that uses start_chat().send_message() — matching the
    actual gemini_service implementation.
    """
    response = MagicMock()
    response.text = text
    chat = MagicMock()
    chat.send_message.return_value = response
    model = MagicMock()
    model.start_chat.return_value = chat
    return model, chat, response


# ── is_configured ────────────────────────────────────────────────────────────

def test_is_configured_false_when_no_api_key():
    env = {k: v for k, v in os.environ.items() if k != "GEMINI_API_KEY"}
    with patch.dict(os.environ, env, clear=True):
        assert gemini_service.is_configured() is False


def test_is_configured_true_when_api_key_set():
    with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key-xyz"}):
        assert gemini_service.is_configured() is True


# ── get_model ────────────────────────────────────────────────────────────────

def test_get_model_returns_default():
    env = {k: v for k, v in os.environ.items() if k != "GEMINI_MODEL"}
    with patch.dict(os.environ, env, clear=True):
        assert gemini_service.get_model() == "gemini-2.0-flash"


def test_get_model_respects_env_override():
    with patch.dict(os.environ, {"GEMINI_MODEL": "gemini-1.5-pro"}):
        assert gemini_service.get_model() == "gemini-1.5-pro"


# ── upload_video ─────────────────────────────────────────────────────────────

def test_upload_video_calls_files_api():
    """
    upload_video must call genai.upload_file with the local path and return the
    file URI.  The file-state loop is short-circuited by having state.name be
    something other than 'PROCESSING' immediately.
    """
    import google.generativeai as genai

    fake_file = MagicMock()
    fake_file.uri = "files/abc123"
    fake_file.name = "abc123"
    fake_file.state.name = "ACTIVE"  # not "PROCESSING" → no wait loop

    genai.upload_file = MagicMock(return_value=fake_file)
    genai.configure = MagicMock()

    with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}), \
         patch("os.path.exists", return_value=True):
        result = gemini_service.upload_video("/app/uploads/video.mp4")

    genai.upload_file.assert_called_once_with(
        "/app/uploads/video.mp4", mime_type="video/mp4"
    )
    assert result == fake_file.uri


# ── upload_from_url ──────────────────────────────────────────────────────────

def test_upload_from_url_returns_url():
    """upload_from_url must return the URL unchanged — no API call is made."""
    url = "https://example.com/keynote.mp4"
    result = gemini_service.upload_from_url(url)
    assert result == url


# ── delete_file ──────────────────────────────────────────────────────────────

def test_delete_file_calls_files_delete():
    """
    delete_file must call genai.delete_file with 'files/<name>' derived from the
    URI and return True.
    """
    import google.generativeai as genai

    genai.delete_file = MagicMock()
    genai.configure = MagicMock()

    uri = "files/abc123"
    with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
        result = gemini_service.delete_file(uri)

    genai.delete_file.assert_called_once_with("files/abc123")
    assert result is True


# ── generate_blog ────────────────────────────────────────────────────────────

def test_generate_blog_returns_dict_with_blog_and_timestamps():
    """
    generate_blog must return a dict with 'blog' (str) and 'timestamps' (list)
    keys regardless of whether the model includes a JSON block.
    """
    import google.generativeai as genai

    model_mock, chat_mock, _ = _chat_mock(
        text="**My Blog**\n\nGreat content here about the demo."
    )
    genai.GenerativeModel = MagicMock(return_value=model_mock)
    genai.configure = MagicMock()

    file_ref = "https://example.com/video.mp4"
    messages = [{"role": "user", "parts": ["Write a blog post about this video."]}]

    with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
        result = gemini_service.generate_blog(file_ref, messages)

    assert isinstance(result, dict), "generate_blog must return a dict"
    assert "blog" in result, "result must have a 'blog' key"
    assert "timestamps" in result, "result must have a 'timestamps' key"
    assert isinstance(result["blog"], str)
    assert isinstance(result["timestamps"], list)


# ── ask ──────────────────────────────────────────────────────────────────────

def test_ask_returns_string():
    """ask must return the model's text response as a plain string."""
    import google.generativeai as genai

    model_mock, chat_mock, _ = _chat_mock(text="  The video shows a product demo.  ")
    genai.GenerativeModel = MagicMock(return_value=model_mock)
    genai.configure = MagicMock()

    file_ref = "https://example.com/keynote.mp4"
    messages = [{"role": "user", "parts": ["What is in the video?"]}]

    with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
        result = gemini_service.ask(file_ref, messages)

    assert isinstance(result, str), "ask must return a string"
    # Leading/trailing whitespace should be stripped
    assert result == result.strip()
