"""Config service — read and write the application .env file.

Provides get_config() and update_config() for the admin panel's config
management. The .env file is read from the project root (D:\codeProject\aiagentwebgis\.env).
"""

import os
import re
import shutil
from copy import deepcopy
from pathlib import Path
from typing import Any

# Determine the project root (.env location) relative to this file.
# app/services/config_service.py → backend/app/services/ → project root
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_ENV_PATH = _PROJECT_ROOT / ".env"

# Keys whose values should be masked when exposed to the API.
_SECRET_KEYS = {
    "DASHSCOPE_API_KEY", "ONEAPI_API_KEY", "AMAP_API_KEY",
    "JWT_SECRET_KEY", "DB_PASSWORD", "VITE_AMAP_KEY",
}

# Keys that require a backend restart when changed (persistent connections).
_RESTART_KEYS = {
    "DATABASE_URL", "REDIS_URL", "JWT_SECRET_KEY",
}

# Keys that can be hot-updated via the admin API. Everything else (secrets,
# connection strings, anything matching _SECRET_KEYS or _RESTART_KEYS) must
# be edited by hand in the .env file and requires a process restart. This
# prevents an attacker (or a fat-fingered admin) from rotating the JWT secret
# out from under a live deployment or pointing the DB URL at a hostile host.
_ALLOWED_UPDATE_KEYS: frozenset[str] = frozenset({
    "LLM_PROVIDER",
    "LLM_MODEL",
    "LLM_BASE_URL",
    "APP_ENV",
    "DEBUG",
})

# Lower-cased versions for case-insensitive lookup at apply-time.
_ALLOWED_UPDATE_KEYS_LOWER: frozenset[str] = frozenset(
    k.lower() for k in _ALLOWED_UPDATE_KEYS
)
_RESTART_KEYS_LOWER: frozenset[str] = frozenset(
    k.lower() for k in _RESTART_KEYS
)


def _mask(value: str) -> str:
    """Mask a secret value, showing only the last 4 characters.

    Short secrets (<= 8 chars) are fully masked — exposing 4 of 5 chars would
    give an attacker 80% of the secret for trivial offline cracking.
    """
    if not value:
        return ""
    if len(value) <= 8:
        return "****"
    return "****" + value[-4:]


def _parse_env(path: Path) -> dict[str, str]:
    """Parse a .env file into a dict, preserving inline comments."""
    result: dict[str, str] = {}
    if not path.exists():
        return result
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        # Strip inline comment after the value
        # E.g. DB_PASSWORD=changeme  # comment
        content = line.split("#", 1)[0]
        if "=" not in content:
            continue
        key, _, value = content.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        result[key] = value
    return result


def get_config() -> dict[str, Any]:
    """Return the current .env config as a dict.  Secrets are masked."""
    raw = _parse_env(_ENV_PATH)
    result: dict[str, Any] = {}
    for key, value in raw.items():
        if key in _SECRET_KEYS:
            result[key] = {"value": _mask(value), "masked": True}
        else:
            result[key] = {"value": value, "masked": False}
    return result


def update_config(updates: dict[str, str]) -> dict[str, Any]:
    """Merge settings into the .env file and return which keys need restart.

    Refuses to write any key outside ``_ALLOWED_UPDATE_KEYS`` — secrets
    (``JWT_SECRET_KEY``, API keys, DB password) and connection strings
    (``DATABASE_URL``, ``REDIS_URL``) MUST be edited in the .env file by hand
    and require a process restart. This stops a compromised admin account
    from rotating the JWT signing key under a running deployment.

    Args:
        updates: Dictionary of key → new_value to write.

    Returns:
        {"updated": [...], "requires_restart": [...], "rejected": [...]}
    """
    if not _ENV_PATH.exists():
        raise FileNotFoundError(f".env not found at {_ENV_PATH}")

    rejected: list[str] = []
    accepted: dict[str, str] = {}
    for key, value in updates.items():
        if key in _ALLOWED_UPDATE_KEYS:
            accepted[key] = value
        else:
            rejected.append(key)

    # Read current file as raw lines to preserve structure
    lines = _ENV_PATH.read_text(encoding="utf-8").splitlines()
    existing_keys = set()

    # Update existing keys in-place
    new_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            new_lines.append(line)
            continue
        content = stripped.split("#", 1)[0]
        if "=" not in content:
            new_lines.append(line)
            continue
        key = content.split("=", 1)[0].strip()
        if key in accepted:
            existing_keys.add(key)
            inline_comment = ""
            if "#" in stripped:
                inline_comment = " #" + stripped.split("#", 1)[1]
            # Preserve original quoting style if the key already exists and
            # the old value is quoted
            old_value = content.split("=", 1)[1].strip()
            old_was_quoted = (old_value.startswith('"') or old_value.startswith("'"))
            new_value = accepted[key]
            if old_was_quoted:
                new_lines.append(f'{key}="{new_value}"{inline_comment}')
            else:
                new_lines.append(f'{key}={new_value}{inline_comment}')
        else:
            new_lines.append(line)

    # Append new keys that didn't exist in the file
    for key, value in accepted.items():
        if key not in existing_keys:
            new_lines.append(f'{key}={value}')

    # Skip writing the file when nothing was accepted (still report rejections)
    if accepted:
        # Atomic write: write to temp file then rename
        tmp_path = _ENV_PATH.with_suffix(".env.tmp")
        tmp_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
        shutil.move(str(tmp_path), str(_ENV_PATH))

    # NOTE: restart-required keys (DATABASE_URL / REDIS_URL / JWT_SECRET_KEY)
    # are deliberately NOT in _ALLOWED_UPDATE_KEYS — they cannot be hot-changed
    # via the API. So `requires_restart` is always [] in practice. The field
    # is preserved in the response shape so the admin UI can render a generic
    # "changes applied" toast without a special-case branch.
    requires_restart = [
        k for k in accepted if k in _RESTART_KEYS
    ]

    # Reload the pydantic settings singleton so changes take effect immediately
    # for non-restart keys.
    from app.config import settings

    # Use case-insensitive comparison (env keys are uppercase, pydantic attrs
    # are lowercase).  Previous code did a direct `attr not in _RESTART_KEYS`
    # which compared lowercase to uppercase and was ALWAYS True — JWT_SECRET
    # was being hot-swapped via the admin API.
    for key, value in accepted.items():
        attr = key.lower()
        if attr in _RESTART_KEYS_LOWER:
            # Restart-required key — value is on disk but settings stays old
            continue
        if hasattr(settings, attr):
            setattr(settings, attr, value)

    return {
        "updated": list(accepted.keys()),
        "requires_restart": requires_restart,
        "rejected": rejected,
    }
