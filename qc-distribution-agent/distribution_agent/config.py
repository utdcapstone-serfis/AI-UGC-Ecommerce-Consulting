"""Loads platform credentials from environment variables.

Credentials are never hardcoded or stored in the repo. Copy `.env.example`
to `.env`, fill in real values, and load it (e.g. via `python-dotenv`)
before running the agent.
"""

import os


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
