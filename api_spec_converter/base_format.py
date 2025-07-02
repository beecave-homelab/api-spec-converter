"""Base class for API specification format handlers."""

import json
import yaml
import requests  # Placeholder, will be used for fetching URLs

# An array containing the OpenAPI/Swagger top level attributes for preferred ordering.
# Attributes are listed in a typical desired output order.
# When sorting, items in this list will appear before others, respecting their order here.
# Attributes not found in this list will be sorted alphabetically after these.
ATTR_ORDER = [
    "openapi",  # OpenAPI/Swagger version
    "swagger",  # (Legacy for Swagger 2.0)
    "info",  # Metadata about the API
    "servers",  # Server information (OpenAPI 3.0+)
    "host",  # (Legacy for Swagger 2.0)
    "basePath",  # (Legacy for Swagger 2.0)
    "schemes",  # (Legacy for Swagger 2.0)
    "consumes",  # Default MIME types consumed by the API (Swagger 2.0)
    "produces",  # Default MIME types produced by the API (Swagger 2.0)
    "paths",  # API paths and operations
    "components",  # Reusable components (OpenAPI 3.0+)
    "definitions",  # Schema definitions (Swagger 2.0)
    "parameters",  # Reusable parameters (Swagger 2.0)
    "responses",  # Reusable responses (Swagger 2.0)
    "securityDefinitions",  # Security scheme definitions (Swagger 2.0)
    "security",  # Global security requirements
    "tags",  # Tags used by operations
    "externalDocs",  # External documentation
]


