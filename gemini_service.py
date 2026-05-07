"""
Google Gemini API service for video2blog.

Handles video uploads, blog generation, Q&A, and file lifecycle management
via the Google Generative AI Python client.
"""

import os
import time
from typing import Optional
import google.generativeai as genai


def is_configured() -> bool:
    """Return True if GEMINI_API_KEY is set in the environment."""
    return bool(os.environ.get("GEMINI_API_KEY"))


def get_model() -> str:
    """Return the Gemini model name, defaulting to gemini-2.0-flash."""
    return os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")


def _client() -> genai.GenerativeModel:
    """Configure and return a GenerativeModel instance."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set. Cannot call Gemini API.")
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(get_model())


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

    api_key = os.environ["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)

    uploaded = genai.upload_file(local_path, mime_type="video/mp4")

    # Wait for the file to finish processing
    max_wait = 300  # seconds
    waited = 0
    while uploaded.state.name == "PROCESSING" and waited < max_wait:
        time.sleep(5)
        waited += 5
        uploaded = genai.get_file(uploaded.name)

    if uploaded.state.name != "ACTIVE":
        raise RuntimeError(
            f"Gemini file upload did not become ACTIVE (state={uploaded.state.name}): {local_path}"
        )

    return uploaded.uri


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
    Generate a blog post from a video reference and conversation history.

    Args:
        file_ref: Gemini file URI (from upload_video) or a public URL.
        messages: List of prior conversation turns:
                  [{"role": "user"|"model", "parts": [str]}, ...]

    Returns:
        {"blog": str, "timestamps": list}
        Timestamps is a list of dicts like {"time": "00:01:23", "label": "..."}.

    Raises:
        RuntimeError: If GEMINI_API_KEY is not set or the API call fails.
    """
    model = _client()

    system_prompt = (
        "You are a professional blog writer. "
        "Analyze the provided video and produce a detailed, engaging blog post. "
        "At the end of your response, include a JSON block wrapped in ```json ... ``` "
        "containing a list of key timestamps in the format: "
        '[{"time": "HH:MM:SS", "label": "short description"}, ...]'
    )

    # Build the parts list: video reference + history + generation request
    if file_ref.startswith("files/") or file_ref.startswith("https://generativelanguage"):
        video_part = genai.get_file(file_ref.replace("files/", "", 1)) if file_ref.startswith("files/") else {"file_uri": file_ref, "mime_type": "video/mp4"}
    else:
        # Treat as a public URL
        video_part = {"file_uri": file_ref, "mime_type": "video/mp4"}

    # Flatten conversation history for the multi-turn call
    history = []
    for msg in messages:
        history.append({"role": msg["role"], "parts": msg["parts"]})

    chat = model.start_chat(history=history)
    response = chat.send_message(
        [video_part, system_prompt] if not history else system_prompt
    )

    raw_text: str = response.text

    # Extract timestamps JSON block if present
    import json
    import re
    timestamps: list = []
    json_match = re.search(r"```json\s*(.*?)\s*```", raw_text, re.DOTALL)
    if json_match:
        try:
            timestamps = json.loads(json_match.group(1))
        except json.JSONDecodeError:
            timestamps = []
        # Remove the JSON block from the blog text
        blog_text = raw_text[: json_match.start()].strip()
    else:
        blog_text = raw_text.strip()

    return {"blog": blog_text, "timestamps": timestamps}


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
    model = _client()

    if not messages:
        raise ValueError("messages must not be empty; provide at least one user turn.")

    # Separate history from the current question
    history = messages[:-1]
    current = messages[-1]

    # Resolve file reference
    if file_ref.startswith("files/"):
        file_name = file_ref.replace("files/", "", 1) if not file_ref.startswith("files/files/") else file_ref
        video_part = genai.get_file(file_name)
    else:
        video_part = {"file_uri": file_ref, "mime_type": "video/mp4"}

    chat = model.start_chat(history=history)

    # On the first turn, include the video part alongside the question
    if not history:
        user_parts = [video_part] + (current["parts"] if isinstance(current["parts"], list) else [current["parts"]])
    else:
        user_parts = current["parts"] if isinstance(current["parts"], list) else [current["parts"]]

    response = chat.send_message(user_parts)
    return response.text.strip()


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

    api_key = os.environ["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)

    try:
        # The Files API name is the last path segment
        file_name = file_uri.split("/")[-1]
        genai.delete_file(f"files/{file_name}")
        return True
    except Exception as e:
        print(f"gemini_service.delete_file error: {e}")
        return False
