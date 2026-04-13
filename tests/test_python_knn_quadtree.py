"""
Tests for Python QuadTree.k_nearest_neighbor().

Validates:
- Correctness against brute-force for k=1, k=3, k=N
- Returned QuadNode objects have the right .item and .index attributes
- Edge cases: single point, k larger than tree size, exact query match
- Negative coordinates
- Large trees (exercises the tree-splitting / branch-and-bound pruning)
- Output is ordered nearest-first
- Agreement with the Rust implementation when it is available
"""

import pytest

from polytope_feature.datacube.quadtree.quad_tree import QuadNode, QuadTree

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def dist2(a, b):
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2


def brute_force_knn(query, points, k):
    """Return list of (index, point) for the k nearest points, nearest-first."""
    ranked = sorted(enumerate(points), key=lambda ip: dist2(query, ip[1]))
    return ranked[:k]


def build_tree(points):
    qt = QuadTree()
    qt.build_point_tree([tuple(p) for p in points])
    return qt


def result_indices(nodes):
    """Extract .index from a list of QuadNode objects."""
    return [n.index for n in nodes]


def result_points(nodes):
    """Extract .item from a list of QuadNode objects."""
    return [n.item for n in nodes]


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------

SIMPLE_POINTS = [
    (0.0, 0.0),  # 0
    (10.0, 0.0),  # 1
    (0.0, 10.0),  # 2
    (10.0, 10.0),  # 3
    (5.0, 5.0),  # 4
]

SCATTERED_POINTS = [
    (1.0, 2.0),  # 0
    (5.0, 3.0),  # 1
    (9.0, 8.0),  # 2
    (2.0, 9.0),  # 3
    (7.0, 1.0),  # 4
    (4.0, 6.0),  # 5
]


# ---------------------------------------------------------------------------
# k=1 (nearest-neighbour) tests
# ---------------------------------------------------------------------------


class TestSingleNearestNeighbor:
    """k=1 correctness — should agree with brute force on all queries."""

    def test_simple_grid_k1(self):
        qt = build_tree(SIMPLE_POINTS)
        queries = [(1.0, 1.0), (11.0, 11.0), (5.1, 5.1), (-1.0, -1.0)]
        for query in queries:
            result = qt.k_nearest_neighbor(query, 1)
            assert len(result) == 1
            bf_idx, _ = brute_force_knn(query, SIMPLE_POINTS, 1)[0]
            got_idx = result[0].index
            got_point = result[0].item
            assert got_idx == bf_idx, (
                f"Query {query}: expected index {bf_idx} ({SIMPLE_POINTS[bf_idx]}), "
                f"got index {got_idx} ({got_point})"
            )

    def test_exact_match_k1(self):
        """Querying exactly on a stored point should return that point."""
        qt = build_tree(SIMPLE_POINTS)
        for idx, pt in enumerate(SIMPLE_POINTS):
            result = qt.k_nearest_neighbor(pt, 1)
            assert len(result) == 1
            assert result[0].index == idx, f"Exact query at {pt} should return index {idx}, got {result[0].index}"

    def test_negative_coords_k1(self):
        points = [(-10.0, -10.0), (-5.0, 0.0), (0.0, 5.0), (5.0, -5.0)]
        qt = build_tree(points)
        queries = [(-6.0, -9.0), (-1.0, 3.0), (4.0, -4.5)]
        for query in queries:
            result = qt.k_nearest_neighbor(query, 1)
            bf_idx, _ = brute_force_knn(query, points, 1)[0]
            assert result[0].index == bf_idx, f"Query {query}: expected {bf_idx}, got {result[0].index}"

    def test_single_point_k1(self):
        qt = build_tree([(3.0, 7.0)])
        result = qt.k_nearest_neighbor((0.0, 0.0), 1)
        assert len(result) == 1
        assert result[0].index == 0
        assert result[0].item == (3.0, 7.0)

    def test_distant_query_k1(self):
        """Query far outside the domain should still return the correct point."""
        qt = build_tree(SIMPLE_POINTS)
        result = qt.k_nearest_neighbor((200.0, 200.0), 1)
        assert len(result) == 1
        bf_idx, _ = brute_force_knn((200.0, 200.0), SIMPLE_POINTS, 1)[0]
        assert result[0].index == bf_idx


# ---------------------------------------------------------------------------
# k>1 tests
# ---------------------------------------------------------------------------


