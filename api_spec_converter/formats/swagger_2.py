"""Swagger 2.0 (OpenAPI 2.0) format handler."""
import copy
import re
# import jsonschema # Will be used for validation, equivalent to sway
# from swagger_spec_validator import validate_spec # A potential library for validation
# For jsonschema, we might need a specific swagger 2.0 schema.
# swagger_spec_validator can also be an option.

from api_spec_converter.base_format import BaseFormat
from api_spec_converter.formats import register_format
# from api_spec_converter.utils import parse_json, parse_yaml # Assuming these will be in utils

# TODO: Find or implement a robust Python equivalent of the 'swagger2openapi' library.
# This is a placeholder for the actual conversion logic.
def swagger2_to_openapi3_converter(swagger2_instance: 'Swagger2Format',
                                   passthrough_options: dict = None) -> dict:
    """
    Converts a Swagger 2.0 specification object to an OpenAPI 3.0.x dictionary.

    This is a placeholder for a complex conversion. A library like `swagger2openapi`
    in JavaScript handles many edge cases and transformations. A Python equivalent
    would be needed for a full, correct conversion.

    Args:
        swagger2_instance (Swagger2Format): An instance of Swagger2Format containing the spec.
        passthrough_options (dict, optional): Options for the converter. Not used in placeholder.

    Returns:
        dict: The converted OpenAPI 3.0.x specification as a dictionary.
    """
    print("Warning: swagger_2 to openapi_3 conversion is a basic placeholder and not fully implemented.")
    if not swagger2_instance.spec:
        return {"openapi": "3.0.0", "info": {"title": "Empty Spec", "version": "1.0.0"}, "paths": {}}

    # Naive copy and basic field mapping
    converted_spec = copy.deepcopy(swagger2_instance.spec)

    converted_spec['openapi'] = '3.0.0'
    converted_spec.pop('swagger', None) # Remove Swagger 2.0 version field

    # Basic transformations (very simplified):
    # Host, basePath, schemes -> servers
    servers = []
    host = converted_spec.pop('host', None)
    base_path = converted_spec.pop('basePath', '/')
    schemes = converted_spec.pop('schemes', ['http'])

    if host:
        for scheme in schemes:
            servers.append({'url': f"{scheme}://{host}{base_path}"})
    elif base_path != '/': # If only basePath is there (e.g. /v2)
         servers.append({'url': base_path})

    if not servers and swagger2_instance.source_type == 'url' and swagger2_instance.source:
        # Try to infer from original source URL if no host/schemes
        from urllib.parse import urlparse
        parsed_source_url = urlparse(swagger2_instance.source)
        if parsed_source_url.scheme and parsed_source_url.netloc:
             servers.append({'url': f"{parsed_source_url.scheme}://{parsed_source_url.netloc}{base_path}"})

    if not servers: # Fallback if no other info
        servers.append({'url': base_path if base_path.startswith('/') else '/'}) # Default server URL

    converted_spec['servers'] = servers

    # consumes/produces -> requestBody/responses content types (complex mapping)
    global_consumes = converted_spec.pop('consumes', None)
    global_produces = converted_spec.pop('produces', None)

    if 'paths' in converted_spec:
        for path_item in converted_spec['paths'].values():
            if isinstance(path_item, dict):
                for operation in path_item.values():
                    if isinstance(operation, dict):
                        # Handle consumes -> requestBody content
                        operation_consumes = operation.pop('consumes', global_consumes)
                        if operation_consumes:
                            body_param = next((p for p in operation.get('parameters', []) if p.get('in') == 'body'), None)
                            if body_param and 'schema' in body_param:
                                if 'requestBody' not in operation:
                                    operation['requestBody'] = {'content': {}}
                                for media_type in operation_consumes:
                                    operation['requestBody']['content'][media_type] = {'schema': body_param['schema']}
                                if body_param.get('description'):
                                     operation['requestBody']['description'] = body_param['description']
                                if body_param.get('required'):
                                     operation['requestBody']['required'] = body_param['required']
                                # Remove original body parameter
                                operation['parameters'] = [p for p in operation.get('parameters', []) if p.get('in') != 'body']
                                if not operation['parameters']:
                                    operation.pop('parameters')


                        # Handle produces -> responses content
                        operation_produces = operation.pop('produces', global_produces)
                        if operation_produces and 'responses' in operation:
                            for response in operation['responses'].values():
                                if isinstance(response, dict) and 'schema' in response:
                                    schema = response.pop('schema')
                                    response['content'] = {}
                                    for media_type in operation_produces:
                                        response['content'][media_type] = {'schema': schema}

    # definitions -> components.schemas
    if 'definitions' in converted_spec:
        if 'components' not in converted_spec:
            converted_spec['components'] = {}
        converted_spec['components']['schemas'] = converted_spec.pop('definitions')

    # parameters -> components.parameters (for top-level parameters)
    if 'parameters' in converted_spec: # Swagger 2.0 top-level parameters
        if 'components' not in converted_spec:
            converted_spec['components'] = {}
        converted_spec['components']['parameters'] = converted_spec.pop('parameters')

    # responses -> components.responses
    if 'responses' in converted_spec: # Swagger 2.0 top-level responses
        if 'components' not in converted_spec:
            converted_spec['components'] = {}
        converted_spec['components']['responses'] = converted_spec.pop('responses')

    # securityDefinitions -> components.securitySchemes
    if 'securityDefinitions' in converted_spec:
        if 'components' not in converted_spec:
            converted_spec['components'] = {}
        converted_spec['components']['securitySchemes'] = converted_spec.pop('securityDefinitions')
        # TODO: Transform security scheme objects (e.g., type 'basic' to 'http' with scheme 'basic')

    # Further transformations (e.g., parameter types, collectionsFormat) are needed.
    return converted_spec