class BaseFormat:
    """
    Base class for handling different API specification formats.

    Provides common functionality for reading, parsing, stringifying, validating,
    and converting API specifications. Subclasses should implement format-specific
    details.

    Attributes:
        spec (dict, optional): The API specification data as a Python dictionary.
        source (str, optional): The original source of the specification (e.g., URL or file path).
        source_type (str, optional): The type of the source (e.g., 'url', 'file', 'string', 'object').
        sub_resources (dict): A dictionary to store resolved sub-resources (e.g., external $refs).
        converters (dict): A dictionary mapping target format names to converter functions.
                           Example: {'openapi_3': self._convert_to_openapi_3_method}
    """

    def __init__(self, spec=None):
        """
        Initializes the BaseFormat instance.

        Args:
            spec (dict, optional): The API specification data. Defaults to None.
        """
        self.spec = spec
        # self.format_name property must be implemented by subclasses
        self.converters = {}
        self.source = None
        self.source_type = None
        self.sub_resources = {}

    def stringify(self, options=None):
        """
        Converts the specification data to a string representation (JSON or YAML).

        Args:
            options (dict, optional): A dictionary of options for stringification.
                'syntax' (str): 'json' or 'yaml'. Defaults to 'json'.
                'order' (str): 'openapi' (uses ATTR_ORDER), 'alpha' (alphabetical),
                               or 'false' (attempts to preserve original order,
                               though dict parsing may alter it). Defaults to 'openapi'.

        Returns:
            str: The stringified API specification.
        """
        options = options or {}
        syntax = options.get("syntax", "json")
        order = options.get("order", "openapi")

        if not self.spec:
            return ""

        sorted_specs = self.spec
        if order != "false":

            def sort_dict_recursively(d):
                """Helper to recursively sort dictionaries based on 'order'."""
                if not isinstance(d, dict):
                    return d

                # Sort items: attributes appearing in ``ATTR_ORDER`` keep that
                # defined order.  Any keys not in that list are appended
                # alphabetically afterwards.  This matches the expectations in
                # the unit-test suite.
                predefined_keys = [k for k in d.keys() if k in ATTR_ORDER]
                other_keys = [k for k in d.keys() if k not in ATTR_ORDER]

                if order == "openapi":
                    # Keep canonical order, then remaining alphabetically.
                    all_sorted_keys = predefined_keys
                    all_sorted_keys.sort(key=ATTR_ORDER.index)  # preserve spec order
                    all_sorted_keys += sorted(other_keys)
                else:  # 'alpha'
                    all_sorted_keys = sorted(d.keys())

                return {
                    key: sort_dict_recursively(d[key])
                    if isinstance(d[key], dict)
                    else [
                        sort_dict_recursively(i) if isinstance(i, dict) else i
                        for i in d[key]
                    ]
                    if isinstance(d[key], list)
                    else d[key]
                    for key in all_sorted_keys
                }

            sorted_specs = sort_dict_recursively(self.spec)

        if syntax == "yaml":
            return yaml.safe_dump(sorted_specs, sort_keys=False, allow_unicode=True)

        return json.dumps(sorted_specs, indent=2, ensure_ascii=False)

    def to_dict(self):
        """
        Returns the raw specification data as a Python dictionary.

        Returns:
            dict: The API specification data.
        """
        return self.spec

    def _get_source_type(self, source):
        """
        Determines the type of the input source.

        Args:
            source (any): The input source, which can be a URL string,
                          file path string, raw content string, or a Python dictionary.

        Returns:
            str: The type of the source ('url', 'file', 'string', 'object').

        Raises:
            ValueError: If the source type is invalid or cannot be determined.
        """
        if isinstance(source, str):
            if source.startswith(("http://", "https://")):
                return "url"
            elif __import__("os").path.exists(source):  # Check if it's a file path
                return "file"
            else:  # Assume it's a string containing the spec content
                return "string"
        elif isinstance(source, dict):  # Check if it's already a Python dict
            return "object"
        else:
            raise ValueError(
                "Invalid source type. Source must be a URL, file path, string, or dict."
            )

    def _read_from_url(self, url):
        """
        Reads content from a URL.

        Args:
            url (str): The URL to read from.

        Returns:
            str: The content read from the URL.

        Raises:
            IOError: If there's an error reading from the URL (e.g., network issue, HTTP error).
        """
        try:
            response = requests.get(url)
            response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
            return response.text
        except requests.exceptions.RequestException as e:
            raise IOError(f"Error reading from URL {url}: {e}")

    def _read_from_file(self, filepath):
        """
        Reads content from a local file.

        Args:
            filepath (str): The path to the file.

        Returns:
            str: The content read from the file.

        Raises:
            IOError: If the file is not found or there's an error reading it.
        """
        try:
            with open(filepath, "r") as f:
                return f.read()
        except FileNotFoundError:
            raise IOError(f"File not found: {filepath}")
        except Exception as e:
            raise IOError(f"Error reading from file {filepath}: {e}")

    def parse(self, data: str):
        """
        Parse data as JSON or YAML and return a dictionary.

        Args:
            data (str): The string data to parse (JSON or YAML).

        Returns:
            dict: The parsed data as a Python dictionary.

        Raises:
            ValueError: If parsing fails or the result is not a mapping.
        """
        # Try JSON first
        try:
            result = json.loads(data)
        except json.JSONDecodeError:
            try:
                result = yaml.safe_load(data)
            except yaml.YAMLError as err:
                raise ValueError(
                    f"Failed to parse data as JSON or YAML: {err}"
                ) from err

        if not isinstance(result, dict):
            raise ValueError(
                "Failed to parse data as JSON or YAML: Parsed result is not an object"
            )

        return result

    def read_spec(self, source):
        """
        Reads the API specification from the given source and parses it.

        The source can be a URL, a file path, a string containing the spec content,
        or a pre-parsed Python dictionary.

        Args:
            source (any): The source of the API specification.

        Returns:
            tuple: A tuple containing:
                - dict: The parsed API specification as a Python dictionary.
                - str: The determined source type ('url', 'file', 'string', 'object').

        Raises:
            ValueError: If the source type is invalid or parsing fails.
            IOError: If reading from a URL or file fails.
        """
        current_source_type = self._get_source_type(source)

        if current_source_type == "url":
            content = self._read_from_url(source)
            # Store the original source URL for context (e.g. resolving relative $refs)
            self.source = source
            self.source_type = "url"
        elif current_source_type == "file":
            content = self._read_from_file(source)
            self.source = source
            self.source_type = "file"
        elif current_source_type == "string":
            content = source
            self.source = None  # No specific path/URL for direct string content
            self.source_type = "string"
        elif current_source_type == "object":
            # If it's already an object, no need to read or parse further.
            # The 'source' attribute might be set by the caller if context is needed.
            self.source_type = "object"
            return source, current_source_type
        else:
            # This case should ideally not be reached due to _get_source_type validation
            raise ValueError(f"Unsupported source type: {current_source_type}")

        return self.parse(content), current_source_type

    def resolve_resources(self, source):
        """
        Reads, parses, and validates the specification from a given source.

        This method orchestrates the loading process:
        1. Reads the raw data from the source (URL, file, string, or dict).
        2. Parses the data into a Python dictionary.
        3. Validates that the data conforms to the expected format.
        4. Resolves any external references (sub-resources).
        5. Performs any necessary format-specific fixes.

        Args:
            source (any): The source of the API specification.

        Returns:
            BaseFormat: The instance of the class, now populated with the spec.

        Raises:
            ValueError: If the source data is not a valid format.
        """
        # Step 1 & 2: Read and Parse the spec
        self.spec, self.source_type = self.read_spec(source)
        self.source = source

        # Step 3: Check if the parsed data is in the expected format
        if not self.check_format(self.spec):
            # Use self.format_name which should be defined by the subclass
            raise ValueError(
                f"Source '{self.source or 'object'}' is not a valid {getattr(self, 'format_name', 'unknown')} format."
            )

        self.resolve_sub_resources()  # Modifies self.sub_resources in-place
        self.fix_spec()  # Modifies self.spec in-place

        version = self.get_format_version()
        if version not in self.supported_versions:
            raise ValueError(
                f"Unsupported {getattr(self, 'format_name', 'unknown')} version: {version}. "
                f"Supported versions are: {self.supported_versions}"
            )
        return self

    def check_format(self, spec_data: dict) -> bool:
        """
        Checks if the given specification data conforms to the expected format.

        This is a basic check. More thorough validation should be done in the `validate` method.
        Subclasses must override this method.

        Args:
            spec_data (dict): The specification data to check.

        Returns:
            bool: True if the data appears to be of the correct format, False otherwise.

        Raises:
            NotImplementedError: If the subclass does not implement this method.
        """
        # Basic check, should be overridden by subclasses for specific format validation
        # Example: return isinstance(spec_data, dict) and "swagger" in spec_data for Swagger 2.0
        raise NotImplementedError("Subclasses must implement check_format.")

    def fix_spec(self):
        """
        Applies any necessary fixes or normalizations to the specification.

        This method modifies `self.spec` in-place.
        Subclasses should override this to implement format-specific fixes.
        """
        # Placeholder for format-specific spec fixing. Modifies self.spec in-place.
        pass

    def fill_missing(self):
        """
        Fills missing required fields in the specification with dummy data.

        This method modifies `self.spec` in-place.
        Subclasses should override this to implement format-specific logic.
        """
        # Placeholder for filling missing required fields. Modifies self.spec in-place.
        pass

    def validate(self) -> dict:
        """
        Validates the specification against its schema or rules.

        Returns:
            dict: A dictionary containing 'errors' and 'warnings' lists.
                  Example: {"errors": ["Error message"], "warnings": ["Warning message"]}
                  Returns {"errors": None, "warnings": None} if validation passes without issues.

        Subclasses should override this method to implement format-specific validation
        (e.g., using jsonschema or a dedicated library like swagger-spec-validator).
        """
        # Default validation: always valid. Should be overridden by subclasses.
        return {"errors": None, "warnings": None}

    def list_sub_resources(self) -> dict:
        """
        Identifies external references (sub-resources) within the specification.

        This method should scan `self.spec` for constructs like `$ref` (in OpenAPI/Swagger)
        that point to external documents and return a mapping of where these references
        are located in the spec to their external source URI.

        Returns:
            dict: A dictionary where keys are paths/identifiers within the spec
                  (e.g., JSON pointers) and values are the URIs of the external resources.
                  Example: {"#/components/schemas/ExternalUser": "./common/user_schema.yaml"}

        Subclasses should override this if their format supports external references.
        """
        # Placeholder, should be overridden by subclasses if they support sub-resources.
        return {}

    def resolve_sub_resources(self):
        """
        Resolves and loads sub-resources identified by `list_sub_resources`.

        This method iterates over the resources listed by `list_sub_resources`,
        reads their content using `read_spec`, and stores the parsed data in
        `self.sub_resources`. It's a basic implementation; more sophisticated error
        handling, circular dependency detection, or relative path resolution based on
        `self.source` might be needed for full $ref support.

        Modifies `self.sub_resources` in-place.

        Returns:
            BaseFormat: The current instance, for chaining.
        """
        self.sub_resources = {}
        sub_resource_sources = self.list_sub_resources()

        for ref_identifier, source_uri in sub_resource_sources.items():
            try:
                # TODO: Handle relative URIs for sub-resources based on self.source (if it's a URL/file)
                # For now, assuming source_uri is absolute or resolvable as is.
                spec_data, _ = self.read_spec(source_uri)
                self.sub_resources[ref_identifier] = spec_data
            except Exception as e:
                # Log or collect warnings about unresolved sub-resources
                # For example, add to a self.warnings list
                print(
                    f"Warning: Could not resolve sub-resource '{ref_identifier}' from '{source_uri}': {e}"
                )
        return self

    def convert_to(self, target_format_name: str, passthrough_options=None):
        """
        Converts the current specification to the specified target format.

        Args:
            target_format_name (str): The name of the target format (e.g., "openapi_3").
            passthrough_options (dict, optional): Options to pass to the underlying
                                                  converter function.

        Returns:
            BaseFormat: An instance of the target format's handler class,
                        containing the converted specification.

        Raises:
            NotImplementedError: If conversion to the target format is not supported.
            ValueError: If the target format name is not registered.
        """
        # Lazy import FORMAT_REGISTRY to avoid circular dependencies at module load time
        from api_spec_converter.formats import FORMAT_REGISTRY

        if target_format_name == self.format_name:  # Access format_name via property
            return self  # Already in the target format

        converter_func = self.converters.get(target_format_name)
        if not converter_func:
            raise NotImplementedError(
                f"Conversion from {self.format_name} to {target_format_name} is not supported."
            )

        # The converter function should return the raw converted spec data (dict)
        converted_spec_data = converter_func(self, passthrough_options)

        if target_format_name not in FORMAT_REGISTRY:
            raise ValueError(
                f"Target format '{target_format_name}' is not registered in FORMAT_REGISTRY."
            )

        TargetFormatClass = FORMAT_REGISTRY[target_format_name]
        # Initialize the target format instance with the converted data
        target_spec_instance = TargetFormatClass(converted_spec_data)

        # Set source context for the new instance if relevant (e.g., if conversion implies a new base)
        # target_spec_instance.source = self.source # Or some derivative
        # target_spec_instance.source_type = self.source_type

        target_spec_instance.fix_spec()  # Apply any necessary fixes for the target format

        return target_spec_instance

    def convert_transitive(
        self, intermediary_formats: list[str], passthrough_options=None
    ):
        """
        Converts the specification through a series of intermediary formats.

        Args:
            intermediary_formats (list[str]): A list of target format names representing
                                              the conversion path.
            passthrough_options (dict, optional): Options to pass to the underlying
                                                  converter functions.

        Returns:
            BaseFormat: An instance of the final target format's handler class.
        """
        current_spec_instance = self
        for target_format_name in intermediary_formats:
            current_spec_instance = current_spec_instance.convert_to(
                target_format_name, passthrough_options
            )
        return current_spec_instance

    # --- Properties and Methods to be implemented or overridden by subclasses ---
    @property
    def format_name(self) -> str:
        """
        The canonical name of the format (e.g., "swagger_2", "openapi_3").
        Subclasses MUST override this property.
        """
        raise NotImplementedError("Subclasses must define their format_name property.")

    @property
    def supported_versions(self) -> list[str]:
        """
        A list of supported version strings for this format (e.g., ["2.0"] for Swagger 2.0).
        Subclasses MUST override this property.
        """
        raise NotImplementedError(
            "Subclasses must define their supported_versions property."
        )

    def get_format_version(self) -> str:
        """
        Extracts and returns the version string from the loaded specification (`self.spec`).
        Subclasses MUST override this method.

        Returns:
            str: The version of the loaded specification.

        Raises:
            ValueError: If the version cannot be determined from the spec.
        """
        raise NotImplementedError("Subclasses must implement get_format_version.")


# ---------------------------------------------------------------------------
# Public attributes expected by the test-suite
# ---------------------------------------------------------------------------

# Alias the dynamic registry so the tests can patch
from api_spec_converter.formats import FORMAT_REGISTRY as _FORMAT_REGISTRY  # noqa: E402  pylint: disable=wrong-import-position

FORMAT_REGISTRY = _FORMAT_REGISTRY  # type: ignore  # makes the symbol re-exported from this module

# Attach the canonical attribute order list to the class for easy access
BaseFormat.ATTR_ORDER = ATTR_ORDER  # type: ignore[attr-defined]
