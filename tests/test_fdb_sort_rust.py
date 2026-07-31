"""
Integration tests for Rust-accelerated sort_request_ranges and expand_compressed_requests,
comparing against equivalent Python reference implementations.
"""

import itertools

import pytest

try:
    from polytope_feature.polytope_rs import (
        expand_compressed_requests,
        sort_request_ranges,
    )

    HAS_RUST = True
except ImportError:
    HAS_RUST = False

pytestmark = pytest.mark.skipif(not HAS_RUST, reason="polytope_rs not available")


# ---------------------------------------------------------------------------
# Python reference implementations
# ---------------------------------------------------------------------------


def py_sort_request_ranges(current_start_idxs, skip_dedup=False):
    """Pure-Python equivalent used to validate the Rust output."""
    seen = set()
    removal_pairs = []

    if not skip_dedup:
        for i, group in enumerate(current_start_idxs):
            for k, sublist in enumerate(group):
                if sublist and all(idx in seen for idx in sublist):
                    removal_pairs.append((i, k))
                else:
                    seen.update(sublist)

    removal_set = set(removal_pairs)
    permutations = []
    all_ranges = []

    for i, group in enumerate(current_start_idxs):
        flat = []
        for k, sublist in enumerate(group):
            if (i, k) in removal_set:
                continue
            for val in sublist:
                flat.append((val, k))

        flat.sort(key=lambda x: x[0])
        permutations.append([k for _, k in flat])

        if not flat:
            continue

        vals = [v for v, _ in flat]
        rs, re = vals[0], vals[0]
        for j in range(1, len(vals)):
            if vals[j] - vals[j - 1] > 1:
                all_ranges.append(((rs, re), i))
                rs = vals[j]
            re = vals[j]
        all_ranges.append(((rs, re), i))

    all_ranges.sort(key=lambda x: x[0][0])
    sorted_ranges = [r for r, _ in all_ranges]
    range_group = [g for _, g in all_ranges]
    return permutations, sorted_ranges, range_group, removal_pairs


def py_expand_compressed_requests(value_lists):
    """Pure-Python cartesian product (returns list of lists)."""
    result = [[]]
    for lst in value_lists:
        if not lst:
            return []
        result = [existing + [v] for existing in result for v in lst]
    return result


# ---------------------------------------------------------------------------
# Tests — sort_request_ranges
# ---------------------------------------------------------------------------


