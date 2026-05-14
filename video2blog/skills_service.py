"""
Skills discovery and prompt loading service — Issue #15.

Functions:
  list_skills(skills_folder=None) → list of {name, description, modes?, parameters?} dicts
  get_skill_prompt(skill_name, skills_folder=None) → prompt body (str)
  get_skill_data(skill_name, skills_folder=None) → full skill data dict
  get_merged_parameters(skill_name, mode_name, skills_folder=None) → merged parameter list
"""

import os
import re
import logging
import yaml

logger = logging.getLogger(__name__)


def _get_skills_folder(skills_folder=None):
    """Return skills folder path, defaulting to env var SKILLS_FOLDER or ./skills."""
    if skills_folder is not None:
        return skills_folder
    return os.getenv("SKILLS_FOLDER", "./skills")


def _parse_frontmatter(content):
    """
    Parse YAML front matter from a SKILL.md file.
    
    Returns (frontmatter_dict, body_content).
    Front matter is expected between --- delimiters at the start of the file.
    """
    # Match front matter: starts with ---, ends with ---, YAML in between
    pattern = r'^---\s*\n(.*?\n)---\s*\n(.*)$'
    match = re.match(pattern, content, re.DOTALL)
    
    if not match:
        return None, content
    
    frontmatter_raw = match.group(1)
    body = match.group(2)
    
    # Parse YAML using PyYAML for proper structure support
    try:
        frontmatter = yaml.safe_load(frontmatter_raw)
        if frontmatter is None:
            frontmatter = {}
    except yaml.YAMLError as e:
        logger.warning(f"Failed to parse YAML front matter: {e}")
        return None, content
    
    return frontmatter, body


def list_skills(skills_folder=None):
    """
    Scan the skills folder and return a list of skill dicts.
    
    Each skill is a subdirectory containing a SKILL.md file with YAML front matter.
    
    Returns:
        list: [{name: str, description: str, modes?: list, parameters?: list}, ...]
    
    Malformed files (missing required fields) are skipped silently with a warning.
    """
    folder = _get_skills_folder(skills_folder)
    
    if not os.path.isdir(folder):
        logger.warning(f"Skills folder not found: {folder}")
        return []
    
    skills = []
    
    for entry in os.listdir(folder):
        skill_path = os.path.join(folder, entry)
        if not os.path.isdir(skill_path):
            continue
        
        skill_file = os.path.join(skill_path, "SKILL.md")
        if not os.path.isfile(skill_file):
            continue
        
        try:
            with open(skill_file, "r", encoding="utf-8") as f:
                content = f.read()
            
            frontmatter, _ = _parse_frontmatter(content)
            
            if not frontmatter:
                logger.warning(f"Skill {entry}: missing front matter, skipping")
                continue
            
            name = frontmatter.get("name")
            description = frontmatter.get("description")
            
            if not name or not description:
                logger.warning(
                    f"Skill {entry}: missing required fields (name, description), skipping"
                )
                continue
            
            skill_dict = {"name": name, "description": description}
            
            # Include modes and parameters if present
            if "modes" in frontmatter:
                skill_dict["modes"] = frontmatter["modes"]
            
            if "parameters" in frontmatter:
                skill_dict["parameters"] = frontmatter["parameters"]
            
            skills.append(skill_dict)
        
        except Exception as e:
            logger.warning(f"Failed to parse skill {entry}: {e}")
            continue
    
    return skills


def get_skill_prompt(skill_name, skills_folder=None):
    """
    Load the prompt body for a given skill (front matter stripped).
    
    Args:
        skill_name: Name of the skill (subdirectory name)
        skills_folder: Optional override for skills folder path
    
    Returns:
        str: The prompt body content
    
    Raises:
        FileNotFoundError: If the skill does not exist
        ValueError: If the SKILL.md is malformed
    """
    folder = _get_skills_folder(skills_folder)
    skill_file = os.path.join(folder, skill_name, "SKILL.md")
    
    if not os.path.isfile(skill_file):
        raise FileNotFoundError(f"Skill not found: {skill_name}")
    
    with open(skill_file, "r", encoding="utf-8") as f:
        content = f.read()
    
    frontmatter, body = _parse_frontmatter(content)
    
    if not frontmatter:
        raise ValueError(f"Skill {skill_name}: missing front matter")
    
    return body.strip()


def get_skill_data(skill_name, skills_folder=None):
    """
    Load full skill data including front matter and prompt body.
    
    Args:
        skill_name: Name of the skill (subdirectory name)
        skills_folder: Optional override for skills folder path
    
    Returns:
        dict: {name, description, modes?, parameters?, prompt}
    
    Raises:
        FileNotFoundError: If the skill does not exist
        ValueError: If the SKILL.md is malformed
    """
    folder = _get_skills_folder(skills_folder)
    skill_file = os.path.join(folder, skill_name, "SKILL.md")
    
    if not os.path.isfile(skill_file):
        raise FileNotFoundError(f"Skill not found: {skill_name}")
    
    with open(skill_file, "r", encoding="utf-8") as f:
        content = f.read()
    
    frontmatter, body = _parse_frontmatter(content)
    
    if not frontmatter:
        raise ValueError(f"Skill {skill_name}: missing front matter")
    
    name = frontmatter.get("name")
    description = frontmatter.get("description")
    
    if not name or not description:
        raise ValueError(f"Skill {skill_name}: missing required fields (name, description)")
    
    skill_data = {
        "name": name,
        "description": description,
        "prompt": body.strip()
    }
    
    # Include modes and parameters if present
    if "modes" in frontmatter:
        skill_data["modes"] = frontmatter["modes"]
    
    if "parameters" in frontmatter:
        skill_data["parameters"] = frontmatter["parameters"]
    
    return skill_data


def get_merged_parameters(skill_name, mode_name=None, skills_folder=None):
    """
    Return the merged parameter list for a skill invocation.

    Skill-level parameters (apply to every invocation) are listed first,
    followed by mode-level parameters (only when mode_name is given).

    Args:
        skill_name: Name of the skill (subdirectory name)
        mode_name: Optional mode name to include mode-level parameters
        skills_folder: Optional override for skills folder path

    Returns:
        list: [{name, label, placeholder?, required?}, ...]

    Raises:
        FileNotFoundError: If the skill does not exist
        ValueError: If the SKILL.md is malformed
    """
    skill_data = get_skill_data(skill_name, skills_folder)

    merged = list(skill_data.get("parameters") or [])

    if mode_name:
        for mode in skill_data.get("modes") or []:
            if mode.get("name") == mode_name:
                merged.extend(mode.get("parameters") or [])
                break

    return merged
