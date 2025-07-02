# To-Do: Improve API Spec Conversion Logic

This document outlines the investigation into the `api-spec-converter`'s functionality, the fixes implemented, and the path forward to make the tool reliable.

## Summary

The initial goal was to test the conversion of an OpenAPI 3.1 specification to Swagger 2.0 and verify its integrity through a round-trip conversion (OpenAPI 3 -> Swagger 2 -> OpenAPI 3).

The investigation revealed that both the `openapi_3_to_swagger_2` and `swagger_2_to_openapi_3` converters are incomplete placeholders and not suitable for production use. While several superficial bugs were fixed, the core conversion logic remains flawed, leading to significant data corruption.

## Work Completed

- [x] **Initial Conversion Test:**
  - **Action:** Attempted to convert `openapi.yaml` from `openapi_3` to `swagger_2`.
  - **Result:** Failed. The tool does not support OpenAPI 3.1.0.
  - **Fix:** Downgraded `openapi.yaml` version from `3.1.0` to `3.0.0`.

- [x] **Round-Trip Conversion Test:**
  - **Action:** Performed a round-trip conversion (`openapi_3` -> `swagger_2` -> `openapi_3`).
  - **Result:** Failed. The intermediate JSON files were corrupted by warning messages printed to standard output.

- [x] **Silence Conversion Warnings:**
  - **Action:** Located and commented out `print` statements in the `validate`, `list_sub_resources`, and converter functions within both `api_spec_converter/formats/openapi_3.py` and `api_spec_converter/formats/swagger_2.py`.
  - **Result:** The tool no longer pollutes the standard output with warnings, allowing for clean file generation.

- [x] **Fix Server URL Generation:**
  - **Action:** Corrected the logic in the `swagger_2` to `openapi_3` converter that was incorrectly appending a trailing slash to the server URL.

- [x] **Investigate Data Corruption:**
  - **Action:** Ran a `diff` between the original and the round-trip-converted specification.
  - **Result:** Identified significant data loss and structural changes, particularly in how `produces`/`consumes` directives and response schemas are handled. An initial attempt to fix this was insufficient.

## Path Forward: Next Steps

The existing converter functions are basic placeholders and require a complete implementation to be reliable.

- [ ] **Fully Implement Converters:**
  - **Action:** Rewrite the conversion logic in `api_spec_converter/formats/openapi_3.py` and `api_spec_converter/formats/swagger_2.py`.
  - **Details:** The new implementation must correctly map all fields between the two specifications. Key areas needing attention include:
    - `consumes`/`produces` mapping to `requestBody`/`responses` content objects.
    - Transformation of `components` (schemas, parameters, security schemes, etc.).
    - Handling of authentication and security definitions.
    - Correctly managing parameter types and structures (e.g., `collectionFormat`).

- [ ] **Recommendation: Integrate a Third-Party Library:**
  - **Rationale:** Building a fully-featured API specification converter from scratch is a complex task. The existing code is a mere skeleton.
  - **Action:** Research and identify a mature, well-tested Python library that specializes in OpenAPI and Swagger conversions.
  - **Next Step:** Replace the placeholder converter logic with calls to the chosen library. This would be far more efficient and reliable than continuing to build upon the current incomplete implementation. 