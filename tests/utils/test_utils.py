import unittest
from api_spec_converter_py.utils.utils import remove_none_values, parse_json, parse_yaml, ParseError

class TestUtils(unittest.TestCase):

    def test_remove_none_values_simple(self):
        data = {"a": 1, "b": None, "c": "hello"}
        expected = {"a": 1, "c": "hello"}
        self.assertEqual(remove_none_values(data), expected)

    def test_remove_none_values_nested(self):
        data = {
            "a": 1,
            "b": None,
            "c": {
                "d": "hello",
                "e": None,
                "f": [1, None, {"g": 2, "h": None, "k": "stay"}]
            },
            "i": None,
            "j": [None, "world", {"l": None, "m": "visible"}]
        }
        expected = {
            "a": 1,
            "c": {
                "d": "hello",
                "f": [1, {"g": 2, "k": "stay"}]
            },
            "j": ["world", {"m": "visible"}]
        }
        # remove_none_values modifies in-place and also returns the object
        remove_none_values(data)
        self.assertEqual(data, expected)

    def test_remove_none_values_empty_dict(self):
        data = {}
        expected = {}
        self.assertEqual(remove_none_values(data), expected)

    def test_remove_none_values_all_none(self):
        data = {"a": None, "b": None}
        expected = {}
        self.assertEqual(remove_none_values(data), expected)

    def test_remove_none_values_list_with_nones(self):
        data = {"a": [1, None, 2, None, {"b": None, "c": 3}]}
        expected = {"a": [1, 2, {"c": 3}]}
        remove_none_values(data)
        self.assertEqual(data, expected)

    def test_parse_json_valid(self):
        json_string = '{"name": "Test", "version": 1.0}'
        expected = {"name": "Test", "version": 1.0}
        self.assertEqual(parse_json(json_string), expected)

    def test_parse_json_invalid(self):
        json_string = '{"name": "Test", "version": 1.0,}' # Trailing comma
        with self.assertRaises(ParseError):
            parse_json(json_string)

    def test_parse_yaml_valid(self):
        yaml_string = "name: Test\nversion: 1.0"
        expected = {"name": "Test", "version": 1.0}
        self.assertEqual(parse_yaml(yaml_string), expected)

    def test_parse_yaml_invalid(self):
        yaml_string = "name: Test\n  version: 1.0" # Bad indentation
        with self.assertRaises(ParseError):
            parse_yaml(yaml_string)

if __name__ == '__main__':
    unittest.main()