class TestSortRequestRanges:

    def test_basic_two_groups(self):
        """Two groups with unsorted sublists; each sublist sorted ascending."""
        data = [[[5, 2, 8]], [[3, 1]]]
        r_perms, r_ranges, r_rg, r_rp = sort_request_ranges(data, False)
        p_perms, p_ranges, p_rg, p_rp = py_sort_request_ranges(data, False)

        assert r_ranges == p_ranges
        assert r_rg == p_rg
        assert r_rp == p_rp
        assert r_perms == p_perms

    def test_consecutive_indices_merged(self):
        """[1,2,3,7,8,9] → ranges [(1,3),(7,9)]."""
        data = [[[1, 2, 3, 7, 8, 9]]]
        _, r_ranges, _, _ = sort_request_ranges(data, True)
        assert r_ranges == [(1, 3), (7, 9)]

    def test_dedup_removes_second_occurrence(self):
        """Two sublists sharing the same indices; skip_dedup=False removes second."""
        data = [[[5, 10], [5, 10]]]
        _, _, _, r_rp = sort_request_ranges(data, False)
        assert (0, 1) in r_rp

    def test_skip_dedup_keeps_both(self):
        """skip_dedup=True means no removal_pairs even with duplicates."""
        data = [[[5, 10], [5, 10]]]
        _, _, _, r_rp = sort_request_ranges(data, True)
        assert r_rp == []

    def test_dedup_matches_python(self):
        """Dedup behaviour matches Python reference for multi-group input."""
        data = [[[10, 11]], [[10, 11]]]
        r_perms, r_ranges, r_rg, r_rp = sort_request_ranges(data, False)
        p_perms, p_ranges, p_rg, p_rp = py_sort_request_ranges(data, False)
        assert r_rp == p_rp
        assert r_ranges == p_ranges
        assert r_rg == p_rg

    def test_large_input_no_gaps_within_range(self):
        """1000 indices with gaps of 3 → each index becomes its own range; ranges are valid."""
        indices = list(range(0, 3000, 3))  # [0, 3, 6, …, 2997]
        data = [[indices]]
        _, r_ranges, _, _ = sort_request_ranges(data, True)
        # Each range must be self-contained (start == end for gap-3 sequence)
        for start, end in r_ranges:
            assert start <= end
            # No gap within a range
            assert end - start == 0  # every index is isolated

        assert len(r_ranges) == 1000

    def test_large_input_consecutive_block(self):
        """1000 consecutive indices → single range (0, 999)."""
        indices = list(range(1000))
        data = [[indices]]
        _, r_ranges, _, _ = sort_request_ranges(data, True)
        assert r_ranges == [(0, 999)]

    def test_large_input_mixed_gaps(self):
        """Mixed consecutive runs; Rust and Python produce identical ranges."""
        # blocks of 10 separated by gap of 5
        indices = []
        for b in range(50):
            base = b * 15
            indices.extend(range(base, base + 10))
        data = [[indices]]
        r_perms, r_ranges, r_rg, r_rp = sort_request_ranges(data, True)
        p_perms, p_ranges, p_rg, p_rp = py_sort_request_ranges(data, True)
        assert r_ranges == p_ranges
        assert r_rg == p_rg


# ---------------------------------------------------------------------------
# Tests — expand_compressed_requests
# ---------------------------------------------------------------------------


class TestExpandCompressedRequests:

    def test_basic_cartesian_product(self):
        """Basic 2×3×1 product matches itertools.product."""
        value_lists = [["a", "b"], ["x", "y", "z"], ["1"]]
        r = expand_compressed_requests(value_lists)
        expected = [list(c) for c in itertools.product(*value_lists)]
        assert r == expected

    def test_empty_input_returns_one_empty_combo(self):
        """Empty list of lists → one empty combination (identity for product)."""
        r = expand_compressed_requests([])
        assert r == [[]]

    def test_list_with_empty_sublist_returns_empty(self):
        """If any sub-list is empty the product is empty."""
        assert expand_compressed_requests([[]]) == []
        assert expand_compressed_requests([["a"], [], ["b"]]) == []

    def test_single_list(self):
        """Single list of N items → N singleton combos."""
        value_lists = [["p", "q", "r"]]
        r = expand_compressed_requests(value_lists)
        assert r == [["p"], ["q"], ["r"]]

    def test_two_lists(self):
        """2×2 = 4 combinations; order matches itertools.product."""
        value_lists = [["a", "b"], ["1", "2"]]
        r = expand_compressed_requests(value_lists)
        expected = [list(c) for c in itertools.product(*value_lists)]
        assert r == expected

    def test_large_cartesian_product(self):
        """5 lists × 10 values each = 100,000 combinations; verify count and boundary items."""
        value_lists = [[str(i) for i in range(10)] for _ in range(5)]
        r = expand_compressed_requests(value_lists)
        expected = [list(c) for c in itertools.product(*value_lists)]
        assert len(r) == 100_000
        assert r[0] == expected[0]
        assert r[-1] == expected[-1]

    def test_matches_python_reference_various(self):
        """Cross-check Rust against Python reference for several shapes."""
        cases = [
            [["yes", "no"]],
            [["a", "b", "c"], ["1", "2"]],
            [["x"], ["y"], ["z"]],
            [["cat", "dog"], ["big", "small"], ["fast", "slow"]],
        ]
        for value_lists in cases:
            r = expand_compressed_requests(value_lists)
            expected = py_expand_compressed_requests(value_lists)
            assert r == expected, f"Mismatch for {value_lists}"