@register_format("swagger_2")
class Swagger2Format(BaseFormat):
    """
    Handles Swagger 2.0 (OpenAPI 2.0) formatted API specifications.

    This class provides methods to read, parse, validate, fix, and convert
    Swagger 2.0 specifications. It inherits common functionalities from
    `BaseFormat`.
    """
    def __init__(self, spec: dict = None):
        """
        Initializes the Swagger2Format instance.

        Args:
            spec (dict, optional): The Swagger 2.0 specification data. Defaults to None.
        """
        super().__init__(spec)
        self.converters = {
            "openapi_3": swagger2_to_openapi3_converter,
        }

    @property
    def format_name(self) -> str:
        """The canonical name of this format."""
        return "swagger_2"

    @property
    def supported_versions(self) -> list[str]:
        """A list of supported Swagger/OpenAPI versions for this handler."""
        return ["2.0"]

    def get_format_version(self) -> str:
        """
        Extracts and returns the version string from the loaded Swagger 2.0 specification.

        Returns:
            str: The version string (e.g., "2.0").

        Raises:
            ValueError: If the 'swagger' version field is not found in the spec.
        """
        if self.spec and "swagger" in self.spec:
            return str(self.spec["swagger"])
        raise ValueError("Swagger 2.0 version field ('swagger') not found in specification.")

    def check_format(self, spec_data: dict) -> bool:
        """
        Checks if the provided data appears to be a Swagger 2.0 specification.

        It verifies the presence of the 'swagger' field and that its value is "2.0".

        Args:
            spec_data (dict): The specification data to check.

        Returns:
            bool: True if the data is likely Swagger 2.0, False otherwise.
        """
        if not isinstance(spec_data, dict) or "swagger" not in spec_data:
            return False
        return str(spec_data["swagger"]) == "2.0"

    def fix_spec(self):
        """
        Applies common fixes and normalizations to the Swagger 2.0 specification.

        Modifies `self.spec` in-place. Fixes include:
        - Ensuring `info.version` is a string.
        - Inferring `host` and `schemes` if the source was a URL and they are missing.
        - Normalizing `basePath` (ensuring it starts with '/', removing trailing '/').
        - Removing deprecated 'id' fields from definitions.
        """
        if not self.spec:
            return

        # Ensure info.version is a string
        if "info" in self.spec and isinstance(self.spec["info"], dict) and \
           "version" in self.spec["info"]:
            version = self.spec["info"]["version"]
            if not isinstance(version, str):
                self.spec["info"]["version"] = str(version)

        # If source was a URL, try to infer host and schemes
        if self.source_type == 'url' and self.source:
            from urllib.parse import urlparse
            parsed_url = urlparse(self.source)
            if "host" not in self.spec and parsed_url.netloc:
                self.spec["host"] = parsed_url.netloc
            if ("schemes" not in self.spec or not self.spec["schemes"]) and parsed_url.scheme:
                self.spec["schemes"] = [parsed_url.scheme]

        # Ensure schemes is a list if present
        if "schemes" in self.spec and not isinstance(self.spec["schemes"], list):
            self.spec.pop("schemes") # Or try to convert if it's a string? For now, remove if malformed.


        # Normalize basePath
        if "basePath" in self.spec and isinstance(self.spec["basePath"], str):
            bp = self.spec["basePath"].strip()
            if not bp: # If basePath becomes empty after strip, remove it or set to "/"
                self.spec["basePath"] = "/"
            else:
                if not bp.startswith("/"):
                    bp = "/" + bp
                # Trailing slash removal is debatable for Swagger 2.0 basePath,
                # but often done for consistency. Let's keep it if it's not just "/".
                if bp != "/" and bp.endswith("/"):
                    bp = bp[:-1]
                self.spec["basePath"] = bp

        # Remove 'id' fields from definitions
        if "definitions" in self.spec and isinstance(self.spec["definitions"], dict):
            for def_obj in self.spec["definitions"].values():
                if isinstance(def_obj, dict) and "id" in def_obj:
                    del def_obj["id"]

        # TODO: Consider using remove_none_values from utils if that's desired behavior from original.
        # from api_spec_converter.utils.utils import remove_none_values
        # remove_none_values(self.spec)

    def fill_missing(self, dummy_data: dict = None):
        """
        Fills missing required fields in the Swagger 2.0 spec with dummy data.

        Modifies `self.spec` in-place. Required fields like `info`, `swagger`, `paths`
        are ensured.

        Args:
            dummy_data (dict, optional): Custom dummy data to merge. If None,
                                         default dummy data is used.
        """
        default_dummy_data = {
            "swagger": "2.0",
            "info": {
                "title": "< An API title here >",
                "version": "1.0.0"
            },
            "paths": {}
        }

        current_dummy_data = dummy_data or default_dummy_data

        if not self.spec:
            self.spec = copy.deepcopy(current_dummy_data)
            return

        # Ensure top-level required fields from dummy_data are present
        for key, value in current_dummy_data.items():
            if key not in self.spec:
                self.spec[key] = copy.deepcopy(value)
            elif isinstance(value, dict) and isinstance(self.spec.get(key), dict):
                # Recursively fill for nested dictionaries like 'info'
                for sub_key, sub_value in value.items():
                    if sub_key not in self.spec[key]:
                        self.spec[key][sub_key] = copy.deepcopy(sub_value)

        # Explicitly ensure core fields if somehow missed by generic merge
        if "swagger" not in self.spec:
            self.spec["swagger"] = current_dummy_data["swagger"]
        if "info" not in self.spec:
            self.spec["info"] = copy.deepcopy(current_dummy_data["info"])
        elif not isinstance(self.spec["info"], dict): # Ensure info is a dict
             self.spec["info"] = copy.deepcopy(current_dummy_data["info"])
        else: # Ensure title and version within info
            if "title" not in self.spec["info"]:
                self.spec["info"]["title"] = current_dummy_data["info"]["title"]
            if "version" not in self.spec["info"]:
                 self.spec["info"]["version"] = current_dummy_data["info"]["version"]
        if "paths" not in self.spec:
            self.spec["paths"] = {}


    def validate(self) -> dict:
        """
        Validates the Swagger 2.0 specification.

        This method should use a dedicated Swagger/OpenAPI validation library.
        Currently, it's a placeholder.

        Returns:
            dict: A dictionary with "errors" and "warnings" lists.
                  Example: `{"errors": ["Error message"], "warnings": None}`
        """
        # Placeholder: Implement validation using a library like swagger-spec-validator
        # try:
        #     from swagger_spec_validator import validate_spec_url, validate_spec
        #     # If self.source is a URL and spec wasn't modified much, validate_spec_url might be better
        #     # For an in-memory spec dict:
        #     validate_spec(self.spec)
        #     return {"errors": None, "warnings": None}
        # except Exception as e: # Catch specific validation errors from the library
        #     # Format 'e' to be a list of error messages/objects
        #     return {"errors": [str(e)], "warnings": None}

        print("Warning: Swagger 2.0 validation is a placeholder and not fully implemented.")
        return {"errors": None, "warnings": None} # Default: no errors

    def list_sub_resources(self) -> dict:
        """
        Identifies external JSON References (`$ref`) in the Swagger 2.0 specification.

        This is a placeholder. A full implementation requires recursively traversing
        the specification object to find all dictionary items like `{"$ref": "uri"}`
        where "uri" points to an external resource.

        Returns:
            dict: A dictionary mapping unique reference identifiers (e.g., the `$ref` value
                  itself or a JSON pointer to its location) to the external URI.
                  Example: `{"./common/schemas.json#/User": "./common/schemas.json"}`
        """
        # TODO: Implement robust $ref discovery.
        # This requires a recursive traversal of self.spec.
        # For each dict, if a "$ref" key exists and its value is an external URI (not starting with '#'),
        # it should be added to the map. The key in the map could be the ref string itself
        # or a JSON pointer to its location.
        # Example:
        #   refs = {}
        #   def find_refs_recursive(obj, current_path):
        #       if isinstance(obj, dict):
        #           for k, v in obj.items():
        #               if k == "$ref" and isinstance(v, str) and not v.startswith("#"):
        #                   # Need to resolve v relative to self.source if applicable
        #                   refs[f"{current_path}/$ref"] = v # Store with JSON pointer like path
        #               else:
        #                   find_refs_recursive(v, f"{current_path}/{k}")
        #       elif isinstance(obj, list):
        #           for i, item in enumerate(obj):
        #               find_refs_recursive(item, f"{current_path}/{i}")
        #   find_refs_recursive(self.spec, "#")
        print("Warning: list_sub_resources for Swagger 2.0 is a placeholder.")
        return {}
