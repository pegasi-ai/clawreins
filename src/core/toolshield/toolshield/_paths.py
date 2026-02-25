"""Centralized path resolution for ToolShield.

Resolution order: environment variable → CLI argument → default relative to repo root.
"""

from __future__ import annotations

import os
from pathlib import Path


def repo_root() -> Path:
    """Return the repository root directory."""
    env = os.getenv("TOOLSHIELD_REPO_ROOT")
    if env:
        return Path(env)
    return Path(__file__).resolve().parent.parent


def default_agent_config() -> Path:
    """Return the default agent config TOML path."""
    return repo_root() / "agentrisk" / "agent_config" / "config.toml"


def default_eval_dir() -> Path:
    """Return the default evaluation directory."""
    return repo_root() / "agentrisk"


def default_output_dir() -> Path:
    """Return the default output directory for generated tasks."""
    return repo_root() / "output"


def default_seed_sql() -> Path:
    """Return the path to the bundled Postgres seed SQL."""
    return Path(__file__).resolve().parent / "data" / "seed.sql"
