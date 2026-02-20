"""
Test that options.py implements lazy import correctly for optional switching_grids dependencies.
"""

import sys
from unittest.mock import patch

import pytest

from polytope_feature.options import PolytopeOptions


def _optional_deps_available():
    """Check if optional switching_grids dependencies are available."""
    try:
        import eccodes  # noqa: F401
        import pyfdb  # noqa: F401

        return True
    except ImportError:
        return False


class TestOptionsLazyImport:
    """Test lazy import behavior for switching_grid_helper module."""

    def test_options_import_without_optional_deps(self):
        """Test that importing options.py does not import switching_grid_helper."""
        # Before calling get_polytope_options with dynamic_grid=True,
        # switching_grid_helper should not be imported
        assert "polytope_feature.datacube.switching_grid_helper" not in sys.modules

    def test_get_options_without_dynamic_grid(self):
        """Test that get_polytope_options works without dynamic_grid enabled."""
        options = {
            "axis_config": [
                {
                    "axis_name": "number",
                    "transformations": [{"name": "type_change", "type": "int"}],
                },
            ],
            "dynamic_grid": False,
        }

        result = PolytopeOptions.get_polytope_options(options)

        # Verify that we got the expected return tuple
        assert len(result) == 6
        (
            axis_config,
            compressed_axes_config,
            pre_path,
            alternative_axes,
            use_catalogue,
            engine_options,
        ) = result

        # Verify basic structure
        assert len(axis_config) == 1
        assert axis_config[0].axis_name == "number"

        # Verify switching_grid_helper was not imported
        assert "polytope_feature.datacube.switching_grid_helper" not in sys.modules

    def test_get_options_without_dynamic_grid_no_flag(self):
        """Test that get_polytope_options works when dynamic_grid is omitted (defaults to False)."""
        options = {
            "axis_config": [
                {
                    "axis_name": "latitude",
                    "transformations": [{"name": "reverse", "is_reverse": True}],
                },
            ],
        }

        result = PolytopeOptions.get_polytope_options(options)

        # Verify that we got the expected return tuple
        assert len(result) == 6
        (
            axis_config,
            compressed_axes_config,
            pre_path,
            alternative_axes,
            use_catalogue,
            engine_options,
        ) = result

        # Verify basic structure
        assert len(axis_config) == 1
        assert axis_config[0].axis_name == "latitude"

        # Verify switching_grid_helper was not imported
        assert "polytope_feature.datacube.switching_grid_helper" not in sys.modules

    def test_get_options_with_dynamic_grid_missing_deps(self):
        """Test that get_polytope_options gracefully handles missing optional dependencies.

        NOTE: This test only validates the ImportError path if optional dependencies
        are NOT installed. In CI, they are typically installed as part of test dependencies,
        so this test may not exercise the ImportError handling. See
        test_get_options_with_dynamic_grid_simulated_missing_deps for a test that
        uses mocking to simulate missing dependencies regardless of installation status.
        """
        options = {
            "axis_config": [
                {
                    "axis_name": "values",
                    "transformations": [
                        {
                            "name": "mapper",
                            "type": "lambert_conformal",
                            "resolution": 1280,
                            "axes": ["latitude", "longitude"],
                        }
                    ],
                },
            ],
            "dynamic_grid": True,
            "pre_path": {
                "georef": "test",
            },
        }

        # This should not raise an exception even if optional deps are missing
        result = PolytopeOptions.get_polytope_options(options)

        # Verify that we got the expected return tuple
        assert len(result) == 6
        (
            axis_config,
            compressed_axes_config,
            pre_path,
            alternative_axes,
            use_catalogue,
            engine_options,
        ) = result

        # Verify basic structure - original config should be preserved
        assert len(axis_config) == 1
        assert axis_config[0].axis_name == "values"

    def test_get_options_with_dynamic_grid_simulated_missing_deps(self):
        """Test ImportError handling by simulating missing optional dependencies.

        This test uses mocking to simulate the ImportError that occurs when optional
        dependencies (eccodes/pyfdb) are not installed, ensuring the ImportError
        handling path is tested even when dependencies are installed in CI.
        """

        options_dict = {
            "axis_config": [
                {
                    "axis_name": "values",
                    "transformations": [
                        {
                            "name": "mapper",
                            "type": "lambert_conformal",
                            "resolution": 1280,
                            "axes": ["latitude", "longitude"],
                        }
                    ],
                },
            ],
            "dynamic_grid": True,
            "pre_path": {
                "georef": "test",
            },
        }

        # Mock the builtins.__import__ to raise ImportError for switching_grid_helper
        original_import = __builtins__.__import__

        def mock_import(name, *args, **kwargs):
            if "switching_grid_helper" in name:
                raise ImportError(f"No module named '{name}'")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            # This should not raise an exception even with ImportError
            result = PolytopeOptions.get_polytope_options(options_dict)

            # Verify that we got the expected return tuple
            assert len(result) == 6
            (
                axis_config,
                compressed_axes_config,
                pre_path,
                alternative_axes,
                use_catalogue,
                engine_options,
            ) = result

            # Verify basic structure - original config should be preserved
            assert len(axis_config) == 1
            assert axis_config[0].axis_name == "values"

    @pytest.mark.skipif(
        not _optional_deps_available(),
        reason="Optional switching_grids dependencies not installed",
    )
    def test_lazy_import_only_when_needed(self):
        """Test that switching_grid_helper is only imported when dynamic_grid is True."""
        # Remove the module if already imported from previous tests
        if "polytope_feature.datacube.switching_grid_helper" in sys.modules:
            del sys.modules["polytope_feature.datacube.switching_grid_helper"]

        # First verify it's not imported
        assert "polytope_feature.datacube.switching_grid_helper" not in sys.modules

        options = {
            "axis_config": [
                {
                    "axis_name": "test",
                    "transformations": [{"name": "type_change", "type": "int"}],
                },
            ],
            "dynamic_grid": False,
        }

        PolytopeOptions.get_polytope_options(options)

        # Should still not be imported
        assert "polytope_feature.datacube.switching_grid_helper" not in sys.modules
