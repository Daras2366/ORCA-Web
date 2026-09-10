"""
_env.py — Load the project root .env before any auth module reads os.getenv().

Import this module FIRST in backend/auth/main.py so that all subsequent
imports (security.py, database.py, …) see the populated environment.

Resolution strategy:
  Walk up from this file's directory until we find a .env that contains
  at least one recognised ORCA key (JWT_SECRET or GEMINI_API_KEY).
  Fall back to python-dotenv's own CWD search if nothing is found.

This is CWD-independent: it works whether uvicorn is started from the
project root, from backend/, or from any other directory.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


def _find_project_root_env() -> Path | None:
    """
    Walk up the directory tree from this file looking for a .env file
    that contains ORCA-specific keys. Return its path, or None.
    """
    anchor_keys = {"JWT_SECRET", "GEMINI_API_KEY", "DATABASE_URL"}
    candidate = Path(__file__).resolve().parent

    for _ in range(10):          # cap at 10 levels to avoid infinite loops
        env_file = candidate / ".env"
        if env_file.is_file():
            # Quick content scan — no need to parse, just check for keys.
            try:
                content = env_file.read_text(encoding="utf-8", errors="ignore")
                if any(key in content for key in anchor_keys):
                    return env_file
            except OSError:
                pass
        parent = candidate.parent
        if parent == candidate:   # filesystem root
            break
        candidate = parent

    return None


def load_orca_env() -> None:
    """Load the project root .env, then fall back to dotenv's CWD search."""
    env_path = _find_project_root_env()

    if env_path:
        # override=False so real shell env vars always win over .env values.
        load_dotenv(dotenv_path=env_path, override=False)
    else:
        # Fallback: let python-dotenv search from CWD upward.
        load_dotenv(override=False)


# Load immediately on import so every subsequent os.getenv() call in the
# auth package sees the correct values.
load_orca_env()
