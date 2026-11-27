"""Optional native English grammar backend."""

from types import ModuleType


def load_harper() -> ModuleType:
    """Imports Harper or raises an explicit error when the wheel is absent."""
    try:
        import harper
    except ImportError as error:
        raise RuntimeError("Install harper-py to use the Harper backend") from error
    return harper
