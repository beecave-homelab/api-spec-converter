import unittest
import json
import yaml
from unittest.mock import patch, mock_open

from api_spec_converter_py.base_format import BaseFormat, ATTR_ORDER

# A very simple concrete implementation of BaseFormat for testing purposes
class ConcreteFormat(BaseFormat):
    @property
    def format_name(self):
        return "concrete_format"

    @property
    def supported_versions(self):
        return ["1.0"]

    def get_format_version(self):
        if self.spec and "version_key" in self.spec:
            return str(self.spec["version_key"])
        return "1.0" # Default if not found for check_format pass

    def check_format(self, spec_data):
        # For testing, assume it's valid if it's a dict and has a 'concrete_marker'
        return isinstance(spec_data, dict) and "concrete_marker" in spec_data

    # Converters are not strictly needed for BaseFormat tests but good for completeness
    def __init__(self, spec=None):
        super().__init__(spec)
        self.converters = {
            "other_format": self._convert_to_other_format
        }

    def _convert_to_other_format(self, current_instance, passthrough_options=None):
        # Dummy converter for testing convert_to
        if not current_instance.spec:
            return {}
        return {"converted": True, "original_spec": current_instance.spec}


class TestBaseFormat(unittest.TestCase):

    def setUp(self):
        self.sample_spec_dict = {
            "info": {"title": "Test API", "version": "1.0"},
            "paths": {"/test": {"get": {"summary": "Test endpoint"}}},
            "swagger": "2.0", # Example: one of the ATTR_ORDER items
            "definitions": {"Pet": {"type": "object"}},
            "z_alpha": "last_alpha",
            "a_alpha": "first_alpha",
            "concrete_marker": True, # For ConcreteFormat's check_format
            "version_key": "1.0"
        }
        self.base_format = ConcreteFormat(self.sample_spec_dict)

    def test_initialization(self):
        self.assertEqual(self.base_format.spec, self.sample_spec_dict)
        self.assertIn("openapi_3", BaseFormat.ATTR_ORDER) # Check ATTR_ORDER is accessible

    def test_stringify_json_default_order(self):
        # Default is 'openapi' order
        output_json_string = self.base_format.stringify()
        output_dict = json.loads(output_json_string)

        keys = list(output_dict.keys())
        # Expected: swagger, info, paths, definitions (from ATTR_ORDER, reversed), then alphabetical
        self.assertTrue(keys.index("swagger") < keys.index("info"))
        self.assertTrue(keys.index("info") < keys.index("paths"))
        self.assertTrue(keys.index("paths") < keys.index("definitions"))
        self.assertTrue(keys.index("definitions") < keys.index("a_alpha")) # a_alpha after ATTR_ORDER items
        self.assertTrue(keys.index("a_alpha") < keys.index("concrete_marker"))
        self.assertTrue(keys.index("concrete_marker") < keys.index("version_key"))
        self.assertTrue(keys.index("version_key") < keys.index("z_alpha"))


        self.assertEqual(output_dict["info"]["title"], "Test API")

    def test_stringify_yaml_default_order(self):
        output_yaml_string = self.base_format.stringify({"syntax": "yaml"})
        output_dict = yaml.safe_load(output_yaml_string)

        keys = list(output_dict.keys())
        # Check order similar to JSON
        self.assertTrue(keys.index("swagger") < keys.index("info"))
        self.assertTrue(keys.index("info") < keys.index("paths"))
        self.assertTrue(keys.index("paths") < keys.index("definitions"))
        self.assertTrue(keys.index("definitions") < keys.index("a_alpha"))
        self.assertTrue(keys.index("a_alpha") < keys.index("concrete_marker"))

        self.assertEqual(output_dict["info"]["title"], "Test API")

    def test_stringify_json_alpha_order(self):
        output_json_string = self.base_format.stringify({"order": "alpha"})
        output_dict = json.loads(output_json_string)
        keys = list(output_dict.keys())
        # Expected: a_alpha, concrete_marker, definitions, info, paths, swagger, version_key, z_alpha
        expected_alpha_order = sorted(self.sample_spec_dict.keys())
        self.assertEqual(keys, expected_alpha_order)

    def test_stringify_yaml_alpha_order(self):
        output_yaml_string = self.base_format.stringify({"syntax": "yaml", "order": "alpha"})
        output_dict = yaml.safe_load(output_yaml_string)
        keys = list(output_dict.keys())
        expected_alpha_order = sorted(self.sample_spec_dict.keys())
        self.assertEqual(keys, expected_alpha_order)

    def test_stringify_json_no_sort_order(self):
        # 'false' order should ideally preserve original insertion order if possible,
        # but dicts pre-3.7 are unordered. json.dumps doesn't guarantee either.
        # This test is more about it not crashing and producing valid JSON.
        # The actual order might vary.
        output_json_string = self.base_format.stringify({"order": "false"})
        output_dict = json.loads(output_json_string)
        self.assertEqual(output_dict["info"]["title"], "Test API")
        self.assertEqual(len(output_dict.keys()), len(self.sample_spec_dict.keys()))

    def test_to_dict(self):
        self.assertEqual(self.base_format.to_dict(), self.sample_spec_dict)

    def test_get_source_type(self):
        bf = ConcreteFormat()
        self.assertEqual(bf._get_source_type("http://example.com/spec.json"), "url")
        self.assertEqual(bf._get_source_type("https://example.com/spec.yaml"), "url")
        # For file, we need to mock os.path.exists
        with patch('os.path.exists', return_value=True):
            self.assertEqual(bf._get_source_type("local_spec.json"), "file")
        with patch('os.path.exists', return_value=False):
            self.assertEqual(bf._get_source_type("just a string"), "string")
        self.assertEqual(bf._get_source_type({"already": "a dict"}), "object")
        with self.assertRaises(ValueError):
            bf._get_source_type(123) # Invalid type

    @patch('requests.get')
    def test_read_from_url_success(self, mock_get):
        mock_response = mock_get.return_value
        mock_response.status_code = 200
        mock_response.text = '{"url_spec": "content"}'
        mock_response.raise_for_status.return_value = None # No error

        bf = ConcreteFormat()
        content = bf._read_from_url("http://example.com/spec.json")
        self.assertEqual(content, '{"url_spec": "content"}')
        mock_get.assert_called_once_with("http://example.com/spec.json")

    @patch('requests.get')
    def test_read_from_url_failure(self, mock_get):
        mock_response = mock_get.return_value
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Client Error")

        bf = ConcreteFormat()
        with self.assertRaises(IOError):
            bf._read_from_url("http://example.com/nonexistent.json")

    @patch("builtins.open", new_callable=mock_open, read_data='{"file_spec": "content"}')
    def test_read_from_file_success(self, mock_file_open):
        bf = ConcreteFormat()
        content = bf._read_from_file("dummy_path.json")
        self.assertEqual(content, '{"file_spec": "content"}')
        mock_file_open.assert_called_once_with("dummy_path.json", 'r')

    @patch("builtins.open", side_effect=FileNotFoundError)
    def test_read_from_file_not_found(self, mock_file_open):
        bf = ConcreteFormat()
        with self.assertRaises(IOError):
            bf._read_from_file("nonexistent_path.json")

    def test_parse_json_then_yaml(self):
        bf = ConcreteFormat()
        # Test JSON
        json_data = '{"key": "value_json", "concrete_marker": true}'
        parsed = bf.parse(json_data)
        self.assertEqual(parsed, {"key": "value_json", "concrete_marker": True})
        # Test YAML
        yaml_data = 'key: value_yaml\nconcrete_marker: true'
        parsed = bf.parse(yaml_data)
        self.assertEqual(parsed, {"key": "value_yaml", "concrete_marker": True})
        # Test invalid
        invalid_data = 'this is not json or yaml'
        with self.assertRaises(ValueError): # "Failed to parse data as JSON or YAML"
            bf.parse(invalid_data)

    def test_read_spec_object_source(self):
        bf = ConcreteFormat()
        spec_object = {"key": "value", "concrete_marker": True}
        # For object source, it should return the object itself and 'object' type
        parsed_spec, source_type = bf.read_spec(spec_object)
        self.assertEqual(parsed_spec, spec_object)
        self.assertEqual(source_type, "object")


    @patch('api_spec_converter_py.base_format.BaseFormat.read_spec')
    def test_resolve_resources_success(self, mock_read_spec):
        # Mock read_spec to return our sample spec and a source type
        mock_read_spec.return_value = (self.sample_spec_dict, "string")

        bf = ConcreteFormat() # Fresh instance
        resolved_bf = bf.resolve_resources("dummy source string")

        self.assertIsNotNone(resolved_bf.spec)
        self.assertEqual(resolved_bf.spec["info"]["title"], "Test API")
        self.assertEqual(resolved_bf.source_type, "string")
        mock_read_spec.assert_called_once_with("dummy source string")
        # fix_spec and resolve_sub_resources are also called, ensure they don't break
        # (their default implementations are pass/simple)

    @patch('api_spec_converter_py.base_format.BaseFormat.read_spec')
    def test_resolve_resources_invalid_format(self, mock_read_spec):
        # Make check_format fail by returning a spec without 'concrete_marker'
        invalid_spec_data = {"info": "missing marker"}
        mock_read_spec.return_value = (invalid_spec_data, "string")

        bf = ConcreteFormat()
        with self.assertRaisesRegex(ValueError, "is not a valid concrete_format format"):
            bf.resolve_resources("dummy source for invalid")

    # Test convert_to - requires a mock registry and another format class or careful mocking
    @patch('api_spec_converter_py.base_format.FORMAT_REGISTRY', new_callable=dict)
    def test_convert_to_registered_format(self, mock_format_registry):
        # Mock another format class
        class OtherFormat(BaseFormat):
            def __init__(self, spec=None): super().__init__(spec)
            @property
            def format_name(self): return "other_format"
            def fix_spec(self): self.spec["fixed_by_other"] = True # Mock fix_spec

        mock_format_registry["other_format"] = OtherFormat

        bf_instance = ConcreteFormat({"concrete_marker": True, "data": "stuff"})
        # Ensure resolve_resources is called to set up bf_instance.spec correctly
        with patch.object(ConcreteFormat, 'read_spec', return_value=({"concrete_marker": True, "data": "stuff"}, "object")):
             bf_instance.resolve_resources({"concrete_marker": True, "data": "stuff"})


        converted_instance = bf_instance.convert_to("other_format")

        self.assertIsInstance(converted_instance, OtherFormat)
        self.assertTrue(converted_instance.spec["converted"])
        self.assertEqual(converted_instance.spec["original_spec"]["data"], "stuff")
        self.assertTrue(converted_instance.spec["fixed_by_other"]) # Check fix_spec was called

    def test_convert_to_self(self):
        converted_instance = self.base_format.convert_to("concrete_format")
        self.assertIs(converted_instance, self.base_format)

    def test_convert_to_unsupported_format(self):
        with self.assertRaisesRegex(NotImplementedError, "Conversion from concrete_format to unsupported_format is not supported"):
            self.base_format.convert_to("unsupported_format")

    @patch('api_spec_converter_py.base_format.FORMAT_REGISTRY', new_callable=dict)
    def test_convert_to_unregistered_target_format(self, mock_format_registry):
        # Converter exists, but target format class not in registry
        bf_instance = ConcreteFormat({"concrete_marker": True, "data": "stuff"})
        # The converter for 'other_format' exists in ConcreteFormat
        with self.assertRaisesRegex(ValueError, "Target format 'other_format' is not registered."):
            bf_instance.convert_to("other_format")


if __name__ == '__main__':
    unittest.main()
