"""
Unit tests for QuadTree.nearest_neighbor() functionality.

Tests verify that:
1. The nearest neighbor search correctly identifies the closest point
2. Edge cases are handled (empty tree, single point, exact matches)
3. Various query positions work correctly
4. The algorithm works with large point sets
5. Negative coordinates and scattered points work as expected
"""

import pytest

try:
    from polytope_feature.polytope_rs import QuadTree
except ImportError:
    QuadTree = None

pytestmark = pytest.mark.skipif(QuadTree is None, reason="QuadTree not installed")


def squared_distance(p1, p2):
    """Calculate squared Euclidean distance between two points."""
    dx = p1[0] - p2[0]
    dy = p1[1] - p2[1]
    return dx * dx + dy * dy


def find_expected_nearest(query, points):
    """
    Brute force search to find expected nearest neighbor.

    Args:
        query: (x, y) query point
        points: list of (x, y) points

    Returns:
        tuple: (index, distance_squared) or (None, None) if no points
    """
    if not points:
        return None, None

    min_distance = float("inf")
    min_index = None

    for idx, point in enumerate(points):
        dist = squared_distance(query, point)
        if dist < min_distance:
            min_distance = dist
            min_index = idx

    return min_index, min_distance


class TestNearestNeighbor:
    """Test suite for nearest neighbor search."""

    def test_simple_grid(self):
        """Test with simple grid of 5 points."""
        print("\n=== Test: Simple Grid ===")
        points = [
            (10.0, 0.0),  # index 1
            (0.0, 0.0),  # index 0
            (0.0, 10.0),  # index 2
            (10.0, 10.0),  # index 3
            (5.0, 5.0),  # index 4
        ]

        quadtree = QuadTree()
        quadtree.build_point_tree(points)

        # Test 1: Query at (1, 1) - should find point (0, 0)
        query = (1.0, 1.0)
        result = quadtree.nearest_neighbor(query, points)
        expected = 1
        assert result == expected, f"Query {query}: expected {expected}, got {result}"
        print(f"✓ Query {query} → index {result} (point {points[result]})")

        # Test 2: Query at (11, 11) - should find point (10, 10)
        query = (11.0, 11.0)
        result = quadtree.nearest_neighbor(query, points)
        expected = 3
        assert result == expected, f"Query {query}: expected {expected}, got {result}"
        print(f"✓ Query {query} → index {result} (point {points[result]})")

        # Test 3: Query at (5.1, 5.1) - should find point (5, 5)
        query = (5.1, 5.1)
        result = quadtree.nearest_neighbor(query, points)
        expected = 4
        assert result == expected, f"Query {query}: expected {expected}, got {result}"
        print(f"✓ Query {query} → index {result} (point {points[result]})")

    def test_exact_point_match(self):
        """Test querying exactly on a point in the tree."""
        print("\n=== Test: Exact Point Match ===")
        points = [
            (0.0, 0.0),
            (10.0, 10.0),
            (20.0, 20.0),
            (15.0, 5.0),
        ]

        quadtree = QuadTree()
        quadtree.build_point_tree(points)

        # Query exactly at point (10, 10) - should find itself
        query = (10.0, 10.0)
        result = quadtree.nearest_neighbor(query, points)
        expected = 1
        assert result == expected, f"Query {query}: expected {expected}, got {result}"
        print(f"✓ Query exactly at {query} → index {result} (itself)")

    def test_random_points_correctness(self):
        """Test correctness with random-ish points."""
        print("\n=== Test: Random Points Correctness ===")
        points = [
            (1.0, 2.0),
            (5.0, 3.0),
            (9.0, 8.0),
            (2.0, 9.0),
            (7.0, 1.0),
            (4.0, 6.0),
        ]

        quadtree = QuadTree()
        quadtree.build_point_tree(points)

        test_queries = [
            (3.5, 2.5),
            (6.0, 4.0),
            (0.5, 0.5),
            (8.5, 8.5),
        ]

        for query in test_queries:
            result = quadtree.nearest_neighbor(query, points)
            expected_idx, expected_dist = find_expected_nearest(query, points)

            assert result == expected_idx, f"Query {query}: expected {expected_idx}, got {result}"

            # Verify distances match
            result_dist = squared_distance(query, points[result])
            assert abs(result_dist - expected_dist) < 1e-10, f"Distance mismatch for query {query}"

            print(f"✓ Query {query} → index {result} (point {points[result]}, dist²={result_dist:.2f})")

    def test_single_point(self):
        """Test edge case: only one point in tree."""
        print("\n=== Test: Single Point ===")
        points = [(5.0, 5.0)]

        quadtree = QuadTree()
        quadtree.build_point_tree(points)

        query = (0.0, 0.0)
        result = quadtree.nearest_neighbor(query, points)
        expected = 0
        assert result == expected, f"Query {query}: expected {expected}, got {result}"
        print(f"✓ Query {query} with single point → index {result}")

    def test_empty_tree(self):
        """Test edge case: empty tree."""
        print("\n=== Test: Empty Tree ===")
        points = []

        quadtree = QuadTree()
        # Don't call build_point_tree on empty list

        query = (5.0, 5.0)
        result = quadtree.nearest_neighbor(query, points)
        assert result is None, f"Query on empty tree should return None, got {result}"

    def test_distant_query(self):
        """Test with query point far from all tree points."""
        print("\n=== Test: Distant Query ===")
        points = [
            (0.0, 0.0),
            (1.0, 1.0),
            (2.0, 2.0),
        ]

        quadtree = QuadTree()
        quadtree.build_point_tree(points)

        # Query far away - should still find correct nearest
        query = (100.0, 100.0)
        result = quadtree.nearest_neighbor(query, points)
        expected = 2  # (2, 2) is closest
        assert result == expected, f"Query {query}: expected {expected}, got {result}"
        print(f"✓ Query {query} (distant) → index {result} (point {points[result]})")

    def test_negative_coordinates(self):
        """Test with negative coordinates."""
        print("\n=== Test: Negative Coordinates ===")
        points = [
            (-10.0, -10.0),
            (-5.0, 0.0),
            (0.0, 5.0),
            (5.0, -5.0),
        ]

        quadtree = QuadTree()
        quadtree.build_point_tree(points)

        query = (-6.0, -9.0)
        result = quadtree.nearest_neighbor(query, points)
        expected_idx, _ = find_expected_nearest(query, points)

        assert result == expected_idx, f"Query {query}: expected {expected_idx}, got {result}"
        print(f"✓ Query {query} with negatives → index {result} (point {points[result]})")

    def test_large_tree(self):
        """Test with many points to exercise quadtree splitting."""
        print("\n=== Test: Large Tree (400 points) ===")
        # Create 20x20 grid
        points = []
        for i in range(20):
            for j in range(20):
                points.append((i * 5.0, j * 5.0))

        print(f"Building tree with {len(points)} points...")
        quadtree = QuadTree()
        quadtree.build_point_tree(points)

        test_queries = [
            (12.5, 12.5),
            (75.0, 75.0),
            (2.0, 98.0),
            (97.0, 2.0),
        ]

        for query in test_queries:
            result = quadtree.nearest_neighbor(query, points)
            expected_idx, expected_dist = find_expected_nearest(query, points)

            assert result == expected_idx, f"Query {query}: expected {expected_idx}, got {result}"

            result_dist = squared_distance(query, points[result])
            print(f"✓ Query {query} → index {result} (dist²={result_dist:.2f})")

    def run_all(self):
        """Run all tests."""
        print("=" * 60)
        print("QUADTREE NEAREST NEIGHBOR TESTS")
        print("=" * 60)

        tests = [
            self.test_simple_grid,
            self.test_exact_point_match,
            self.test_random_points_correctness,
            self.test_single_point,
            self.test_empty_tree,
            self.test_distant_query,
            self.test_negative_coordinates,
            self.test_large_tree,
        ]

        passed = 0
        failed = 0

        for test in tests:
            try:
                test()
                passed += 1
            except AssertionError as e:
                print(f"✗ FAILED: {e}")
                failed += 1
            except Exception as e:
                print(f"✗ ERROR: {e}")
                failed += 1

        print("\n" + "=" * 60)
        print(f"RESULTS: {passed} passed, {failed} failed")
        print("=" * 60)

        return failed == 0
