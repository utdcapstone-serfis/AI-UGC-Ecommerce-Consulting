"""Loads platform credentials from environment variables.

Credentials are never hardcoded or stored in the repo. Copy `.env.example`
to `.env`, fill in real values, and load it (e.g. via `python-dotenv`)
before running the agent.
"""

import os
import warnings
from pathlib import Path

from dotenv import set_key


class ConfigError(RuntimeError):
    """Raised when a required credential is missing from the environment."""


def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise ConfigError(
            f"Missing required environment variable: {name}. "
            "See .env.example for the full list of credentials each adapter needs."
        )
    return value


def pending_path(env_path: Path, name: str) -> Path:
    """Where a value that could not be saved to .env is parked."""
    return Path(env_path).with_name(f"{name.lower()}.pending")


def persist_env_value(name: str, value: str, env_path: Path, critical: bool = True) -> str:
    """Saves a rotated credential so it is not lost. Never prints the value.

    Returns where it ended up:
    - "env": written into the .env file (the normal case).
    - "pending": .env could not be written (missing file, file locked, no
      permission), so the value was parked in `<name>.pending` next to .env
      (gitignored). The caller's .env value is now stale: move the value
      into .env by hand, then delete the pending file.
    - "none": nothing could be saved. The value exists only in this process
      (os.environ), and the credential must be re-created by the user.

    The process environment is always updated, so the rest of this run works.

    `critical=False` is for harmless bookkeeping values (a "last refreshed"
    date): it tries to write .env, returns "env" or "none", and stays quiet
    on failure (no pending file, no warning).
    """
    os.environ[name] = value
    env_path = Path(env_path)

    if not critical:
        if env_path.exists():
            try:
                set_key(str(env_path), name, value)
                return "env"
            except Exception:
                return "none"
        return "none"

    if env_path.exists():
        try:
            set_key(str(env_path), name, value)
            return "env"
        except Exception as exc:  # type only: never put the value in a message
            reason = f"writing {env_path.name} failed ({type(exc).__name__})"
    else:
        reason = f"{env_path.name} does not exist (credentials come from real environment variables?)"

    parked = pending_path(env_path, name)
    try:
        parked.write_text(value, encoding="utf-8")
        warnings.warn(
            f"{name} was rotated but {reason}. The new value was saved to {parked}; "
            f"copy it into {env_path.name} (or your secrets store) and delete that file. "
            f"The old {name} no longer works.",
            RuntimeWarning,
            stacklevel=2,
        )
        return "pending"
    except Exception as exc:
        warnings.warn(
            f"{name} was rotated but {reason}, and the fallback file {parked} could not be "
            f"written either ({type(exc).__name__}). The new value exists only in this "
            f"process. The old {name} no longer works; re-create the credential "
            f"(see SETUP.md).",
            RuntimeWarning,
            stacklevel=2,
        )
        return "none"
