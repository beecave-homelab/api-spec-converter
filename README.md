# API Specification Converter (Python Port)

This project is a Python port of the original Node.js-based [api-spec-converter](https://github.com/LucyBot-Inc/api-spec-converter). It aims to provide similar functionality for converting API specifications between various formats, using Python.

**Current Status:** This port is under development. Core functionality for conversion between Swagger 2.0 and OpenAPI 3.0.x is being implemented.

## Features (Planned/In-Progress)

*   Conversion between various API specification formats:
    *   Swagger 1.x (swagger_1)
    *   OpenAPI (fka Swagger) 2.0 (swagger_2)
    *   OpenAPI 3.0.x (openapi_3)
    *   RAML (raml) - *Planned*
    *   API Blueprint (api_blueprint) - *Planned*
    *   Google API Discovery (google) - *Planned*
    *   WADL (wadl) - *Planned*
    *   I/O Docs (io_docs) - *Planned*
*   Command-line interface (CLI).
*   Library usage for programmatic conversions.
*   Support for JSON and YAML input/output.
*   Option to validate specifications.
*   Option to fill missing required fields with dummy data.

## Installation

```bash
# Ensure you have Python 3.7+ installed
# Clone the repository (if not already done)
# git clone <repository_url>
# cd api-spec-converter-py # Or your project directory name

# It's recommended to use a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install the package (e.g., in editable mode for development)
pip install -e .
```

## Usage

### Command Line

The CLI script `api-spec-converter-py` will be available after installation.

```bash
api-spec-converter-py --help
```

**Example:**

Convert a Swagger 2.0 file to OpenAPI 3.0 YAML:

```bash
api-spec-converter-py --from-format swagger_2 --to-format openapi_3 --syntax yaml path/to/your/swagger_spec.json > openapi_spec.yaml
```

**Options:**

*   `-f, --from-format TEXT`: Specifies the source format (e.g., `swagger_2`, `openapi_3`). (Required)
*   `-t, --to-format TEXT`: Specifies the target output format. (Required)
*   `-s, --syntax [json|yaml]`: Specifies output data syntax (default: `json`).
*   `-o, --order [openapi|alpha|false]`: Specifies top-level field ordering for the output (default: `openapi`).
*   `-c, --check`: Validates the output specification after conversion.
*   `-d, --dummy`: Fills missing required fields in the output with dummy data.
*   `SOURCE`: Path to the input API specification file, a URL, or `-` to read from stdin.

### Library Usage (Planned)

```python
from api_spec_converter_py import APIConverter

# Example (API may change)
# converter = APIConverter()
# try:
#     # Load from a file path
#     swagger_spec = converter.load_spec('path/to/swagger.json', from_format='swagger_2')
#
#     # Convert to OpenAPI 3
#     openapi_spec = swagger_spec.convert_to('openapi_3')
#
#     # Stringify to YAML
#     yaml_output = openapi_spec.stringify(syntax='yaml', order='openapi')
#     print(yaml_output)
#
#     # Or convert directly:
#     # result_spec = converter.convert(
#     # source='path/to/input.json',
#     # from_format='swagger_2',
#     #     to_format='openapi_3'
#     # )
#     # print(result_spec.stringify(syntax='yaml'))
#
# except Exception as e:
#     print(f"An error occurred: {e}")
```

## Development

### Project Structure

*   `api_spec_converter_py/`: Main package directory.
    *   `base_format.py`: Base class for all format handlers.
    *   `cli.py`: Command-line interface script.
    *   `formats/`: Module for specific format handlers (e.g., `swagger_2.py`, `openapi_3.py`).
    *   `utils/`: Utility functions.
*   `tests/`: Unit and integration tests.
*   `setup.py`: Package setup script.
*   `requirements.txt`: Python dependencies.

### Running Tests

```bash
python -m unittest discover -s tests
# Or, if you have specific test files:
# python -m unittest tests.test_cli
# python -m unittest tests.test_base_format
```

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues.
If you plan to add a new format handler, please look at the existing handlers in `api_spec_converter_py/formats/` and the `BaseFormat` class for guidance.

Key areas for contribution:
*   Implementing new format handlers (RAML, API Blueprint, etc.).
*   Improving the accuracy and completeness of existing conversions (Swagger 2 <-> OpenAPI 3).
*   Enhancing validation logic for each format.
*   Adding more comprehensive tests, especially integration tests using real-world specs.
*   Refining the library API for programmatic usage.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file (TODO: Add LICENSE file, assuming MIT based on original).
```
