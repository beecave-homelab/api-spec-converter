"""
Initializes the formats module for the API Specification Converter.

This module provides:
- `FORMAT_REGISTRY`: A dictionary to store mappings from format names
  (e.g., "swagger_2") to their corresponding format handler classes.
- `register_format`: A decorator function used to register format handler
  classes into the `FORMAT_REGISTRY`.

Format handler modules (like `swagger_2.py`, `openapi_3.py`) should be
imported here to ensure their classes are registered upon package initialization.
"""

FORMAT_REGISTRY: dict[str, type] = {}  # type: ignore[type-arg]


def register_format(name: str):
    """
    A decorator to register format handler classes in the `FORMAT_REGISTRY`.

    Args:
        name (str): The canonical name for the format (e.g., "swagger_2").
                    This name will be used to look up the handler class.

    Returns:
        Callable: The decorator function that registers the class.
    """

    def decorator(cls: type) -> type:  # type: ignore[type-arg]
        """
        Registers the decorated class with the given name.

        Args:
            cls (type): The format handler class to register.

        Returns:
            type: The registered class.
        """
        if name in FORMAT_REGISTRY:
            print(
                f"Warning: Format '{name}' is being re-registered. Overwriting previous entry."
            )
        FORMAT_REGISTRY[name] = cls
        return cls

    return decorator


# Import all available format handler modules here.
# This ensures that each format's @register_format decorator is executed,
# populating the FORMAT_REGISTRY.
from . import swagger_2
from . import openapi_3
# Example for future formats:
# from . import raml
# from . import api_blueprint
# ... etc.
