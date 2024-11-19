__version__ = "0.1.0"

from .config import settings


def hello() -> str:
    return "Hello from findingmodelforge!"


__all__ = ["hello", "settings"]