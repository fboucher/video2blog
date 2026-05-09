"""
Skills discovery and prompt loading service — Issue #15.

Functions:
  list_skills(skills_folder=None) → list of {name, description} dicts
  get_skill_prompt(skill_name, skills_folder=None) → prompt body (str)
"""

import os
import re
import logging

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
    
    # Parse YAML manually (simple key: value pairs)
    frontmatter = {}
    for line in frontmatter_raw.split('\n'):
        line = line.strip()
        if not line or ':' not in line:
            continue
        key, value = line.split(':', 1)
        frontmatter[key.strip()] = value.strip()
    
    return frontmatter, body


def list_skills(skills_folder=None):
    """
    Scan the skills folder and return a list of skill dicts.
    
    Each skill is a subdirectory containing a SKILL.md file with YAML front matter.
    
    Returns:
        list: [{name: str, description: str}, ...]
    
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
            
            skills.append({"name": name, "description": description})
        
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
