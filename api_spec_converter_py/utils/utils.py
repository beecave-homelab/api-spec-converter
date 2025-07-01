"""Utility functions for the API specification converter."""
import json
import yaml

class ParseError(Exception):
    """Custom exception raised for errors during JSON or YAML parsing."""
    pass

def parse_json(data_string: str) -> dict:
    """
    Parses a JSON formatted string into a Python dictionary.

    Args:
        data_string (str): The JSON string to parse.

    Returns:
        dict: A Python dictionary representing the parsed JSON.

    Raises:
        ParseError: If the string cannot be parsed as JSON.
    """
    try:
        return json.loads(data_string)
    except json.JSONDecodeError as e:
        raise ParseError(f"Failed to parse JSON: {e}")

def parse_yaml(data_string: str) -> dict:
    """
    Parses a YAML formatted string into a Python dictionary.

    Args:
        data_string (str): The YAML string to parse.

    Returns:
        dict: A Python dictionary representing the parsed YAML.

    Raises:
        ParseError: If the string cannot be parsed as YAML.
    """
    try:
        # Using safe_load to avoid arbitrary code execution from malicious YAML.
        return yaml.safe_load(data_string)
    except yaml.YAMLError as e:
        raise ParseError(f"Failed to parse YAML: {e}")

def remove_none_values(obj: any) -> any:
    """
    Recursively removes keys from dictionaries if their value is None.

    This function modifies the input object (dictionary or list containing dictionaries)
    in-place. It traverses nested dictionaries and lists of dictionaries.

    Args:
        obj (any): The object (typically a dictionary or list) from which
                   None values should be removed.

    Returns:
        any: The modified object with None values removed.
    """
    if isinstance(obj, dict):
        # Iterate over a copy of keys because we might modify the dict during iteration.
        for key in list(obj.keys()):
            if obj[key] is None:
                del obj[key]
            else:
                # Recursively call for nested dictionaries or lists.
                remove_none_values(obj[key])
    elif isinstance(obj, list):
        # For lists, iterate through items and apply recursively.
        # Note: This does not remove None items from the list itself,
        # only from dictionaries within the list.
        # If removing None items from list is desired, list comprehension would be:
        # obj[:] = [remove_none_values(item) for item in obj if item is not None]
        # However, current behavior matches typical 'removeNonValues' which focuses on object keys.
        for item in obj:
            remove_none_values(item)
    return obj


# Note: Some utility-like functions from the original `lib/util.js` (e.g., for
# determining source type or reading from URLs/files) have been implemented
# as methods within the `BaseFormat` class (e.g., `_get_source_type`,
# `_read_from_url`, `_read_from_file`, and `parse` which uses the above
# `parse_json`/`parse_yaml`). This was done because they are closely tied to
# the spec loading process of `BaseFormat`. They could be refactored here if
# they gain broader utility outside of `BaseFormat`.

if __name__ == '__main__':
    # Example Usage for testing remove_none_values
    print("Testing remove_none_values:")
    test_dict_1 = {
        "a": 1, "b": None, "c": {"d": "hello", "e": None, "f": [1, None, {"g": 2, "h": None}]},
        "i": None, "j": [None, "world", {"k": None, "l": "visible"}]
    }
    print("Original 1:", test_dict_1)
    remove_none_values(test_dict_1)
    print("Cleaned  1:", test_dict_1)
    # Expected: {'a': 1, 'c': {'d': 'hello', 'f': [1, {'g': 2}]}, 'j': ['world', {'l': 'visible'}]}
    # Correction: List items that are None are not removed by this implementation, only keys in dicts.
    # Expected based on current code: {'a': 1, 'c': {'d': 'hello', 'f': [1, None, {'g': 2}]}, 'j': [None, 'world', {'l': 'visible'}]}


    test_dict_2_yaml_str = """
    name: Test API
    version: 1.0
    description: null
    contact:
      name: API Support
      email: null # This should be removed
      url: http://example.com
    tags:
      - name: General
        description: null # This should be removed
      - name: Users
        description: User operations
    paths:
      /test:
        get:
          summary: Test endpoint
          deprecated: null # This key should be removed if value is null
          parameters:
            - name: limit
              in: query
              description: null # This key should be removed
              required: false
              schema:
                type: integer
    """
    print("\nTesting with YAML structure:")
    parsed_yaml_data = parse_yaml(test_dict_2_yaml_str)
    print("Original parsed YAML:", json.dumps(parsed_yaml_data, indent=2))
    remove_none_values(parsed_yaml_data)
    print("Cleaned parsed YAML:", json.dumps(parsed_yaml_data, indent=2))
    # Expected 'description: null' and 'deprecated: null' to be removed.
    # And 'email: null' from contact.
    # And 'description: null' from tags.
    # And 'description: null' from parameters.
