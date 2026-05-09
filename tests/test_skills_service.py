"""
Unit tests for skills_service.py — Issue #15 acceptance criteria.

Tests verify:
  list_skills()         — scans SKILLS_FOLDER, parses YAML front matter,
                          returns list of skill dicts; skips malformed files
  get_skill_prompt()    — returns prompt body with front matter stripped

All tests are marked skip until the #15 implementation lands.
"""

import os
import pytest


# ── Helpers ───────────────────────────────────────────────────────────────────

VALID_SKILL_MD = """\
---
name: summarize
description: Condense the draft into a shorter version.
---

You are a professional editor. Summarize the following blog post draft,
preserving all key ideas but reducing length by at least 30%.
"""

SKILL_WITHOUT_FRONT_MATTER = """\
You are a helpful assistant. Edit the draft.
"""

MALFORMED_FRONT_MATTER = """\
---
name: broken
description: [unclosed bracket
---

Body text here.
"""

MINIMAL_SKILL_MD = """\
---
name: improve-flow
description: Improve the flow and readability.
---
Rewrite for flow.
"""


# ── list_skills ───────────────────────────────────────────────────────────────

@pytest.mark.skip(reason="Pending #15 implementation")
def test_list_skills_returns_list_of_dicts(tmp_path):
    """list_skills() with a valid SKILL.md returns a list containing at least one dict."""
    skill_dir = tmp_path / "summarize"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(VALID_SKILL_MD)

    import skills_service
    result = skills_service.list_skills(str(tmp_path))

    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["name"] == "summarize"
    assert result[0]["description"] == "Condense the draft into a shorter version."


@pytest.mark.skip(reason="Pending #15 implementation")
def test_list_skills_multiple_skills(tmp_path):
    """list_skills() returns one dict per valid SKILL.md found."""
    for folder_name, content in [
        ("summarize", VALID_SKILL_MD),
        ("improve-flow", MINIMAL_SKILL_MD),
    ]:
        d = tmp_path / folder_name
        d.mkdir()
        (d / "SKILL.md").write_text(content)

    import skills_service
    result = skills_service.list_skills(str(tmp_path))

    assert len(result) == 2
    names = {s["name"] for s in result}
    assert "summarize" in names
    assert "improve-flow" in names


@pytest.mark.skip(reason="Pending #15 implementation")
def test_list_skills_skips_malformed_files_without_crashing(tmp_path):
    """list_skills() skips files with malformed YAML front matter gracefully."""
    good_dir = tmp_path / "summarize"
    good_dir.mkdir()
    (good_dir / "SKILL.md").write_text(VALID_SKILL_MD)

    bad_dir = tmp_path / "broken"
    bad_dir.mkdir()
    (bad_dir / "SKILL.md").write_text(MALFORMED_FRONT_MATTER)

    import skills_service
    result = skills_service.list_skills(str(tmp_path))

    # Should return only the valid skill, not crash
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["name"] == "summarize"


@pytest.mark.skip(reason="Pending #15 implementation")
def test_list_skills_skips_files_without_front_matter(tmp_path):
    """list_skills() skips SKILL.md files that have no YAML front matter."""
    d = tmp_path / "no-front-matter"
    d.mkdir()
    (d / "SKILL.md").write_text(SKILL_WITHOUT_FRONT_MATTER)

    import skills_service
    result = skills_service.list_skills(str(tmp_path))

    assert isinstance(result, list)
    assert len(result) == 0


@pytest.mark.skip(reason="Pending #15 implementation")
def test_list_skills_empty_folder_returns_empty_list(tmp_path):
    """list_skills() returns an empty list when SKILLS_FOLDER has no SKILL.md files."""
    import skills_service
    result = skills_service.list_skills(str(tmp_path))
    assert result == []


@pytest.mark.skip(reason="Pending #15 implementation")
def test_list_skills_uses_env_var_default(monkeypatch, tmp_path):
    """list_skills() uses SKILLS_FOLDER env var when no explicit path is given."""
    skill_dir = tmp_path / "improve"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(VALID_SKILL_MD)

    monkeypatch.setenv("SKILLS_FOLDER", str(tmp_path))

    import skills_service
    result = skills_service.list_skills()

    assert isinstance(result, list)
    assert len(result) == 1


# ── get_skill_prompt ──────────────────────────────────────────────────────────

@pytest.mark.skip(reason="Pending #15 implementation")
def test_get_skill_prompt_returns_body_without_front_matter(tmp_path):
    """get_skill_prompt() returns the prompt body with YAML front matter stripped."""
    skill_dir = tmp_path / "summarize"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(VALID_SKILL_MD)

    import skills_service
    body = skills_service.get_skill_prompt("summarize", str(tmp_path))

    assert body is not None
    # Front matter delimiters must be stripped
    assert "---" not in body.strip()[:3]
    assert "name: summarize" not in body
    # Prompt body content must be present
    assert "professional editor" in body


@pytest.mark.skip(reason="Pending #15 implementation")
def test_get_skill_prompt_returns_none_for_unknown_skill(tmp_path):
    """get_skill_prompt() returns None when the named skill does not exist."""
    import skills_service
    result = skills_service.get_skill_prompt("nonexistent-skill", str(tmp_path))
    assert result is None


@pytest.mark.skip(reason="Pending #15 implementation")
def test_get_skill_prompt_body_is_stripped(tmp_path):
    """get_skill_prompt() returns the body with leading/trailing whitespace stripped."""
    skill_dir = tmp_path / "summarize"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(VALID_SKILL_MD)

    import skills_service
    body = skills_service.get_skill_prompt("summarize", str(tmp_path))

    assert body == body.strip(), (
        "get_skill_prompt() should return a stripped string"
    )
