"""Environment loading. Imported first, by everything that reads a variable.

`.env` was gitignored and documented from the start, and nothing ever loaded it. A key
placed there did nothing, silently, which is the worst kind of nothing: the app fell back
to its defaults and looked like it was working.

Search order is deliberate. The real environment wins over the file, so a variable exported
in a shell or set by a deployment is never overridden by a stale line in a checkout.
"""
from __future__ import annotations

import os
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent


def load_env(path: pathlib.Path | None = None) -> list[str]:
    """Read KEY=value lines from .env. Returns the names it set, for logging.

    Deliberately not python-dotenv: the format we use is a dozen lines of KEY=value, and
    the parsing is eight lines. A dependency to read eight lines is a dependency to
    install, pin and explain.
    """
    env_file = path or (ROOT / ".env")
    if not env_file.exists():
        return []

    loaded: list[str] = []
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        # the shell wins: an exported variable is a deliberate act, a file line is a default
        if key and key not in os.environ:
            os.environ[key] = value
            loaded.append(key)
    return loaded


#: Loaded on import, so any module that reads os.environ sees it.
LOADED = load_env()
