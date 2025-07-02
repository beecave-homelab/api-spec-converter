"""
Command-Line Interface for API Specification Converter.

This module provides a CLI using Click to convert API specifications
between different formats like Swagger 2.0 and OpenAPI 3.0.x.
"""
import click
import sys
import json # For pretty printing validation errors if they are complex objects

from api_spec_converter.formats import FORMAT_REGISTRY
# ATTR_ORDER is not directly used in CLI but defined in BaseFormat for ordering logic
# from api_spec_converter.base_format import ATTR_ORDER

# Ensure all format handlers are imported so they register with FORMAT_REGISTRY.
# The noqa comments are to prevent linters from flagging unused imports if not directly called.
from api_spec_converter.formats import swagger_2 # noqa: F401
from api_spec_converter.formats import openapi_3 # noqa: F401
# Example for future formats:
# from api_spec_converter.formats import raml # noqa: F401


def get_supported_formats() -> list[str]:
    """
    Retrieves a sorted list of currently supported (registered) format names.

    Returns:
        list[str]: A list of format name strings.
    """
    return sorted(list(FORMAT_REGISTRY.keys()))

@click.command(context_settings=dict(help_option_names=['-h', '--help']))
@click.option(
    '--from-format', '-f', 'from_format_name',
    type=click.Choice(get_supported_formats(), case_sensitive=False),
    required=True,
    help='The format of the input API specification.'
)
@click.option(
    '--to-format', '-t', 'to_format_name',
    type=click.Choice(get_supported_formats(), case_sensitive=False),
    required=True,
    help='The target format for the API specification.'
)
@click.option(
    '--syntax', '-s', 'output_syntax',
    type=click.Choice(['json', 'yaml'], case_sensitive=False),
    default='json',
    show_default=True,
    help='The syntax for the output: json or yaml.'
)
@click.option(
    '--order', '-o', 'sort_order',
    type=click.Choice(['openapi', 'alpha', 'false'], case_sensitive=False),
    default='openapi',
    show_default=True,
    help=(
        'The top-level field ordering for the output: '
        '"openapi" (standard OpenAPI/Swagger order as defined in ATTR_ORDER), '
        '"alpha" (alphabetical), or '
        '"false" (no sorting, preserve original if possible, though parsing might alter it).'
    )
)
@click.option(
    '--check', '-c', 'check_output',
    is_flag=True,
    help='Validate the output specification after conversion.'
)
@click.option(
    '--dummy', '-d', 'fill_dummy_data',
    is_flag=True,
    help='Fill missing required fields in the output with dummy data.'
)
@click.argument(
    'source',
    type=click.Path(exists=True, dir_okay=False, allow_dash=True)
    # allow_dash=True allows reading from stdin if source is '-'
    # We might need to adjust exists=True if we want to support URLs directly
    # For now, click.Path is good for files. URLs will need custom handling before this.
    # The original JS tool supports URL, filename, or JS object.
    # The original JS tool supports URL, filename. We adapt to handle URL, filename, or stdin.
    # Click's Path(exists=True) validates files. URLs and stdin are handled before BaseFormat.
)
@click.version_option(version="0.1.0", prog_name="api-spec-converter-py", message="%(prog)s, version %(version)s")
def main(from_format_name: str,
         to_format_name: str,
         output_syntax: str,
         sort_order: str,
         check_output: bool,
         fill_dummy_data: bool,
         source: str):
    """
    Converts API specifications between different formats.

    Supported formats include swagger_2, openapi_3, and others as implemented.

    SOURCE can be a local file path, a URL (http/https), or '-' to read from stdin.
    The output is printed to stdout.
    """

    input_content_or_url = None
    # The 'source' variable from click.argument will be the file path, URL, or '-'.

    if source == '-':
        if sys.stdin.isatty():
            click.echo("Reading from stdin... (Ctrl-D or Ctrl-Z then Enter to end)", err=True)
        input_content_or_url = sys.stdin.read()
        if not input_content_or_url:
            click.echo("Error: No input received from stdin.", err=True)
            sys.exit(1)
    elif source.startswith(('http://', 'https://')):
        # Pass the URL directly; BaseFormat's read_spec will handle fetching.
        input_content_or_url = source
    else:
        # It's a file path; click.Path should have validated its existence.
        try:
            # Use open_file for consistent handling, though reading directly is also fine.
            with click.open_file(source, 'r', encoding='utf-8') as f:
                input_content_or_url = f.read()
        except Exception as e: # Catch potential errors during file read
            click.echo(f"Error reading file {source}: {e}", err=True)
            sys.exit(1)

    if not input_content_or_url: # Should be caught earlier for stdin, but as a safeguard
        click.echo("Error: No input content or source URL provided.", err=True)
        sys.exit(1)

    # Get the class for the 'from' format
    FromFormatClass = FORMAT_REGISTRY.get(from_format_name.lower()) # Ensure lowercase lookup
    if not FromFormatClass:
        # This case should ideally be caught by click.Choice, but as a fallback.
        click.echo(f"Error: Source format '{from_format_name}' is not supported.", err=True)
        sys.exit(1)

    try:
        # 1. Initialize and resolve the source spec.
        # BaseFormat.resolve_resources handles whether input_content_or_url is
        # a URL string, a file path string (if we passed it), or actual content string.
        # Currently, it expects URL or content string.
        from_spec_instance = FromFormatClass()

        # The `source` argument passed to resolve_resources will be used to determine
        # if it's a URL or content. If it's a file path, `read_spec` handles it.
        # Our current `read_spec` in BaseFormat will try `os.path.exists` if it's not a URL.
        # However, we've already read file content. So, we pass the content.
        # The original `source` (filepath/URL) is useful for `BaseFormat` to store as `self.source`.

        # Let BaseFormat know the original source if it was a file or URL, for context.
        if source != '-': # If not stdin, source is the original path/URL
            from_spec_instance.source = source
            from_spec_instance.source_type = from_spec_instance._get_source_type(source)

        from_spec_instance.resolve_resources(input_content_or_url)

        # 2. Convert to the target format
        to_spec_instance = from_spec_instance.convert_to(to_format_name.lower())

        # 3. Optionally fill missing dummy data
        if fill_dummy_data:
            to_spec_instance.fill_missing()

        # 4. Optionally validate the output
        if check_output:
            validation_result = to_spec_instance.validate()
            if validation_result.get("errors"):
                click.echo("Validation Errors:", err=True, color='red')
                click.echo(json.dumps(validation_result["errors"], indent=2), err=True)
            if validation_result.get("warnings"):
                click.echo("Validation Warnings:", err=True, color='yellow')
                click.echo(json.dumps(validation_result["warnings"], indent=2), err=True)
            if not validation_result.get("errors") and not validation_result.get("warnings"):
                click.echo("Validation successful (no errors or warnings).", err=True, color='green')

        # 5. Stringify the output
        output_options = {"syntax": output_syntax, "order": sort_order}
        output_string = to_spec_instance.stringify(output_options)

        click.echo(output_string)

    except ValueError as e: # Includes ParseError from utils if direct parsing fails in BaseFormat
        click.echo(f"Processing Error: {e}", err=True, color='red')
        sys.exit(1)
    except NotImplementedError as e:
        click.echo(f"Functionality Not Implemented: {e}", err=True, color='red')
        sys.exit(1)
    except IOError as e: # Raised by BaseFormat for file/URL read issues
        click.echo(f"Input/Output Error: {e}", err=True, color='red')
        sys.exit(1)
    except Exception as e:
        click.echo(f"An unexpected error occurred: {type(e).__name__} - {e}", err=True, color='red')
        # For debugging, uncomment the following:
        # import traceback
        # click.echo(traceback.format_exc(), err=True)
        sys.exit(1)

if __name__ == '__main__':
    # This allows running the CLI directly using `python -m api_spec_converter_py.cli`
    # or just `python api_spec_converter_py/cli.py` if in the right directory.
    main()
