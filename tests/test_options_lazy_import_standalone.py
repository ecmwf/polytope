#!/usr/bin/env python3
"""
Standalone test script to verify lazy import behavior.
"""

import sys


def test_options_import_without_optional_deps():
    """Test that importing options.py does not import switching_grid_helper."""
    # Remove any previous imports
    if "polytope_feature.datacube.switching_grid_helper" in sys.modules:
        del sys.modules["polytope_feature.datacube.switching_grid_helper"]

    # Import options module
    from polytope_feature.options import PolytopeOptions  # noqa: F401

    # Verify switching_grid_helper is not imported
    assert (
        "polytope_feature.datacube.switching_grid_helper" not in sys.modules
    ), "switching_grid_helper should not be imported at module level"
    print("✓ Test passed: options module can be imported without switching_grid_helper")


def test_get_options_without_dynamic_grid():
    """Test that get_polytope_options works without dynamic_grid enabled."""
    from polytope_feature.options import PolytopeOptions

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
    assert len(result) == 6, f"Expected 6 elements, got {len(result)}"
    (
        axis_config,
        compressed_axes_config,
        pre_path,
        alternative_axes,
        use_catalogue,
        engine_options,
    ) = result

    # Verify basic structure
    assert len(axis_config) == 1, f"Expected 1 axis config, got {len(axis_config)}"
    assert (
        axis_config[0].axis_name == "number"
    ), f"Expected axis_name 'number', got '{axis_config[0].axis_name}'"

    # Verify switching_grid_helper was not imported
    assert (
        "polytope_feature.datacube.switching_grid_helper" not in sys.modules
    ), "switching_grid_helper should not be imported when dynamic_grid is False"
    print("✓ Test passed: get_polytope_options works without dynamic_grid")


def test_get_options_without_dynamic_grid_no_flag():
    """Test that get_polytope_options works when dynamic_grid is omitted."""
    from polytope_feature.options import PolytopeOptions

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
    assert len(result) == 6, f"Expected 6 elements, got {len(result)}"
    (
        axis_config,
        compressed_axes_config,
        pre_path,
        alternative_axes,
        use_catalogue,
        engine_options,
    ) = result

    # Verify basic structure
    assert len(axis_config) == 1, f"Expected 1 axis config, got {len(axis_config)}"
    assert (
        axis_config[0].axis_name == "latitude"
    ), f"Expected axis_name 'latitude', got '{axis_config[0].axis_name}'"

    # Verify switching_grid_helper was not imported
    assert (
        "polytope_feature.datacube.switching_grid_helper" not in sys.modules
    ), "switching_grid_helper should not be imported when dynamic_grid is not specified"
    print("✓ Test passed: get_polytope_options works when dynamic_grid is omitted")


def test_get_options_with_dynamic_grid_missing_deps():
    """Test that get_polytope_options gracefully handles missing optional dependencies."""
    from polytope_feature.options import PolytopeOptions

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
    assert len(result) == 6, f"Expected 6 elements, got {len(result)}"
    (
        axis_config,
        compressed_axes_config,
        pre_path,
        alternative_axes,
        use_catalogue,
        engine_options,
    ) = result

    # Verify basic structure - original config should be preserved
    assert len(axis_config) == 1, f"Expected 1 axis config, got {len(axis_config)}"
    assert (
        axis_config[0].axis_name == "values"
    ), f"Expected axis_name 'values', got '{axis_config[0].axis_name}'"

    print(
        "✓ Test passed: get_polytope_options gracefully handles missing optional dependencies"
    )


def main():
    """Run all tests."""
    tests = [
        test_options_import_without_optional_deps,
        test_get_options_without_dynamic_grid,
        test_get_options_without_dynamic_grid_no_flag,
        test_get_options_with_dynamic_grid_missing_deps,
    ]

    failed = 0
    for test in tests:
        try:
            test()
        except AssertionError as e:
            print(f"✗ Test failed: {test.__name__}")
            print(f"  {e}")
            failed += 1
        except Exception as e:
            print(f"✗ Test error: {test.__name__}")
            print(f"  {type(e).__name__}: {e}")
            failed += 1

    if failed == 0:
        print(f"\n✓ All {len(tests)} tests passed!")
        return 0
    else:
        print(f"\n✗ {failed}/{len(tests)} tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
