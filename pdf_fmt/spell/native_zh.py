"""Optional native OpenCC backend for Chinese conversion."""

from types import ModuleType


def load_opencc() -> ModuleType:
    """Imports OpenCC or raises an explicit error when the wheel is absent."""
    try:
        import opencc
    except ImportError as error:
        raise RuntimeError("Install opencc to use the native Chinese backend") from error
    return opencc
