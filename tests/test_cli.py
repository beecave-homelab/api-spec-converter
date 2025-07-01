import unittest
import json
from click.testing import CliRunner
from unittest.mock import patch, MagicMock

from api_spec_converter_py.cli import main as cli_main
from api_spec_converter_py.base_format import BaseFormat
from api_spec_converter_py.formats import register_format, FORMAT_REGISTRY

# --- Mock Format Classes for Testing ---
@register_format("mock_format_a")
class MockFormatA(BaseFormat):
    def __init__(self, spec=None):
        super().__init__(spec)
        self.converters = {"mock_format_b": self._to_b}

    @property
    def format_name(self): return "mock_format_a"
    @property
    def supported_versions(self): return ["1.0"]
    def get_format_version(self): return "1.0"
    def check_format(self, spec_data): return "format_a_content" in spec_data
    def fix_spec(self):
        if self.spec: self.spec["fixed_a"] = True
    def _to_b(self, instance, po=None): return {"format_b_content": instance.spec.get("format_a_content", ""), "converted_from_a": True}

@register_format("mock_format_b")
class MockFormatB(BaseFormat):
    def __init__(self, spec=None):
        super().__init__(spec)
        self.converters = {"mock_format_a": self._to_a}

    @property
    def format_name(self): return "mock_format_b"
    @property
    def supported_versions(self): return ["1.0"]
    def get_format_version(self): return "1.0"
    def check_format(self, spec_data): return "format_b_content" in spec_data
    def fix_spec(self):
        if self.spec: self.spec["fixed_b"] = True
    def _to_a(self, instance, po=None): return {"format_a_content": instance.spec.get("format_b_content", ""), "converted_from_b": True}
    def fill_missing(self): # For testing --dummy
        if self.spec: self.spec["dummy_filled_b"] = True
    def validate(self): # For testing --check
        if self.spec and self.spec.get("make_invalid"):
            return {"errors": ["Made invalid by test!"], "warnings": None}
        return {"errors": None, "warnings": ["A test warning."]}


