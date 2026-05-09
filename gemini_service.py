"""
Google Gemini API service for video2blog.

Handles video uploads, blog generation, Q&A, and file lifecycle management
via the Google GenAI Python client.
"""

import os
import time
from typing import Optional
from google import genai
from google.genai import types


def is_configured() -> bool:
    """Return True if GEMINI_API_KEY is set in the environment."""
    return bool(os.environ.get("GEMINI_API_KEY"))


def get_model() -> str:
    """Return the Gemini model name, defaulting to gemini-2.0-flash."""
    return os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")


def _client() -> genai.Client:
    """Return a configured Gemini Client instance."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set. Cannot call Gemini API.")
    return genai.Client(api_key=api_key)


def upload_video(local_path: str) -> str:
    """
    Upload a local video file to the Gemini Files API.

    Args:
        local_path: Absolute or relative path to the video file.

    Returns:
        The file URI assigned by the Files API (e.g. "files/abc123").

    Raises:
        RuntimeError: If the API key is missing or the upload fails.
        FileNotFoundError: If local_path does not exist.
    """
    if not is_configured():
        raise RuntimeError("GEMINI_API_KEY is not set.")
    if not os.path.exists(local_path):
        raise FileNotFoundError(f"Video file not found: {local_path}")

    client = _client()
    uploaded = client.files.upload(file=local_path)

    # Wait for the file to finish processing
    max_wait = 300  # seconds
    waited = 0
    while uploaded.state.name == "PROCESSING" and waited < max_wait:
        time.sleep(5)
        waited += 5
        uploaded = client.files.get(name=uploaded.name)

    if uploaded.state.name != "ACTIVE":
        raise RuntimeError(
            f"Gemini file upload did not become ACTIVE (state={uploaded.state.name}): {local_path}"
        )

    return uploaded.uri


def _build_history(messages: list) -> list:
    """Convert message dicts to types.Content objects required by chats.create."""
    result = []
    for msg in messages:
        # Accept both 'parts' (Gemini format) and 'content' (frontend chat format)
        raw = msg.get("parts") if "parts" in msg else msg.get("content", "")
        raw_parts = raw if isinstance(raw, list) else [raw]
        parts = []
        for p in raw_parts:
            if isinstance(p, str):
                parts.append(types.Part(text=p))
            elif isinstance(p, types.Part):
                parts.append(p)
            elif isinstance(p, dict):
                parts.append(types.Part.model_validate(p))
            else:
                parts.append(p)
        result.append(types.Content(role=msg["role"], parts=parts))
    return result


def _video_part(file_ref: str, client: genai.Client) -> object:
    """Return a Part or File object suitable for send_message / generate_content."""
    if file_ref.startswith("files/"):
        return client.files.get(name=file_ref)
    return types.Part.from_uri(file_uri=file_ref, mime_type="video/mp4")


def upload_from_url(url: str) -> str:
    """
    Return a URL reference for Gemini to handle natively.

    Gemini can reason over publicly accessible video URLs directly, so no
    actual upload is performed here — we just pass the URL back as the
    file reference used in subsequent API calls.

    Args:
        url: Publicly accessible video URL.

    Returns:
        The original URL (used as file_ref in generate_blog / ask).
    """
    return url


def generate_blog(file_ref: str, messages: list) -> dict:
    """
    Generate a blog post and suggested timestamps from a video reference.

    Args:
        file_ref: Gemini file URI (from upload_video) or a public URL.
        messages: List of prior conversation turns:
                  [{"role": "user"|"model", "parts": [str]}, ...]

    Returns:
        {"draft": str, "timestamps": list[int]}
        timestamps is a list of seconds (integers) where key moments occur.
        timestamps is [] if Gemini did not return any or parsing failed.

    Raises:
        RuntimeError: If GEMINI_API_KEY is not set or the API call fails.
    """
    import json
    import re

    client = _client()

    system_prompt = (
        "You are a professional blog writer. "
        "Analyze the provided video and produce a detailed, engaging blog post. "
        "Return a JSON object with exactly two fields:\n"
        '- "draft": the full blog post as markdown\n'
        '- "timestamps": a list of seconds (integers) where key moments occur, e.g. [10, 45, 120]\n'
        "Return only the JSON object — no code fences, no extra text."
    )

    video = _video_part(file_ref, client)
    history = _build_history(messages)

    chat = client.chats.create(model=get_model(), history=history)
    response = chat.send_message(
        [video, system_prompt] if not history else system_prompt
    )

    raw_text: str = response.text.strip()

    # Strip optional code fences Gemini may add despite instructions
    fenced = re.match(r"^```(?:json)?\s*(.*?)\s*```$", raw_text, re.DOTALL)
    if fenced:
        raw_text = fenced.group(1).strip()

    try:
        parsed = json.loads(raw_text)
        draft = str(parsed.get("draft", ""))
        raw_timestamps = parsed.get("timestamps", [])
        timestamps = [int(t) for t in raw_timestamps if isinstance(t, (int, float))]
    except (json.JSONDecodeError, ValueError):
        # Fallback: treat entire response as draft, no timestamps
        draft = response.text.strip()
        timestamps = []

    return {"draft": draft, "timestamps": timestamps}


def ask(file_ref: str, messages: list) -> str:
    """
    Answer a question about a video using conversation history.

    Args:
        file_ref: Gemini file URI or public URL.
        messages: Conversation history (same format as generate_blog).
                  The last message with role "user" is the current question.

    Returns:
        The model's answer as a plain string.

    Raises:
        RuntimeError: If GEMINI_API_KEY is not set or the API call fails.
    """
    client = _client()

    if not messages:
        raise ValueError("messages must not be empty; provide at least one user turn.")

    # Separate history from the current question
    history = _build_history(messages[:-1])
    current = messages[-1]

    video = _video_part(file_ref, client)

    chat = client.chats.create(model=get_model(), history=history)

    # On the first turn, include the video alongside the question
    # Accept both 'parts' (Gemini format) and 'content' (frontend chat format)
    raw = current.get("parts") if "parts" in current else current.get("content", "")
    raw_parts = raw if isinstance(raw, list) else [raw]
    if not history:
        user_parts = [video] + raw_parts
    else:
        user_parts = raw_parts

    response = chat.send_message(user_parts)
    return response.text.strip()


def download_video_from_url(url: str, output_path: str) -> str:
    """Download a video from url to output_path using yt-dlp.

    Args:
        url: Publicly accessible video URL.
        output_path: Desired output path (without extension; yt-dlp may append one).

    Returns:
        The actual file path written to disk.

    Raises:
        RuntimeError: If yt-dlp exits with a non-zero return code.
        FileNotFoundError: If the expected output file cannot be located.
    """
    import subprocess
    import shutil

    ytdlp = shutil.which('yt-dlp') or 'yt-dlp'
    result = subprocess.run(
        [ytdlp, '-o', output_path, '--no-playlist', url],
        capture_output=True, text=True, timeout=300
    )
    if result.returncode != 0:
        raise RuntimeError(f"yt-dlp failed: {result.stderr}")

    if os.path.exists(output_path):
        return output_path

    for ext in ['.mp4', '.webm', '.mkv']:
        candidate = output_path + ext
        if os.path.exists(candidate):
            return candidate

    raise FileNotFoundError(f"yt-dlp output not found at {output_path}")


def delete_file(file_uri: str) -> bool:
    """
    Delete a file from the Gemini Files API.

    Args:
        file_uri: The URI returned by upload_video (e.g. "files/abc123").

    Returns:
        True if deleted successfully, False on error.
    """
    if not is_configured():
        return False

    client = _client()

    try:
        # The Files API name is the last path segment
        file_name = file_uri.split("/")[-1]
        client.files.delete(name=f"files/{file_name}")
        return True
    except Exception as e:
        print(f"gemini_service.delete_file error: {e}")
        return False
