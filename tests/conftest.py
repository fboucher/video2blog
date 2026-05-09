"""
Shared pytest fixtures and test configuration for video2blog.
"""

import sys
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
