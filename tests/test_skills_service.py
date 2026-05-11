"""
Unit tests for skills_service.py — Issue #15 acceptance criteria.

Tests verify:
  list_skills()              — scans SKILLS_FOLDER, parses YAML front matter,
                               returns list of skill dicts; skips malformed files
  get_skill_prompt()         — returns prompt body with front matter stripped
  get_merged_parameters()    — merges skill-level and mode-level parameters
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
description: [unclosed bracket
---

Body text here.
"""

SKILL_WITH_PARAMETERS = """\
---
name: fact-checker
description: Verify factual claims
parameters:
  - name: audience
    label: "Target audience"
    placeholder: "e.g. developers"
    required: true
  - name: goal
    label: "Goal of the piece"
---
You are a fact-checking assistant.
"""

SKILL_WITH_MODES_AND_PARAMS = """\
---
name: text-editor
description: General-purpose text editing
parameters:
  - name: style
    label: "Writing style"
modes:
  - name: full-edit
    label: "Full Edit"
  - name: rewrite-section
    label: "Rewrite Section"
    parameters:
      - name: section
        label: "Which section?"
        required: true
---
You are an expert copy editor.
"""

MINIMAL_SKILL_MD = """\
---
name: improve-flow
description: Improve the flow and readability.
---
Rewrite for flow.
"""


# ── list_skills ───────────────────────────────────────────────────────────────

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


def test_list_skills_skips_files_without_front_matter(tmp_path):
    """list_skills() skips SKILL.md files that have no YAML front matter."""
    d = tmp_path / "no-front-matter"
    d.mkdir()
    (d / "SKILL.md").write_text(SKILL_WITHOUT_FRONT_MATTER)

    import skills_service
    result = skills_service.list_skills(str(tmp_path))

    assert isinstance(result, list)
    assert len(result) == 0


def test_list_skills_empty_folder_returns_empty_list(tmp_path):
    """list_skills() returns an empty list when SKILLS_FOLDER has no SKILL.md files."""
    import skills_service
    result = skills_service.list_skills(str(tmp_path))
    assert result == []


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


def test_get_skill_prompt_returns_none_for_unknown_skill(tmp_path):
    """get_skill_prompt() raises FileNotFoundError when the named skill does not exist."""
    import skills_service
    with pytest.raises(FileNotFoundError):
        skills_service.get_skill_prompt("nonexistent-skill", str(tmp_path))


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


# ── get_merged_parameters ──────────────────────────────────────────────────────

def test_get_merged_parameters_skill_level_only(tmp_path):
    """get_merged_parameters() returns skill-level params when no mode is given."""
    skill_dir = tmp_path / "fact-checker"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(SKILL_WITH_PARAMETERS)

    import skills_service
    params = skills_service.get_merged_parameters("fact-checker", skills_folder=str(tmp_path))

    names = [p["name"] for p in params]
    assert "audience" in names
    assert "goal" in names


def test_get_merged_parameters_merges_skill_and_mode(tmp_path):
    """get_merged_parameters() merges skill-level and mode-level params."""
    skill_dir = tmp_path / "text-editor"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(SKILL_WITH_MODES_AND_PARAMS)

    import skills_service
    params = skills_service.get_merged_parameters(
        "text-editor", mode_name="rewrite-section", skills_folder=str(tmp_path)
    )

    names = [p["name"] for p in params]
    assert "style" in names       # skill-level
    assert "section" in names     # mode-level


def test_get_merged_parameters_skill_level_first(tmp_path):
    """get_merged_parameters() lists skill-level params before mode-level params."""
    skill_dir = tmp_path / "text-editor"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(SKILL_WITH_MODES_AND_PARAMS)

    import skills_service
    params = skills_service.get_merged_parameters(
        "text-editor", mode_name="rewrite-section", skills_folder=str(tmp_path)
    )

    names = [p["name"] for p in params]
    assert names.index("style") < names.index("section")


def test_get_merged_parameters_no_params_returns_empty(tmp_path):
    """get_merged_parameters() returns [] for a skill with no parameters."""
    skill_dir = tmp_path / "summarize"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(VALID_SKILL_MD)

    import skills_service
    params = skills_service.get_merged_parameters("summarize", skills_folder=str(tmp_path))

    assert params == []


def test_get_merged_parameters_unmatched_mode_returns_skill_level_only(tmp_path):
    """get_merged_parameters() with an unknown mode returns only skill-level params."""
    skill_dir = tmp_path / "text-editor"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(SKILL_WITH_MODES_AND_PARAMS)

    import skills_service
    params = skills_service.get_merged_parameters(
        "text-editor", mode_name="nonexistent-mode", skills_folder=str(tmp_path)
    )

    names = [p["name"] for p in params]
    assert names == ["style"]


def test_get_merged_parameters_required_flag_preserved(tmp_path):
    """get_merged_parameters() preserves the required flag on parameters."""
    skill_dir = tmp_path / "fact-checker"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(SKILL_WITH_PARAMETERS)

    import skills_service
    params = skills_service.get_merged_parameters("fact-checker", skills_folder=str(tmp_path))

    audience = next(p for p in params if p["name"] == "audience")
    goal = next(p for p in params if p["name"] == "goal")
    assert audience.get("required") is True
    assert not goal.get("required")


def test_get_merged_parameters_raises_for_unknown_skill(tmp_path):
    """get_merged_parameters() raises FileNotFoundError for unknown skill."""
    import skills_service
    with pytest.raises(FileNotFoundError):
        skills_service.get_merged_parameters("no-such-skill", skills_folder=str(tmp_path))
