# Agent Guidelines for py-frame-x

This document provides coding agents with essential information for working on the Keyframe Extractor project.

## Project Overview

**Language**: Python 3.11  
**Type**: Single-file CLI application for video keyframe extraction  
**Framework**: OpenCV (cv2), NumPy  
**Deployment**: Podman containerized

## Build, Test, and Run Commands

### Running the Application

```bash
# Direct Python execution
python keyframe_extractor.py <video_path> [-o OUTPUT] [-t THRESHOLD] [-m MAX_FRAMES]

# Example with options
python keyframe_extractor.py video.mp4 -o ./frames -t 0.3 -m 50
```

### Podman Commands

```bash
# Build container
podman build -t keyframe-extractor .

# Run with volume mounts
podman run -v $(pwd)/input:/app/input -v $(pwd)/output:/app/output keyframe-extractor \
  python keyframe_extractor.py /app/input/video.mp4 -o /app/output

# Podman Compose
podman-compose up --build
```

### Testing

**Note**: No testing framework is currently configured. If adding tests:

```bash
# Install pytest (not in requirements.txt yet)
pip install pytest pytest-cov

# Run all tests (once created)
pytest

# Run specific test file
pytest tests/test_keyframe_extractor.py

# Run single test function
pytest tests/test_keyframe_extractor.py::test_extract_keyframes

# Run with coverage
pytest --cov=. --cov-report=html
```

### Linting/Formatting

**Note**: No linting tools configured. Recommended setup:

```bash
# Install tools (add to requirements-dev.txt if created)
pip install black flake8 mypy isort

# Format code
black keyframe_extractor.py

# Check formatting (don't modify)
black --check keyframe_extractor.py

# Lint with flake8
flake8 keyframe_extractor.py --max-line-length=100

# Type checking
mypy keyframe_extractor.py

# Sort imports
isort keyframe_extractor.py
```

## Code Style Guidelines

### General Principles

- Follow **PEP 8** conventions strictly
- Keep code simple and functional - avoid over-engineering
- Single file architecture - maintain simplicity unless complexity demands refactoring
- Prefer functional approach over OOP for this utility

### Imports

**Order** (PEP 8):
1. Standard library imports
2. Third-party imports  
3. Local application imports

**Style**:
```python
#!/usr/bin/env python3
# Standard library
import argparse
import json
import os
from pathlib import Path

# Third-party
import cv2
import numpy as np

# Local (if any)
from . import helpers
```

**Important**:
- ALL imports at module top (never inside functions)
- Use standard aliases: `import numpy as np`
- Group imports with blank lines between groups
- Avoid wildcard imports (`from module import *`)

### Naming Conventions

- **Functions**: `snake_case` with descriptive verb-noun pattern
  ```python
  def extract_keyframes(video_path, output_dir, threshold=0.3):
  ```
  
- **Variables**: `snake_case`, descriptive and semantic
  ```python
  frame_count = 0
  saved_count = 0
  prev_frame = None
  ```

- **Constants**: `UPPER_SNAKE_CASE` at module level
  ```python
  DEFAULT_THRESHOLD = 0.3
  MAX_JPEG_QUALITY = 90
  FRAME_SAMPLE_RATE = 5
  ```

- **Private functions/variables**: Prefix with single underscore
  ```python
  def _calculate_histogram_diff(frame1, frame2):
  ```

### Type Hints

**Always use type hints** for function signatures:

```python
from pathlib import Path
from typing import List, Dict, Any

def extract_keyframes(
    video_path: str,
    output_dir: str,
    threshold: float = 0.3,
    max_frames: int = 100
) -> List[Dict[str, Any]]:
    """Extract keyframes from video."""
    pass
```

### Docstrings

Use **Google-style** docstrings for all functions:

```python
def extract_keyframes(video_path: str, output_dir: str, threshold: float = 0.3) -> List[Dict[str, Any]]:
    """Extract keyframes from a video file using scene detection.
    
    Args:
        video_path: Path to the input video file.
        output_dir: Directory to save extracted keyframes.
        threshold: Scene detection threshold between 0.0 and 1.0. Lower values
            detect more scenes. Default is 0.3.
        max_frames: Maximum number of keyframes to extract. Default is 100.
    
    Returns:
        List of dictionaries containing frame metadata (frame number, timestamp, filename).
    
    Raises:
        ValueError: If video file cannot be opened or threshold is out of range.
        IOError: If output directory cannot be created.
    """
```

### Formatting

- **Indentation**: 4 spaces (never tabs)
- **Line length**: Max 100 characters (soft limit), 120 (hard limit)
- **Blank lines**: 2 between top-level functions, 1 between methods
- **Strings**: Use f-strings for formatting, prefer double quotes for docstrings
  ```python
  filename = f"keyframe_{count:04d}_t{timestamp:.2f}s.jpg"
  print(f"Saved {len(keyframes)} keyframes to {output_dir}")
  ```

### Error Handling

**Validate early, fail fast**:

```python
def main():
    # Validate input file
    if not os.path.exists(args.video_path):
        print(f"Error: Video file not found: {args.video_path}")
        return 1
    
    # Validate parameters
    if not 0.0 <= args.threshold <= 1.0:
        print(f"Error: Threshold must be between 0.0 and 1.0")
        return 1
    
    try:
        extract_keyframes(args.video_path, args.output, args.threshold, args.max_frames)
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1
```

**Best practices**:
- Use specific exception types when possible
- Provide informative error messages
- Clean up resources (use context managers or ensure `cap.release()`)
- Return appropriate exit codes (0 = success, 1 = error)

### File Operations

Use `pathlib.Path` for cross-platform compatibility:

```python
from pathlib import Path

# Create directories
Path(output_dir).mkdir(parents=True, exist_ok=True)

# Join paths
output_path = Path(output_dir) / filename

# Check existence
if Path(video_path).exists():
```

## Project-Specific Patterns

### Video Processing

- Sample frames to reduce processing: `if frame_count % 5 != 0: continue`
- Use grayscale for comparisons to improve performance
- Release video capture after processing: `cap.release()`
- Use OpenCV constants: `cv2.CAP_PROP_FPS`, `cv2.HISTCMP_CORREL`

### Output Files

- Naming: `keyframe_{count:04d}_t{timestamp:.2f}s.jpg`
- JPEG quality: 90 (balance between size and quality)
- Metadata: Always save JSON metadata alongside frames

### CLI Arguments

- Use `argparse` for argument parsing
- Provide sensible defaults
- Include help text for all arguments
- Validate inputs before processing

## Adding New Features

When modifying this codebase:

1. **Maintain simplicity**: Only refactor to classes if complexity demands it
2. **Add type hints**: All new functions must have complete type annotations
3. **Write docstrings**: Google-style for all public functions
4. **Consider testing**: Add unit tests for new functionality
5. **Update README**: Document new features and parameters
6. **Podman compatibility**: Ensure changes work in containerized environment

## Common Pitfall Avoidance

- Don't import modules inside functions (move `import json` to top)
- Extract magic numbers to named constants
- Don't use mutable default arguments
- Always close OpenCV VideoCapture objects
- Validate file paths before processing
- Handle edge cases (empty videos, corrupted files, permission errors)

## References

- [PEP 8 Style Guide](https://pep8.org/)
- [OpenCV Documentation](https://docs.opencv.org/)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
