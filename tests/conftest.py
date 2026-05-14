"""
Shared pytest fixtures and test configuration for video2blog.
"""

import sys
import pathlib
from unittest.mock import MagicMock

# ── Mock google.genai before any test module imports it ─────────────────────
# google-genai may not be installed in every environment.
# We inject a MagicMock so imports of the form
#   from google import genai
# succeed in gemini_service.py without the real package.

_mock_genai = MagicMock()
_mock_google = MagicMock()
_mock_google.genai = _mock_genai

sys.modules.setdefault("google", _mock_google)
sys.modules["google.genai"] = _mock_genai

# ── Mock cv2 / numpy before any test module imports them ────────────────────
# opencv-python (cv2) is not installed in every test environment.
# video2blog.keyframe_extractor and video2blog.web_app import cv2/numpy

sys.modules.setdefault("cv2", MagicMock())
sys.modules.setdefault("numpy", MagicMock())

# ── Suppress Docker-path mkdir calls in web_app.py module-level code ────────
# web_app.py calls Path('/app/uploads').mkdir(...) at import time.
# Outside Docker, /app doesn't exist and mkdir raises PermissionError.
# Wrap mkdir to silently ignore PermissionError so web_app imports cleanly.

_orig_mkdir = pathlib.Path.mkdir


def _mkdir_no_permission_error(self, mode=0o777, parents=False, exist_ok=False):
    try:
        _orig_mkdir(self, mode=mode, parents=parents, exist_ok=exist_ok)
    except (PermissionError, FileNotFoundError):
        pass


pathlib.Path.mkdir = _mkdir_no_permission_error
