"""OpenAPI 3.0.x format handler."""
import copy
# import jsonschema # For validation with OpenAPI 3.0 schema
# from openapi_spec_validator import validate_spec # A potential library for validation

from api_spec_converter_py.base_format import BaseFormat
from api_spec_converter_py.formats import register_format
# from api_spec_converter_py.utils import parse_json, parse_yaml

# TODO: Find or implement a robust Python equivalent for OpenAPI 3 to Swagger 2 conversion.
# This is a placeholder for the actual conversion logic.
def openapi3_to_swagger2_converter(openapi3_instance: 'OpenAPI3Format',
                                   passthrough_options: dict = None) -> dict:
    """
    Converts an OpenAPI 3.0.x specification object to a Swagger 2.0 dictionary.

    This is a placeholder for a very complex conversion. Libraries exist in other
    languages (e.g., `openapi-to-swagger` in JS). A Python equivalent would involve
    mapping many OpenAPI 3 features back to Swagger 2.0 limitations or structures.

    Args:
        openapi3_instance (OpenAPI3Format): An instance of OpenAPI3Format containing the spec.
        passthrough_options (dict, optional): Options for the converter. Not used in placeholder.

    Returns:
        dict: The converted Swagger 2.0 specification as a dictionary.
    """
    print("Warning: openapi_3 to swagger_2 conversion is a basic placeholder and not fully implemented.")
    if not openapi3_instance.spec:
        return {"swagger": "2.0", "info": {"title": "Empty Spec", "version": "1.0.0"}, "paths": {}}

    converted_spec = copy.deepcopy(openapi3_instance.spec)

    converted_spec['swagger'] = '2.0'
    converted_spec.pop('openapi', None) # Remove OpenAPI version

    # Basic transformations (very simplified):
    # servers -> host, basePath, schemes
    # Takes the first server object for simplicity. A real conversion would be more nuanced.
    servers = converted_spec.pop('servers', [])
    if servers and isinstance(servers, list) and servers[0].get('url'):
        from urllib.parse import urlparse
        first_server_url = servers[0]['url']
        parsed_url = urlparse(first_server_url)

        converted_spec['host'] = parsed_url.netloc or None
        base_path = parsed_url.path
        # Ensure basePath starts with / and remove if it's just "/" and host is present
        if not base_path.startswith("/"): base_path = "/" + base_path
        if converted_spec['host'] and base_path == "/":
             converted_spec['basePath'] = None # Or prefer to keep it as "/"? Swagger tools vary.
        else:
            converted_spec['basePath'] = base_path if base_path else "/"

        if parsed_url.scheme:
            converted_spec['schemes'] = [parsed_url.scheme]
        else: # Default if scheme is missing
            converted_spec['schemes'] = ['http']
    else: # Fallback if no servers or URL
        converted_spec['host'] = None
        converted_spec['basePath'] = "/"
        converted_spec['schemes'] = ['http']

    # Remove None values for cleaner Swagger 2.0 output if host was not found
    if converted_spec['host'] is None: converted_spec.pop('host')
    if converted_spec['basePath'] is None: converted_spec.pop('basePath')


    # components -> definitions, parameters, responses, securityDefinitions
    components = converted_spec.pop('components', {})
    if 'schemas' in components:
        converted_spec['definitions'] = components['schemas']
    if 'parameters' in components:
        # Swagger 2.0 top-level parameters are simpler than OpenAPI 3 components.parameters
        converted_spec['parameters'] = components['parameters']
    if 'responses' in components:
        converted_spec['responses'] = components['responses']
    if 'securitySchemes' in components:
        converted_spec['securityDefinitions'] = components['securitySchemes']
        # TODO: Transform security scheme objects (e.g., type 'http' to 'basic', 'apiKey', etc.)

    # requestBody -> body parameter (complex transformation)
    # This requires iterating through paths and operations.
    if 'paths' in converted_spec:
        for path_item in converted_spec['paths'].values():
            if isinstance(path_item, dict):
                for op_name, operation in path_item.items():
                    if isinstance(operation, dict) and 'requestBody' in operation:
                        request_body = operation.pop('requestBody')
                        if 'content' in request_body:
                            # Take the first content type's schema for simplicity
                            first_content_type = next(iter(request_body['content']))
                            if first_content_type and 'schema' in request_body['content'][first_content_type]:
                                body_param = {
                                    'name': 'body', # Default name for body parameter
                                    'in': 'body',
                                    'schema': request_body['content'][first_content_type]['schema']
                                }
                                if request_body.get('description'):
                                    body_param['description'] = request_body['description']
                                if request_body.get('required'):
                                    body_param['required'] = request_body['required']

                                if 'parameters' not in operation:
                                    operation['parameters'] = []
                                operation['parameters'].append(body_param)

                    # Media type handling in responses: Swagger 2 produces/consumes vs OpenAPI content map
                    if isinstance(operation, dict) and 'responses' in operation:
                        global_produces = converted_spec.get('produces', [])
                        for resp_code, response_obj in operation.get('responses', {}).items():
                             if isinstance(response_obj, dict) and 'content' in response_obj:
                                first_content_key = next(iter(response_obj['content']), None)
                                if first_content_key:
                                    # Use schema from the first content type found
                                    response_obj['schema'] = response_obj['content'][first_content_key].get('schema')
                                    # Add this content type to global produces if not there
                                    if first_content_key not in global_produces:
                                        global_produces.append(first_content_key)
                                response_obj.pop('content') # Remove OpenAPI 3 content structure
                        if global_produces and 'produces' not in converted_spec : # Set global produces if derived
                            converted_spec['produces'] = list(set(global_produces)) # Unique list


    # Ensure info and paths (even if empty) are present as they are required in Swagger 2.0
    if 'info' not in converted_spec:
        converted_spec['info'] = {'title': 'Converted API', 'version': '1.0.0'}
    if 'paths' not in converted_spec:
        converted_spec['paths'] = {}

    return converted_spec