class TestKNearestNeighbors:
    """k>1 correctness — correct set of k points, ordered nearest-first."""

    def _verify_knn(self, query, points, k, result_nodes):
        """Assert result matches brute force in distance and ordering."""
        bf = brute_force_knn(query, points, k)
        bf_d2s = [dist2(query, p) for _, p in bf]

        assert len(result_nodes) == min(
            k, len(points)
        ), f"Expected {min(k, len(points))} results, got {len(result_nodes)}"

        # All returned points must have distance ≤ the k-th brute-force distance
        kth_d2 = bf_d2s[-1]
        for node in result_nodes:
            d = dist2(query, node.item)
            assert d <= kth_d2 + 1e-9, (
                f"Returned point {node.item} (dist²={d:.4f}) is farther than "
                f"the {k}-th brute-force distance {kth_d2:.4f}"
            )

        # Result must be ordered nearest-first
        d2s = [dist2(query, n.item) for n in result_nodes]
        assert d2s == sorted(d2s), f"Results not sorted nearest-first: distances={d2s}"

        # The set of returned indices must match the brute-force set
        bf_indices = set(idx for idx, _ in bf)
        got_indices = set(result_indices(result_nodes))
        assert got_indices == bf_indices, f"Query {query} k={k}: expected indices {bf_indices}, got {got_indices}"

    def test_k3_scattered(self):
        qt = build_tree(SCATTERED_POINTS)
        queries = [(3.5, 2.5), (6.0, 4.0), (0.5, 0.5), (8.5, 8.5)]
        for query in queries:
            result = qt.k_nearest_neighbor(query, 3)
            self._verify_knn(query, SCATTERED_POINTS, 3, result)

    def test_k_equals_total_points(self):
        """When k == number of points, all points are returned ordered by distance."""
        qt = build_tree(SCATTERED_POINTS)
        query = (3.0, 3.0)
        k = len(SCATTERED_POINTS)
        result = qt.k_nearest_neighbor(query, k)
        self._verify_knn(query, SCATTERED_POINTS, k, result)

    def test_k_exceeds_total_points(self):
        """When k > number of points, return all points (no error, no duplicates)."""
        qt = build_tree(SCATTERED_POINTS)
        result = qt.k_nearest_neighbor((0.0, 0.0), k=100)
        indices = result_indices(result)
        assert len(indices) == len(SCATTERED_POINTS)
        assert len(set(indices)) == len(SCATTERED_POINTS), "Duplicate indices returned"

    def test_no_duplicate_indices(self):
        """Returned list must never contain the same point twice."""
        points = [(float(i), float(j)) for i in range(10) for j in range(10)]
        qt = build_tree(points)
        result = qt.k_nearest_neighbor((4.5, 4.5), 7)
        indices = result_indices(result)
        assert len(indices) == len(set(indices)), f"Duplicate indices: {indices}"

    def test_node_attributes(self):
        """QuadNode objects must expose correct .item and .index."""
        qt = build_tree(SCATTERED_POINTS)
        result = qt.k_nearest_neighbor((5.0, 5.0), 2)
        for node in result:
            assert isinstance(node, QuadNode)
            assert (
                node.item == SCATTERED_POINTS[node.index]
            ), f"Node .item {node.item} doesn't match points[{node.index}]={SCATTERED_POINTS[node.index]}"


# ---------------------------------------------------------------------------
# Large-tree stress test (exercises branch-and-bound pruning)
# ---------------------------------------------------------------------------


class TestLargeTree:
    def setup_method(self, method):
        self.points = [(float(i), float(j)) for i in range(30) for j in range(30)]
        self.qt = build_tree(self.points)

    @pytest.mark.parametrize("k", [1, 3, 8])
    @pytest.mark.parametrize(
        "query",
        [
            (14.5, 14.5),
            (0.3, 0.3),
            (28.7, 28.7),
            (-5.0, 15.0),
            (100.0, 100.0),
        ],
    )
    def test_large_tree_knn(self, query, k):
        result = self.qt.k_nearest_neighbor(query, k)
        bf = brute_force_knn(query, self.points, k)
        kth_d2 = dist2(query, bf[-1][1])

        # Correctness: all returned points are within the k-th brute-force distance
        for node in result:
            d = dist2(query, node.item)
            assert d <= kth_d2 + 1e-9

        # Same set of indices as brute force
        assert set(result_indices(result)) == {i for i, _ in bf}

        # Ordered nearest-first
        d2s = [dist2(query, n.item) for n in result]
        assert d2s == sorted(d2s)


# ---------------------------------------------------------------------------
# Rust parity test (skipped when Rust module is unavailable)
# ---------------------------------------------------------------------------

try:
    from polytope_feature.polytope_rs import QuadTree as RustQuadTree

    RUST_AVAILABLE = True
except ImportError:
    RUST_AVAILABLE = False


@pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust module not installed")
class TestRustParity:
    """Python and Rust kNN must return the same point indices and ordering."""

    def _rust_knn_indices(self, points, query, k):
        qt = RustQuadTree()
        qt.build_point_tree(list(points))
        rust_result = qt.k_nearest_neighbor(query, k, list(points))
        # Rust returns indices sorted nearest-first
        return rust_result  # List[int]

    def _py_knn_indices(self, points, query, k):
        qt = build_tree(list(points))
        nodes = qt.k_nearest_neighbor(query, k)
        return [n.index for n in nodes]

    def _check(self, points, query, k):
        rust = self._rust_knn_indices(points, query, k)
        py = self._py_knn_indices(points, query, k)
        assert set(rust) == set(py), f"Query {query} k={k}: Rust={rust}, Python={py}"
        # Both should be ordered nearest-first by distance
        assert rust == sorted(rust, key=lambda i: dist2(query, points[i]))
        assert py == sorted(py, key=lambda i: dist2(query, points[i]))

    @pytest.mark.parametrize("k", [1, 3])
    def test_simple_grid_parity(self, k):
        for query in [(1.0, 1.0), (5.1, 5.1), (11.0, 11.0)]:
            self._check(SIMPLE_POINTS, query, k)

    @pytest.mark.parametrize("k", [1, 3, 5])
    def test_scattered_parity(self, k):
        for query in [(3.5, 2.5), (6.0, 4.0), (0.0, 0.0)]:
            self._check(SCATTERED_POINTS, query, k)

    def test_large_tree_parity(self):
        points = [(float(i * 5), float(j * 5)) for i in range(15) for j in range(15)]
        for query in [(12.5, 12.5), (70.0, 0.5), (-3.0, 40.0)]:
            for k in [1, 4]:
                self._check(points, query, k)
