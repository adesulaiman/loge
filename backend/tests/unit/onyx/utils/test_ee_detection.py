"""Full feature code loads only when the build ships a real `loge` package.

`is_ee_available` rejects a missing `loge` package and a directory with no
`__init__.py`. `set_is_ee_if_available` selects the full feature set only when
`is_ee_available` is true.
"""

from importlib.machinery import ModuleSpec
from unittest.mock import patch

import pytest

from onyx.utils import variable_functionality
from onyx.utils.variable_functionality import (
    global_version,
    is_ee_available,
    set_is_ee_if_available,
)


def test_ee_is_available_when_the_package_is_real() -> None:
    with patch(
        "onyx.utils.variable_functionality.importlib.util.find_spec",
        return_value=ModuleSpec("loge.main", loader=None, origin="loge/main.py"),
    ):
        assert is_ee_available()


def test_ee_is_unavailable_with_no_loge_package() -> None:
    with patch(
        "onyx.utils.variable_functionality.importlib.util.find_spec",
        side_effect=ModuleNotFoundError("No module named 'loge.main'"),
    ):
        assert not is_ee_available()


@pytest.mark.parametrize(
    "spec",
    [
        None,
        # A leftover `loge` directory with no `main` module.
        ModuleSpec("loge.main", loader=None, origin=None),
    ],
)
def test_ee_is_unavailable_without_a_real_package(spec: ModuleSpec | None) -> None:
    with patch(
        "onyx.utils.variable_functionality.importlib.util.find_spec",
        return_value=spec,
    ):
        assert not is_ee_available()


@pytest.mark.parametrize("available", [True, False])
def test_ee_loads_only_when_the_build_ships_it(available: bool) -> None:
    with patch.object(
        variable_functionality, "is_ee_available", return_value=available
    ):
        set_is_ee_if_available()
    try:
        assert global_version.is_ee_version() is available
    finally:
        global_version.unset_ee()
