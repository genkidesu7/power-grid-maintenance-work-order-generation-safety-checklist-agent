"""AgentCore Platform v1.0"""

# Shared mock-mode flag resolution — single source of truth for every service.
#
# `USE_MOCK` is the canonical flag tests set. `STG_MOCK_MODE` is what the
# scaffold's deploy-stg CI job actually sets on the shell environment it
# boots uvicorn in (see .claude/rules/implementation_rule.md Rule 1). A
# service that only reads USE_MOCK silently runs its real (non-mock) path
# in deploy-stg, where no env/ secret tree exists — that path then raises
# on the first ctx.secrets.require() call. Both aliases must be checked
# here, once, so every caller inherits the guarantee instead of
# re-deriving it per service.

from __future__ import annotations

import os
from pathlib import Path

from dotenv import dotenv_values

_env: dict[str, str | None] = dotenv_values(Path(__file__).parent.parent.parent / ".env")

_TRUE_VALUES = ("1", "true", "yes")


def _get_flag(key: str) -> str:
    """OS env takes precedence over .env file."""
    return os.environ.get(key) or _env.get(key) or ""


def mock_mode_enabled() -> bool:
    """True if mock mode is on via either accepted alias.

    Checks USE_MOCK (canonical) and STG_MOCK_MODE (deploy-stg CI) —
    feature flags, not credentials, so an os.environ read is allowed.
    """
    return _get_flag("USE_MOCK").lower() in _TRUE_VALUES or _get_flag("STG_MOCK_MODE").lower() in _TRUE_VALUES
