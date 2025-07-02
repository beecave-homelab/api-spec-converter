"""Entry point for running ``python -m api_spec_converter``.

This thin wrapper simply delegates execution to the ``main`` Click command
implemented in :pymod:`api_spec_converter.cli` so that the package can be
invoked the same way as the ``api-spec-converter`` console-script or by running
``python api_spec_converter/cli.py`` directly.
"""

from __future__ import annotations

from api_spec_converter.cli import main


def _run() -> None:
    """
    Execute the CLI entry point for the API specification converter.

    This function delegates execution to the main Click command implemented in
    api_spec_converter.cli, allowing the package to be invoked as a module.

    Returns:
        None
    """
    # Click automatically handles ``SystemExit`` for error codes.
    main(standalone_mode=True)


if __name__ == "__main__":  # pragma: no cover -- entry-point guard
    _run()
