"""
API Specification Converter (Python Port)

This package provides tools to convert API specifications between different formats,
such as Swagger 2.0 and OpenAPI 3.0.x. It can be used as a command-line
interface (CLI) or as a Python library.

Core components:
- `BaseFormat`: Base class for all format handlers.
- Format-specific classes (e.g., `Swagger2Format`, `OpenAPI3Format`) in the `formats` module.
- `cli`: The command-line interface module.
- `utils`: Utility functions.

For CLI usage, see `python -m api_spec_converter_py.cli --help`.
For library usage, you would typically import specific format handlers or a
high-level converter class (if one is added later).
"""

# It can be useful to expose some core classes or functions at the package level
# For example, if there was a main converter class:
# from .main_converter import APIConverter

# Or to make format classes easily accessible (though usually imported from .formats)
# from .formats.swagger_2 import Swagger2Format
# from .formats.openapi_3 import OpenAPI3Format

# For now, keeping it minimal as the primary interaction for library users
# would likely be through format classes or a future facade/converter class.

__version__ = "0.1.0" # TODO: Sync with setup.py and cli.py version
