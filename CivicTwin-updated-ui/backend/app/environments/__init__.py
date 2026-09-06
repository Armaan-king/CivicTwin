"""Environment packs: the words and rules one policy area puts on the neutral core.

V1 registers transport and nothing else. Importing this package registers it, so
`registered()` is the honest answer to "what can this run against", not a wish list.

Adding a policy area should be a new module here plus one import line. If it ever
requires editing `app/schemas/core.py`, the seam was not real.
"""
from app.environments.base import EnvironmentPack, get, label, register, registered
from app.environments import transport  # noqa: F401  registers "transport" on import

__all__ = ["EnvironmentPack", "get", "label", "register", "registered"]