class TestCLI(unittest.TestCase):
    def setUp(self):
        self.runner = CliRunner()
        # Ensure our mock formats are in the registry for each test
        # This is important if tests run in parallel or registry is modified elsewhere
        FORMAT_REGISTRY["mock_format_a"] = MockFormatA
        FORMAT_REGISTRY["mock_format_b"] = MockFormatB

        # Keep a copy of the original registry to restore it
        self._original_registry = FORMAT_REGISTRY.copy()

    def tearDown(self):
        # Restore the original FORMAT_REGISTRY to avoid test interference
        # Clear out mock formats if they were added.
        # More robustly, save and restore FORMAT_REGISTRY.
        # For now, let's just ensure they are removed if present.
        FORMAT_REGISTRY.pop("mock_format_a", None)
        FORMAT_REGISTRY.pop("mock_format_b", None)
        # Restore any other formats that might have been popped by mistake
        # This is a bit hacky; ideally, FORMAT_REGISTRY would be managed per test or app context
        for k, v in self._original_registry.items():
            if k not in FORMAT_REGISTRY:
                 FORMAT_REGISTRY[k] = v


    def test_cli_version(self):
        result = self.runner.invoke(cli_main, ["--version"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("api-spec-converter-py, version", result.output)

    def test_cli_help(self):
        result = self.runner.invoke(cli_main, ["--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Usage: main [OPTIONS] SOURCE", result.output)
        self.assertIn("Converts API specifications", result.output)

    def test_cli_conversion_file_input_success(self):
        input_content = '{"format_a_content": "test_data", "version": "1.0"}'
        with self.runner.isolated_filesystem():
            with open("input.json", "w") as f:
                f.write(input_content)

            result = self.runner.invoke(
                cli_main,
                ["-f", "mock_format_a", "-t", "mock_format_b", "input.json"]
            )

            self.assertEqual(result.exit_code, 0, msg=f"CLI Error: {result.output}")

            output_dict = json.loads(result.output)
            self.assertEqual(output_dict["format_b_content"], "test_data")
            self.assertTrue(output_dict["converted_from_a"])
            self.assertTrue(output_dict["fixed_b"]) # fix_spec of Target (MockFormatB) called

    def test_cli_conversion_stdin_input_success(self):
        input_content_json = '{"format_a_content": "stdin_test", "version": "1.0"}'
        result = self.runner.invoke(
            cli_main,
            ["-f", "mock_format_a", "-t", "mock_format_b", "-"],
            input=input_content_json
        )
        self.assertEqual(result.exit_code, 0, msg=f"CLI Error: {result.output}")
        output_dict = json.loads(result.output)
        self.assertEqual(output_dict["format_b_content"], "stdin_test")
        self.assertTrue(output_dict["converted_from_a"])
        self.assertTrue(output_dict["fixed_b"])

    def test_cli_conversion_yaml_output(self):
        input_content = '{"format_a_content": "yaml_out_test"}'
        with self.runner.isolated_filesystem():
            with open("input.json", "w") as f:
                f.write(input_content)

            result = self.runner.invoke(
                cli_main,
                ["-f", "mock_format_a", "-t", "mock_format_b", "--syntax", "yaml", "input.json"]
            )
            self.assertEqual(result.exit_code, 0, msg=f"CLI Error: {result.output}")
            # Basic check for YAML structure
            self.assertIn("format_b_content: yaml_out_test", result.output)
            self.assertIn("converted_from_a: true", result.output) # YAML boolean

    def test_cli_conversion_with_dummy_option(self):
        input_content = '{"format_a_content": "dummy_test"}' # MockFormatA input
        with self.runner.isolated_filesystem():
            with open("input.json", "w") as f:
                f.write(input_content)

            result = self.runner.invoke(
                cli_main,
                ["-f", "mock_format_a", "-t", "mock_format_b", "--dummy", "input.json"]
            )
            self.assertEqual(result.exit_code, 0, msg=f"CLI Error: {result.output}")
            output_dict = json.loads(result.output)
            self.assertTrue(output_dict["dummy_filled_b"]) # Check fill_missing was called

    def test_cli_conversion_with_check_option_valid(self):
        input_content = '{"format_a_content": "check_valid_test"}'
        with self.runner.isolated_filesystem():
            with open("input.json", "w") as f:
                f.write(input_content)

            result = self.runner.invoke(
                cli_main,
                ["-f", "mock_format_a", "-t", "mock_format_b", "--check", "input.json"]
            )
            self.assertEqual(result.exit_code, 0, msg=f"CLI Error: {result.output + result.stderr}")
            self.assertIn("Validation Warnings:", result.stderr) # MockFormatB validate adds a warning
            self.assertIn("A test warning.", result.stderr)

            output_dict = json.loads(result.output) # Main output should still be there
            self.assertEqual(output_dict["format_b_content"], "check_valid_test")


    def test_cli_conversion_with_check_option_invalid(self):
        # Modify MockFormatB's output to be invalid based on a flag
        input_content = '{"format_a_content": "check_invalid_test", "make_invalid": true}' # make_invalid flag for MockFormatB

        # To make MockFormatB's spec have 'make_invalid', the converter _to_b needs to pass it through
        # Let's adjust MockFormatA._to_b for this test case
        original_to_b = MockFormatA._to_b
        def new_to_b(self, instance, po=None):
            res = original_to_b(self, instance, po)
            if instance.spec.get("make_invalid"):
                res["make_invalid"] = True
            return res

        with patch.object(MockFormatA, '_to_b', new=new_to_b):
            with self.runner.isolated_filesystem():
                with open("input.json", "w") as f:
                    f.write(input_content)

                result = self.runner.invoke(
                    cli_main,
                    ["-f", "mock_format_a", "-t", "mock_format_b", "--check", "input.json"]
                )
                self.assertEqual(result.exit_code, 0, msg=f"CLI Error: {result.output + result.stderr}") # Still exits 0, errors to stderr
                self.assertIn("Validation Errors:", result.stderr)
                self.assertIn("Made invalid by test!", result.stderr)

    def test_cli_unknown_from_format(self):
        result = self.runner.invoke(cli_main, ["-f", "nonexistent", "-t", "mock_format_a", "-"], input="{}")
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("Invalid choice for option --from-format", result.output) # Click error

    def test_cli_unknown_to_format(self):
        result = self.runner.invoke(cli_main, ["-f", "mock_format_a", "-t", "nonexistent", "-"], input='{"format_a_content":"test"}')
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("Invalid choice for option --to-format", result.output) # Click error

    def test_cli_conversion_error_in_format_check(self):
        # Input that will fail MockFormatA's check_format
        input_content_json = '{"wrong_content_key": "test_data"}'
        result = self.runner.invoke(
            cli_main,
            ["-f", "mock_format_a", "-t", "mock_format_b", "-"],
            input=input_content_json
        )
        self.assertEqual(result.exit_code, 1)
        self.assertIn("is not a valid mock_format_a format.", result.output) # Error from BaseFormat.resolve_resources

    @patch('api_spec_converter_py.cli.requests.get')
    def test_cli_url_input_success(self, mock_requests_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '{"format_a_content": "url_test_data"}'
        mock_response.raise_for_status.return_value = None
        mock_requests_get.return_value = mock_response

        result = self.runner.invoke(
            cli_main,
            ["-f", "mock_format_a", "-t", "mock_format_b", "http://example.com/spec.json"]
        )
        self.assertEqual(result.exit_code, 0, msg=f"CLI Error: {result.output}")
        mock_requests_get.assert_called_once_with("http://example.com/spec.json")
        output_dict = json.loads(result.output)
        self.assertEqual(output_dict["format_b_content"], "url_test_data")

    @patch('api_spec_converter_py.cli.requests.get')
    def test_cli_url_input_failure(self, mock_requests_get):
        mock_requests_get.side_effect = Exception("Network Error")

        result = self.runner.invoke(
            cli_main,
            ["-f", "mock_format_a", "-t", "mock_format_b", "http://example.com/spec.json"]
        )
        self.assertEqual(result.exit_code, 1) # Should fail
        self.assertIn("Error reading from URL", result.output) # Error from BaseFormat._read_from_url

if __name__ == '__main__':
    unittest.main()
