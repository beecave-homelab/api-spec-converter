"""Base class for API specification format handlers."""
import json
import yaml
import jsonschema # Placeholder, will be used for validation
import requests # Placeholder, will be used for fetching URLs

# An array containing the OpenAPI/Swagger top level attributes for preferred ordering.
# Attributes are listed in a typical desired output order.
# When sorting, items in this list will appear before others, respecting their order here.
# Attributes not found in this list will be sorted alphabetically after these.
ATTR_ORDER = [
    'openapi',          # OpenAPI/Swagger version
    'swagger',          # (Legacy for Swagger 2.0)
    'info',             # Metadata about the API
    'servers',          # Server information (OpenAPI 3.0+)
    'host',             # (Legacy for Swagger 2.0)
    'basePath',         # (Legacy for Swagger 2.0)
    'schemes',          # (Legacy for Swagger 2.0)
    'consumes',         # Default MIME types consumed by the API (Swagger 2.0)
    'produces',         # Default MIME types produced by the API (Swagger 2.0)
    'paths',            # API paths and operations
    'components',       # Reusable components (OpenAPI 3.0+)
    'definitions',      # Schema definitions (Swagger 2.0)
    'parameters',       # Reusable parameters (Swagger 2.0)
    'responses',        # Reusable responses (Swagger 2.0)
    'securityDefinitions', # Security scheme definitions (Swagger 2.0)
    'security',         # Global security requirements
    'tags',             # Tags used by operations
    'externalDocs',     # External documentation
]
# Reversed list for sorting: items with lower index in ATTR_ORDER_REVERSED appear first.
ATTR_ORDER_REVERSED = list(reversed(ATTR_ORDER))


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
        syntax = options.get('syntax', 'json')
        order = options.get('order', 'openapi')

        if not self.spec:
            return ""

        sorted_specs = self.spec
        if order != 'false':
            def sort_dict_recursively(d):
                """Helper to recursively sort dictionaries based on 'order'."""
                if not isinstance(d, dict):
                    return d

                # Sort items: ATTR_ORDER_REVERSED first, then alphabetically for others
                # Items in ATTR_ORDER_REVERSED are sorted by their index in that list.
                # Other items are sorted alphabetically.

                # Separate keys into predefined and others
                predefined_keys = []
                alpha_keys = []

                for k in d.keys():
                    if k in ATTR_ORDER_REVERSED:
                        predefined_keys.append(k)
                    else:
                        alpha_keys.append(k)

                # Sort predefined keys by their order in ATTR_ORDER_REVERSED
                if order == 'openapi':
                    predefined_keys.sort(key=lambda k_item: ATTR_ORDER_REVERSED.index(k_item))
                else: # 'alpha' order for predefined keys too if not 'openapi'
                    predefined_keys.sort()

                alpha_keys.sort() # Sort other keys alphabetically

                # Combine sorted keys
                if order == 'openapi':
                    # For 'openapi' order, predefined come first, then alpha
                    all_sorted_keys = predefined_keys + alpha_keys
                else: # 'alpha' order means all keys are sorted alphabetically together
                    all_sorted_keys = sorted(list(d.keys()))


                return {
                    key: sort_dict_recursively(d[key]) if isinstance(d[key], dict)
                         else [sort_dict_recursively(i) if isinstance(i, dict) else i for i in d[key]] if isinstance(d[key], list)
                         else d[key]
                    for key in all_sorted_keys
                }
            sorted_specs = sort_dict_recursively(self.spec)


        if syntax == "yaml":
            return yaml.safe_dump(sorted_specs, sort_keys=False, allow_unicode=True)
        else: # json
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
            if source.startswith(('http://', 'https://')):
                return 'url'
            elif __import__('os').path.exists(source): # Check if it's a file path
                return 'file'
            else: # Assume it's a string containing the spec content
                return 'string'
        elif isinstance(source, dict): # Check if it's already a Python dict
            return 'object'
        else:
            raise ValueError('Invalid source type. Source must be a URL, file path, string, or dict.')

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
            response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
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
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            raise IOError(f"File not found: {filepath}")
        except Exception as e:
            raise IOError(f"Error reading from file {filepath}: {e}")

    def parse(self, data: str):
        """
        Parses a string containing API specification data (JSON or YAML) into a Python dictionary.

        It first tries to parse as JSON. If that fails, it tries to parse as YAML.

        Args:
            data (str): The string data to parse.

        Returns:
            dict: The parsed API specification as a Python dictionary.

        Raises:
            ValueError: If the data cannot be parsed as either JSON or YAML.
        """
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            try:
                return yaml.safe_load(data)
            except yaml.YAMLError as e:
                raise ValueError(f"Failed to parse data as JSON or YAML: {e}")

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

        if current_source_type == 'url':
            content = self._read_from_url(source)
            # Store the original source URL for context (e.g. resolving relative $refs)
            self.source = source
            self.source_type = 'url'
        elif current_source_type == 'file':
            content = self._read_from_file(source)
            self.source = source
            self.source_type = 'file'
        elif current_source_type == 'string':
            content = source
            self.source = None # No specific path/URL for direct string content
            self.source_type = 'string'
        elif current_source_type == 'object':
            # If it's already an object, no need to read or parse further.
            # The 'source' attribute might be set by the caller if context is needed.
            self.source_type = 'object'
            return source, current_source_type
        else:
            # This case should ideally not be reached due to _get_source_type validation
            raise ValueError(f"Unsupported source type: {current_source_type}")

        return self.parse(content), current_source_type


    def resolve_resources(self, source):
        """
        Resolves the main API specification and its sub-resources (e.g., external $refs).

        This method reads the main spec, checks its format, applies fixes,
        and then attempts to resolve any declared sub-resources.

        Args:
            source (any): The source of the main API specification (URL, file path, string, or dict).

        Returns:
            BaseFormat: The current instance of the format handler, allowing for chaining.

        Raises:
            ValueError: If the spec format is invalid or a version is unsupported.
            IOError: If reading the main spec or sub-resources fails.
        """
        spec_data, source_type_detected = self.read_spec(source)

        # self.source and self.source_type are set within read_spec if source was URL/file/string.
        # If source was an object, self.source might be None unless set externally.
        if source_type_detected == 'object' and self.source is None:
            # If source was an object and we don't have an explicit original source path/URL,
            # it implies the spec was loaded directly as a dict.
            pass


        if not self.check_format(spec_data):
            # Use self.format_name which should be defined by the subclass
            raise ValueError(
                f"Source '{self.source or 'object'}' is not a valid {getattr(self, 'format_name', 'unknown')} format."
            )

        self.spec = spec_data
        # self.source_type is already set by read_spec

        self.resolve_sub_resources() # Modifies self.sub_resources in-place
        self.fix_spec() # Modifies self.spec in-place

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
                print(f"Warning: Could not resolve sub-resource '{ref_identifier}' from '{source_uri}': {e}")
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
        from api_spec_converter_py.formats import FORMAT_REGISTRY

        if target_format_name == self.format_name: # Access format_name via property
            return self # Already in the target format

        converter_func = self.converters.get(target_format_name)
        if not converter_func:
            raise NotImplementedError(
                f"Conversion from {self.format_name} to {target_format_name} is not supported."
            )

        # The converter function should return the raw converted spec data (dict)
        converted_spec_data = converter_func(self, passthrough_options)

        if target_format_name not in FORMAT_REGISTRY:
            raise ValueError(f"Target format '{target_format_name}' is not registered in FORMAT_REGISTRY.")

        TargetFormatClass = FORMAT_REGISTRY[target_format_name]
        # Initialize the target format instance with the converted data
        target_spec_instance = TargetFormatClass(converted_spec_data)

        # Set source context for the new instance if relevant (e.g., if conversion implies a new base)
        # target_spec_instance.source = self.source # Or some derivative
        # target_spec_instance.source_type = self.source_type

        target_spec_instance.fix_spec() # Apply any necessary fixes for the target format

        return target_spec_instance

    def convert_transitive(self, intermediary_formats: list[str], passthrough_options=None):
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
            current_spec_instance = current_spec_instance.convert_to(target_format_name, passthrough_options)
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
        raise NotImplementedError("Subclasses must define their supported_versions property.")

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
    'tags',
    'security',
    'securityDefinitions',
    'responses',
    'parameters',
    'definitions',
    'components',
    'paths',
    'produces',
    'consumes',
    'schemes',
    'basePath',
    'host',
    'servers',
    'info',
    'swagger',
    'openapi',
]