@register_format("openapi_3")
class OpenAPI3Format(BaseFormat):
    """
    Handles OpenAPI 3.0.x formatted API specifications.

    This class provides methods to read, parse, validate, fix, and convert
    OpenAPI 3.0.x specifications. It inherits common functionalities from
    `BaseFormat`.
    """
    def __init__(self, spec: dict = None):
        """
        Initializes the OpenAPI3Format instance.

        Args:
            spec (dict, optional): The OpenAPI 3.0.x specification data. Defaults to None.
        """
        super().__init__(spec)
        self.converters = {
            "swagger_2": openapi3_to_swagger2_converter,
        }

    @property
    def format_name(self) -> str:
        """The canonical name of this format."""
        return "openapi_3"

    @property
    def supported_versions(self) -> list[str]:
        """A list of supported OpenAPI versions for this handler (e.g., "3.0.0", "3.0.1")."""
        return ["3.0.0", "3.0.1", "3.0.2", "3.0.3"] # Add "3.1.0" etc. as support is added

    def get_format_version(self) -> str:
        """
        Extracts and returns the version string from the loaded OpenAPI 3.0.x specification.

        Returns:
            str: The version string (e.g., "3.0.1").

        Raises:
            ValueError: If the 'openapi' version field is not found in the spec.
        """
        if self.spec and "openapi" in self.spec:
            return str(self.spec["openapi"])
        raise ValueError("OpenAPI 3.x version field ('openapi') not found in specification.")

    def check_format(self, spec_data: dict) -> bool:
        """
        Checks if the provided data appears to be an OpenAPI 3.0.x specification.

        Verifies the presence of the 'openapi' field and that its value starts with "3.0.".

        Args:
            spec_data (dict): The specification data to check.

        Returns:
            bool: True if the data is likely OpenAPI 3.0.x, False otherwise.
        """
        return (isinstance(spec_data, dict) and
                "openapi" in spec_data and
                isinstance(spec_data["openapi"], str) and
                (spec_data["openapi"].startswith("3.0.") or spec_data["openapi"].startswith("3.1."))) # Future proof for 3.1

    def fix_spec(self):
        """
        Applies common fixes and normalizations to the OpenAPI 3.0.x specification.

        Modifies `self.spec` in-place. Fixes include:
        - Ensuring `info.version` is a string.
        - Ensuring a default `servers` array exists if none is provided.
        """
        if not self.spec:
            return

        # Ensure info.version is a string
        if "info" in self.spec and isinstance(self.spec["info"], dict) and \
           "version" in self.spec["info"]:
            version = self.spec["info"]["version"]
            if not isinstance(version, str):
                self.spec["info"]["version"] = str(version)

        # Ensure 'servers' array exists and has at least one entry, as it's recommended.
        # OpenAPI 3.0.x spec says: "If the servers property is not provided, or is an empty array,
        # the default value would be a Server Object with a url value of '/'. "
        # So, we can either rely on tools to interpret this default, or explicitly add it.
        # For consistency and to help tools that might not infer, let's add it if missing/empty.
        if 'servers' not in self.spec or not self.spec['servers']:
            self.spec['servers'] = [{'url': '/'}]

    def fill_missing(self, dummy_data: dict = None):
        """
        Fills missing required fields in the OpenAPI 3.0.x spec with dummy data.

        Modifies `self.spec` in-place. Required fields like `openapi`, `info`, `paths`,
        and a default `servers` entry are ensured.

        Args:
            dummy_data (dict, optional): Custom dummy data to merge. If None,
                                         default dummy data is used.
        """
        default_dummy_data = {
            "openapi": self.supported_versions[0] if self.supported_versions else "3.0.0", # Default to first supported
            "info": {
                "title": "< An API title here >",
                "version": "1.0.0"
            },
            "paths": {},
            "servers": [{"url": "/"}]
        }

        current_dummy_data = dummy_data or default_dummy_data


        if not self.spec:
            self.spec = copy.deepcopy(current_dummy_data)
            return

        for key, value in current_dummy_data.items():
            if key not in self.spec:
                self.spec[key] = copy.deepcopy(value)
            elif isinstance(value, dict) and isinstance(self.spec.get(key), dict):
                # Recursively fill for nested dictionaries like 'info'
                for sub_key, sub_value in value.items():
                    if sub_key not in self.spec[key]:
                        self.spec[key][sub_key] = copy.deepcopy(sub_value)

        # Ensure core fields are present and correctly typed
        if "openapi" not in self.spec:
            self.spec["openapi"] = current_dummy_data["openapi"]
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
        if "servers" not in self.spec or not self.spec['servers'] or \
           not (isinstance(self.spec['servers'], list) and all(isinstance(s, dict) for s in self.spec['servers'])):
            self.spec['servers'] = copy.deepcopy(current_dummy_data['servers'])


    def validate(self) -> dict:
        """
        Validates the OpenAPI 3.0.x specification.

        This method should use a dedicated OpenAPI validation library
        (e.g., `openapi-spec-validator`, `openapi-core`). Currently, it's a placeholder.

        Returns:
            dict: A dictionary with "errors" and "warnings" lists.
        """
        # Placeholder: Implement validation using a library like openapi-spec-validator
        # try:
        #     from openapi_spec_validator import validate_spec # Or other relevant function
        #     # For OpenAPI 3.0, the spec itself contains the version, so validate_spec(self.spec) is typical.
        #     # Some validators might allow passing the spec URL if it's from an external source for better
        #     # reference resolution during validation.
        #     validate_spec(self.spec)
        #     return {"errors": None, "warnings": None}
        # except Exception as e: # Catch specific validation errors
        #     return {"errors": [str(e)], "warnings": None}

        print("Warning: OpenAPI 3.0.x validation is a placeholder and not fully implemented.")
        return {"errors": None, "warnings": None} # Default: no errors

    def list_sub_resources(self) -> dict:
        """
        Identifies external JSON References (`$ref`) in the OpenAPI 3.0.x specification.

        This is a placeholder. A full implementation requires recursively traversing
        the specification object.

        Returns:
            dict: A map of reference identifiers to external URIs.
                  Example: `{"#/components/schemas/ExternalModel": "external_models.yaml#/ModelA"}`
        """
        # TODO: Implement robust $ref discovery for OpenAPI 3.0.x.
        # Similar to Swagger2Format, but OpenAPI 3.0.x has more places where $ref can occur.
        print("Warning: list_sub_resources for OpenAPI 3.0.x is a placeholder.")
        return {}
