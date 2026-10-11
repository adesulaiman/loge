"""Unit tests for shared git tip path filters."""

import pytest

from onyx.connectors.cross_connector_utils.git_indexable_files import is_indexable_path


@pytest.mark.parametrize(
    "path,size,expected",
    [
        ("src/main.py", 100, True),
        ("app.ts", 100, True),
        ("README.md", 100, True),
        ("node_modules/left-pad/index.js", 100, False),
        ("vendor/lib.py", 100, False),
        ("huge.py", 2_000_000, False),
        ("logo.png", 100, False),
    ],
)
def test_is_indexable_path(path: str, size: int | None, expected: bool) -> None:
    assert is_indexable_path(path, size) is expected