class BaseFormat:
    def __init__(self, spec=None):
        self.spec = spec
        self.format_name = "base_format"
        self.converters = {}

    def stringify(self, options=None):
        options = options or {}
        syntax = options.get('syntax', 'json')
        order = options.get('order', 'openapi')

        if order == 'false':
            sorted_specs = self.spec
        else:
            def sort_key(item):
                key = item[0]
                if order != 'alpha' and key in ATTR_ORDER:
                    return ATTR_ORDER.index(key)
                return -1  # Items not in ATTR_ORDER or 'alpha' order

            def sort_dict(d):
                if not isinstance(d, dict):
                    return d

                # Separate items based on whether they are in ATTR_ORDER
                ordered_items = []
                alpha_items = []

                for k, v in d.items():
                    if k in ATTR_ORDER:
                        ordered_items.append((k, sort_dict(v) if isinstance(v, dict) else [sort_dict(i) if isinstance(i,dict) else i for i in v] if isinstance(v,list) else v ))
                    else:
                        alpha_items.append((k, sort_dict(v) if isinstance(v, dict) else [sort_dict(i) if isinstance(i,dict) else i for i in v] if isinstance(v,list) else v ))

                # Sort items in ATTR_ORDER by their predefined order (reversed)
                ordered_items.sort(key=lambda item: ATTR_ORDER.index(item[0]), reverse=True)

                # Sort other items alphabetically
                alpha_items.sort(key=lambda item: item[0])

                return dict(ordered_items + alpha_items)

            sorted_specs = sort_dict(self.spec)


        if syntax == "yaml":
            return yaml.safe_dump(sorted_specs, sort_keys=False)
        else:
            return json.dumps(sorted_specs, indent=2)

    def to_dict(self):
        return self.spec

    def _get_source_type(self, source):
        if isinstance(source, str):
            if source.startswith(('http://', 'https://')):
                return 'url'
            elif __import__('os').path.exists(source): # Check if it's a file path
                return 'file'
            else: # Assume it's a string containing the spec content
                return 'string'
        elif isinstance(source, dict): # Check if it's already a Python dict
            return 'object'
        else:
            raise ValueError('Invalid source type. Source must be a URL, file path, string, or dict.')

    def _read_from_url(self, url):
        try:
            response = requests.get(url)
            response.raise_for_status() # Raise an exception for bad status codes
            return response.text
        except requests.exceptions.RequestException as e:
            raise IOError(f"Error reading from URL {url}: {e}")

    def _read_from_file(self, filepath):
        try:
            with open(filepath, 'r') as f:
                return f.read()
        except FileNotFoundError:
            raise IOError(f"File not found: {filepath}")
        except Exception as e:
            raise IOError(f"Error reading from file {filepath}: {e}")

    def parse(self, data: str):
        """
        Tries to parse data as JSON, then as YAML if JSON parsing fails.
        """
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            try:
                return yaml.safe_load(data)
            except yaml.YAMLError as e:
                raise ValueError(f"Failed to parse data as JSON or YAML: {e}")

    def read_spec(self, source):
        """
        Reads the API specification from the given source.
        Source can be a URL, file path, string content, or a Python dictionary.
        Returns the parsed specification as a Python dictionary and the source type.
        """
        self.source_type = self._get_source_type(source)

        if self.source_type == 'url':
            content = self._read_from_url(source)
            self.source = source # Store the original source URL
        elif self.source_type == 'file':
            content = self._read_from_file(source)
            self.source = source # Store the original file path
        elif self.source_type == 'string':
            content = source
            self.source = None # No specific source path/URL for string content
        elif self.source_type == 'object':
            # If it's already an object, no need to read or parse
            return source, self.source_type
        else:
            # This case should ideally not be reached due to _get_source_type validation
            raise ValueError(f"Unsupported source type: {self.source_type}")

        return self.parse(content), self.source_type


    def resolve_resources(self, source):
        """
        Resolves the main specification and its sub-resources.
        """
        spec_data, source_type = self.read_spec(source)

        if not self.check_format(spec_data):
            raise ValueError(f"Source {source} is not a valid {self.format_name} format.")

        self.spec = spec_data
        self.source_type = source_type
        if source_type in ('url', 'file'):
            self.source = source

        self.resolve_sub_resources() # Resolves in-place
        self.fix_spec() # Modifies self.spec in-place

        # version = self.get_format_version() # TODO: Implement get_format_version in subclasses
        # if version not in self.supported_versions:
        #     raise ValueError(f"Unsupported {self.format_name} version: {version}. Supported versions are: {self.supported_versions}")
        return self


    def check_format(self, spec):
        # Basic check, should be overridden by subclasses for specific format validation
        return isinstance(spec, dict)

    def fix_spec(self):
        # Placeholder for format-specific spec fixing. Modifies self.spec in-place.
        pass

    def fill_missing(self):
        # Placeholder for filling missing required fields. Modifies self.spec in-place.
        pass

    def validate(self):
        # Default validation: always valid. Should be overridden by subclasses.
        return {"errors": None, "warnings": None}

    def list_sub_resources(self):
        # Placeholder, should be overridden by subclasses if they support sub-resources.
        return {}

    def resolve_sub_resources(self):
        """
        Resolves sub-resources (like $ref in OpenAPI) and stores them in self.sub_resources.
        This is a simplified version. Actual implementation might need to handle
        different types of references and fetching strategies.
        """
        self.sub_resources = {}
        sub_resource_sources = self.list_sub_resources() # Get a map of {ref_path: source_url_or_path}

        for ref_path, source in sub_resource_sources.items():
            try:
                # We assume sub_resources are complete specs themselves or parts that can be parsed.
                # This might need to be more sophisticated, e.g. handling relative paths.
                spec_data, _ = self.read_spec(source)
                self.sub_resources[ref_path] = spec_data
            except Exception as e:
                # Handle or log errors in resolving sub-resources
                print(f"Warning: Could not resolve sub-resource {ref_path} from {source}: {e}")
        return self


    def convert_to(self, target_format_name: str, passthrough_options=None):
        """
        Converts the current specification to the target format.
        """
        from api_spec_converter_py.formats import FORMAT_REGISTRY # Lazy import to avoid circular dependency

        if target_format_name == self.format_name:
            return self # Already in the target format

        converter_func = self.converters.get(target_format_name)
        if not converter_func:
            raise NotImplementedError(
                f"Conversion from {self.format_name} to {target_format_name} is not supported."
            )

        # The converter function should return the raw converted spec data (dict)
        converted_spec_data = converter_func(self, passthrough_options)

        # Create an instance of the target format class
        if target_format_name not in FORMAT_REGISTRY:
            raise ValueError(f"Target format '{target_format_name}' is not registered.")

        TargetFormatClass = FORMAT_REGISTRY[target_format_name]
        target_spec_instance = TargetFormatClass(converted_spec_data)
        target_spec_instance.fix_spec() # Apply any necessary fixes for the target format

        return target_spec_instance

    def convert_transitive(self, intermediary_formats: list[str], passthrough_options=None):
        """
        Converts the specification through a series of intermediary formats.
        """
        current_spec = self
        for target_format_name in intermediary_formats:
            current_spec = current_spec.convert_to(target_format_name, passthrough_options)
        return current_spec

    # --- Methods to be implemented or overridden by subclasses ---
    @property
    def format_name(self):
        # e.g., "swagger_2", "openapi_3"
        raise NotImplementedError("Subclasses must define their format_name.")

    @property
    def supported_versions(self):
        # e.g., ["2.0"] for Swagger 2.0
        raise NotImplementedError("Subclasses must define their supported_versions.")

    def get_format_version(self):
        # Logic to extract the version from self.spec
        raise NotImplementedError("Subclasses must implement get_format_version.")
