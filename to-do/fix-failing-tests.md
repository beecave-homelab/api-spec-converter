# To-Do: Fix Failing Tests

This plan outlines the steps to fix the 22 failing unit and integration tests.

## Tasks

- [x] **Analysis Phase:**
  - [x] Review the pytest output to categorize the failures.
    - **Path**: Test output
    - **Action**: Identify the root cause for each of the 22 failing tests across `test_base_format.py`, `test_cli.py`, and `test_utils.py`.
    - **Analysis Results**:
      - `test_base_format.py`:
        - `AttributeError: ... does not have the attribute 'FORMAT_REGISTRY'`: The mock patch target is likely incorrect.
        - `AttributeError: type object 'BaseFormat' has no attribute 'ATTR_ORDER'`: `ATTR_ORDER` seems to have been moved or removed from `BaseFormat`.
        - `AssertionError: ValueError not raised`: The `parse` method doesn't raise `ValueError` for invalid input.
        - `AssertionError: expected call not found`: The mock for `open` needs to account for the `encoding` parameter.
        - `NameError: name 'requests' is not defined`: `requests` needs to be imported in `tests/test_base_format.py`.
        - `AssertionError: None != 'string'`: `resolve_resources` is not setting `source_type` correctly.
        - `AssertionError: False is not true` in `test_stringify_*_order`: The `stringify` method is not ordering keys as expected.
      - `test_cli.py`:
        - Multiple `AssertionError: 2 != 0` or `2 != 1`: The CLI is exiting with an unexpected status code, likely because mock formats are not being registered correctly for the tests.
        - `AttributeError: module 'api_spec_converter.cli' has no attribute 'requests'`: The mock patch target for `requests` is incorrect.
        - `AssertionError: 'Invalid choice for option ...' not found`: The error message from Click has changed.
      - `test_utils.py`:
        - `AssertionError` in `test_remove_none_values_*`: The `remove_none_values` function is not correctly removing `None` from lists.
    - **Accept Criteria**: A clear understanding of why each test is failing.

- [x] **Implementation Phase:**
  - [x] Fix tests in `tests/test_base_format.py`
    - **Path**: `tests/test_base_format.py` and `api_spec_converter/base_format.py`
    - **Action**: Address the issues identified in the analysis phase for `test_base_format.py`.
    - **Status**: Pending

  - [x] Fix tests in `tests/test_cli.py`
    - **Path**: `tests/test_cli.py` and `api_spec_converter/cli.py`
    - **Action**: Address the issues identified in the analysis phase for `test_cli.py`.
    - **Status**: Pending

  - [x] Fix function and tests in `api_spec_converter/utils/utils.py` and `tests/utils/test_utils.py`
    - **Path**: `api_spec_converter/utils/utils.py`, `tests/utils/test_utils.py`
    - **Action**: Update `remove_none_values` to handle `None` values inside lists recursively and ensure tests pass.
    - **Status**: Pending

- [x] **Testing Phase:**
  - [x] Run all tests
    - **Path**: `/`
    - **Action**: `pdm run pytest`
    - **Accept Criteria**: All tests pass.

- [ ] **Documentation Phase:**
  - [ ] No documentation changes are expected for these fixes.

## Related Files

- `tests/test_base_format.py`
- `tests/test_cli.py`
- `tests/utils/test_utils.py`
- `api_spec_converter/base_format.py`
- `api_spec_converter/cli.py`
- `api_spec_converter/utils/utils.py`

## Future Enhancements

- [ ] [None] 