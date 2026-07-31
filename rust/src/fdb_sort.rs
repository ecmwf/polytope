use pyo3::prelude::*;
use std::collections::HashSet;

/// Removes duplicate sub-lists from `current_start_idxs`.
/// A sub-list at `[i][k]` is considered a duplicate if ALL its index values
/// were already seen in a previous sub-list (across all groups).
///
/// Returns the (potentially filtered) structure and a list of `(i, k)` pairs
/// that were identified as duplicates.
pub fn remove_duplicates(
    current_start_idxs: Vec<Vec<Vec<i64>>>,
) -> (Vec<Vec<Vec<i64>>>, Vec<(usize, usize)>) {
    let mut seen: HashSet<i64> = HashSet::new();
    let mut removal_pairs: Vec<(usize, usize)> = Vec::new();

    for (i, group) in current_start_idxs.iter().enumerate() {
        for (k, sublist) in group.iter().enumerate() {
            if !sublist.is_empty() && sublist.iter().all(|idx| seen.contains(idx)) {
                removal_pairs.push((i, k));
            } else {
                for &idx in sublist {
                    seen.insert(idx);
                }
            }
        }
    }

    (current_start_idxs, removal_pairs)
}

/// Sort and split index ranges across all groups.
///
/// Returns:
/// - `permutations[i]`: sort permutation for group i (order of sublist positions after sorting)
/// - `sorted_ranges`: consecutive (start, end) inclusive ranges across all groups, sorted by start
/// - `range_group[r]`: which top-level group (i) range r belongs to
/// - `removal_pairs`: (i, k) pairs of sub-lists removed by dedup
#[pyfunction]
pub fn sort_request_ranges(
    current_start_idxs: Vec<Vec<Vec<i64>>>,
    skip_dedup: bool,
) -> (
    Vec<Vec<usize>>,
    Vec<(i64, i64)>,
    Vec<usize>,
    Vec<(usize, usize)>,
) {
    let removal_pairs: Vec<(usize, usize)>;
    let data: Vec<Vec<Vec<i64>>>;

    if skip_dedup {
        removal_pairs = Vec::new();
        data = current_start_idxs;
    } else {
        let (d, rp) = remove_duplicates(current_start_idxs);
        removal_pairs = rp;
        data = d;
    }

    // Build a set of removal pairs for fast lookup
    let removal_set: HashSet<(usize, usize)> = removal_pairs.iter().cloned().collect();

    // permutations[i] = sort permutation (list of sublist indices k in sorted order)
    let mut permutations: Vec<Vec<usize>> = Vec::with_capacity(data.len());

    // Collect all ranges with their group index for later sorting
    let mut all_ranges: Vec<((i64, i64), usize)> = Vec::new();

    for (i, group) in data.iter().enumerate() {
        // Flatten all (index_value, sublist_k) pairs, skipping removed sub-lists
        let mut flat: Vec<(i64, usize)> = Vec::new();
        for (k, sublist) in group.iter().enumerate() {
            if removal_set.contains(&(i, k)) {
                continue;
            }
            for &val in sublist {
                flat.push((val, k));
            }
        }

        // Stable sort by index value
        flat.sort_by_key(|&(val, _)| val);

        // Build permutation: ordered list of sublist positions (k values) as they appear sorted
        let mut perm: Vec<usize> = flat.iter().map(|&(_, k)| k).collect();
        // Deduplicate while preserving order (each k should appear once per occurrence in flat)
        // Actually permutation tracks the k of each element in sorted order — keep as-is
        permutations.push(perm.clone());

        // Split sorted index values into consecutive ranges
        if flat.is_empty() {
            continue;
        }

        let sorted_vals: Vec<i64> = flat.iter().map(|&(v, _)| v).collect();
        let mut range_start = sorted_vals[0];
        let mut range_end = sorted_vals[0];

        for j in 1..sorted_vals.len() {
            if sorted_vals[j] - sorted_vals[j - 1] > 1 {
                all_ranges.push(((range_start, range_end), i));
                range_start = sorted_vals[j];
            }
            range_end = sorted_vals[j];
        }
        all_ranges.push(((range_start, range_end), i));
    }

    // Sort all ranges by start index ascending
    all_ranges.sort_by_key(|&((start, _), _)| start);

    let sorted_ranges: Vec<(i64, i64)> = all_ranges.iter().map(|&(r, _)| r).collect();
    let range_group: Vec<usize> = all_ranges.iter().map(|&(_, g)| g).collect();

    (permutations, sorted_ranges, range_group, removal_pairs)
}

/// Flat interface: accepts flat index array + per-group sizes, avoids nested Vec allocation.
///
/// `flat_indices`: all index values concatenated (group0_sublist0_vals, group0_sublist1_vals, ...)
/// `group_sizes[i]`: number of index values in the i-th sublist (all sublists flattened in order)
///
/// Returns: (range_starts, range_ends, flat_permutations, flat_perm_sizes, removal_group_indices)
/// - range_starts / range_ends: flat sorted range pairs
/// - flat_permutations: all permutations concatenated
/// - flat_perm_sizes: number of elements in each permutation
/// - removal_group_indices: flat list of sublist global indices that were removed (dedup)
#[pyfunction]
pub fn sort_request_ranges_flat(
    flat_indices: Vec<i64>,
    group_sizes: Vec<usize>,
    skip_dedup: bool,
) -> (Vec<i64>, Vec<i64>, Vec<usize>, Vec<usize>, Vec<usize>) {
    // Reconstruct sublists from flat arrays
    let mut sublists: Vec<Vec<i64>> = Vec::with_capacity(group_sizes.len());
    let mut offset = 0usize;
    for &sz in &group_sizes {
        sublists.push(flat_indices[offset..offset + sz].to_vec());
        offset += sz;
    }

    // Dedup across all sublists (treating each sublist as a flat "node")
    let removal_sublist_indices: Vec<usize>;
    if skip_dedup {
        removal_sublist_indices = Vec::new();
    } else {
        let mut seen: HashSet<i64> = HashSet::new();
        let mut removals: Vec<usize> = Vec::new();
        for (idx, sublist) in sublists.iter().enumerate() {
            if !sublist.is_empty() && sublist.iter().all(|v| seen.contains(v)) {
                removals.push(idx);
            } else {
                for &v in sublist {
                    seen.insert(v);
                }
            }
        }
        removal_sublist_indices = removals;
    }

    let removal_set: HashSet<usize> = removal_sublist_indices.iter().cloned().collect();

    let mut all_ranges: Vec<(i64, i64)> = Vec::new();
    let mut flat_permutations: Vec<usize> = Vec::new();
    let mut flat_perm_sizes: Vec<usize> = Vec::new();

    for (idx, sublist) in sublists.iter().enumerate() {
        if removal_set.contains(&idx) {
            continue;
        }
        // Sort values, tracking original positions for permutation
        let mut indexed: Vec<(i64, usize)> = sublist.iter().cloned().enumerate().map(|(i, v)| (v, i)).collect();
        indexed.sort_by_key(|&(v, _)| v);

        // Permutation: original positions in sorted order
        let perm: Vec<usize> = indexed.iter().map(|&(_, orig)| orig).collect();
        flat_perm_sizes.push(perm.len());
        flat_permutations.extend_from_slice(&perm);

        // Build consecutive ranges from sorted values
        if indexed.is_empty() {
            continue;
        }
        let sorted_vals: Vec<i64> = indexed.iter().map(|&(v, _)| v).collect();
        let mut range_start = sorted_vals[0];
        let mut range_end = sorted_vals[0];
        for j in 1..sorted_vals.len() {
            if sorted_vals[j] - sorted_vals[j - 1] > 1 {
                all_ranges.push((range_start, range_end));
                range_start = sorted_vals[j];
            }
            range_end = sorted_vals[j];
        }
        all_ranges.push((range_start, range_end));
    }

    // Sort ranges by start
    all_ranges.sort_by_key(|&(s, _)| s);

    let range_starts: Vec<i64> = all_ranges.iter().map(|&(s, _)| s).collect();
    let range_ends: Vec<i64> = all_ranges.iter().map(|&(_, e)| e).collect();

    (range_starts, range_ends, flat_permutations, flat_perm_sizes, removal_sublist_indices)
}

/// Compute Cartesian product of all `value_lists`.
/// Returns one `Vec<String>` per combination.
#[pyfunction]
pub fn expand_compressed_requests(value_lists: Vec<Vec<String>>) -> Vec<Vec<String>> {
    let mut result: Vec<Vec<String>> = vec![vec![]];

    for list in &value_lists {
        if list.is_empty() {
            return Vec::new();
        }
        let mut next: Vec<Vec<String>> = Vec::with_capacity(result.len() * list.len());
        for existing in &result {
            for val in list {
                let mut combo = existing.clone();
                combo.push(val.clone());
                next.push(combo);
            }
        }
        result = next;
    }

    result
}

/// Flat interface for Cartesian product: accepts flat string array + per-list sizes.
/// Returns: flat output strings (all combinations concatenated) and combo_size (= list_sizes.len()).
/// Python can split the flat output into chunks of combo_size.
#[pyfunction]
pub fn expand_compressed_requests_flat(
    flat_values: Vec<String>,
    list_sizes: Vec<usize>,
) -> (Vec<String>, usize) {
    // Reconstruct value lists
    let mut value_lists: Vec<Vec<String>> = Vec::with_capacity(list_sizes.len());
    let mut offset = 0usize;
    for &sz in &list_sizes {
        value_lists.push(flat_values[offset..offset + sz].to_vec());
        offset += sz;
    }

    let combo_size = list_sizes.len();
    if combo_size == 0 {
        return (Vec::new(), 0);
    }

    // Check for empty list
    for list in &value_lists {
        if list.is_empty() {
            return (Vec::new(), combo_size);
        }
    }

    // Compute product size upfront
    let total: usize = value_lists.iter().map(|l| l.len()).product();
    let mut flat_result: Vec<String> = Vec::with_capacity(total * combo_size);

    // Iterative product using index counters
    let mut indices = vec![0usize; combo_size];
    for _ in 0..total {
        for (i, list) in value_lists.iter().enumerate() {
            flat_result.push(list[indices[i]].clone());
        }
        // Increment indices (rightmost first)
        let mut carry = true;
        for i in (0..combo_size).rev() {
            if carry {
                indices[i] += 1;
                if indices[i] >= value_lists[i].len() {
                    indices[i] = 0;
                } else {
                    carry = false;
                }
            }
        }
    }

    (flat_result, combo_size)
}

#[cfg(test)]
mod tests {
    use super::*;

    // ── remove_duplicates ────────────────────────────────────────────────────

    #[test]
    fn test_remove_duplicates_empty() {
        let (data, pairs) = remove_duplicates(vec![]);
        assert!(data.is_empty());
        assert!(pairs.is_empty());
    }

    #[test]
    fn test_remove_duplicates_single_element() {
        let input = vec![vec![vec![1i64]]];
        let (_, pairs) = remove_duplicates(input);
        assert!(pairs.is_empty());
    }

    #[test]
    fn test_remove_duplicates_no_dups() {
        let input = vec![vec![vec![1i64, 2], vec![3, 4]]];
        let (_, pairs) = remove_duplicates(input);
        assert!(pairs.is_empty());
    }

    #[test]
    fn test_remove_duplicates_full_dup() {
        // second sublist [1,2] is completely seen after first sublist [1,2]
        let input = vec![vec![vec![1i64, 2], vec![1, 2]]];
        let (_, pairs) = remove_duplicates(input);
        assert_eq!(pairs, vec![(0, 1)]);
    }

    #[test]
    fn test_remove_duplicates_partial_dup_not_removed() {
        // [1,3] — 1 seen but 3 not → not a full duplicate
        let input = vec![vec![vec![1i64, 2], vec![1, 3]]];
        let (_, pairs) = remove_duplicates(input);
        assert!(pairs.is_empty());
    }

    #[test]
    fn test_remove_duplicates_across_groups() {
        let input = vec![
            vec![vec![10i64, 11]],
            vec![vec![10i64, 11]], // all seen → duplicate
        ];
        let (_, pairs) = remove_duplicates(input);
        assert_eq!(pairs, vec![(1, 0)]);
    }

    // ── sort_request_ranges ──────────────────────────────────────────────────

    #[test]
    fn test_sort_request_ranges_empty() {
        let (perms, ranges, rg, rp) = sort_request_ranges(vec![], false);
        assert!(perms.is_empty());
        assert!(ranges.is_empty());
        assert!(rg.is_empty());
        assert!(rp.is_empty());
    }

    #[test]
    fn test_sort_request_ranges_all_consecutive() {
        // indices 0..=4 → one range (0,4)
        let input = vec![vec![vec![0i64, 1, 2, 3, 4]]];
        let (_, ranges, rg, _) = sort_request_ranges(input, true);
        assert_eq!(ranges, vec![(0, 4)]);
        assert_eq!(rg, vec![0]);
    }

    #[test]
    fn test_sort_request_ranges_gaps() {
        // 0,1,2 then gap then 5,6
        let input = vec![vec![vec![0i64, 1, 2, 5, 6]]];
        let (_, ranges, rg, _) = sort_request_ranges(input, true);
        assert_eq!(ranges, vec![(0, 2), (5, 6)]);
        assert_eq!(rg, vec![0, 0]);
    }

    #[test]
    fn test_sort_request_ranges_dedup_removed() {
        let input = vec![vec![vec![1i64, 2], vec![1, 2]]];
        let (_, _, _, rp) = sort_request_ranges(input, false);
        assert_eq!(rp, vec![(0, 1)]);
    }

    #[test]
    fn test_sort_request_ranges_skip_dedup() {
        let input = vec![vec![vec![1i64, 2], vec![1, 2]]];
        let (_, _, _, rp) = sort_request_ranges(input, true);
        assert!(rp.is_empty());
    }

    #[test]
    fn test_sort_request_ranges_multi_group_sorted() {
        // group 0: [10], group 1: [1,2]
        // ranges should be sorted: (1,2) before (10,10)
        let input = vec![vec![vec![10i64]], vec![vec![1i64, 2]]];
        let (_, ranges, rg, _) = sort_request_ranges(input, true);
        assert_eq!(ranges[0], (1, 2));
        assert_eq!(ranges[1], (10, 10));
        assert_eq!(rg[0], 1);
        assert_eq!(rg[1], 0);
    }

    #[test]
    fn test_sort_request_ranges_large_input() {
        use std::collections::BTreeSet;
        // Generate 5000 indices with some gaps (every 3rd index)
        let indices: Vec<i64> = (0..5000i64).map(|x| x * 3).collect();
        let input = vec![vec![indices.clone()]];
        let (_, ranges, rg, _) = sort_request_ranges(input, true);
        // Each index is isolated (gap of 3) → 5000 ranges
        assert_eq!(ranges.len(), 5000);
        assert!(rg.iter().all(|&g| g == 0));
    }

    #[test]
    fn test_sort_request_ranges_permutation() {
        // sublist 0: [5], sublist 1: [1] → sorted order is sublist 1 then sublist 0
        let input = vec![vec![vec![5i64], vec![1i64]]];
        let (perms, _, _, _) = sort_request_ranges(input, true);
        // flat after sort: [(1,1),(5,0)] → perm = [1, 0]
        assert_eq!(perms[0], vec![1, 0]);
    }

    // ── expand_compressed_requests ───────────────────────────────────────────

    #[test]
    fn test_expand_empty_input() {
        let result = expand_compressed_requests(vec![]);
        // product of no lists = one empty combination
        assert_eq!(result, vec![vec![] as Vec<String>]);
    }

    #[test]
    fn test_expand_empty_list_in_input() {
        let result = expand_compressed_requests(vec![
            vec!["a".to_string()],
            vec![],
        ]);
        assert!(result.is_empty());
    }

    #[test]
    fn test_expand_single_list() {
        let result = expand_compressed_requests(vec![
            vec!["x".to_string(), "y".to_string(), "z".to_string()],
        ]);
        assert_eq!(result, vec![
            vec!["x".to_string()],
            vec!["y".to_string()],
            vec!["z".to_string()],
        ]);
    }

    #[test]
    fn test_expand_three_lists() {
        let result = expand_compressed_requests(vec![
            vec!["a".to_string(), "b".to_string()],
            vec!["1".to_string(), "2".to_string()],
            vec!["x".to_string(), "y".to_string()],
        ]);
        assert_eq!(result.len(), 8); // 2×2×2
        // Verify first and last combinations
        assert_eq!(result[0], vec!["a", "1", "x"]);
        assert_eq!(result[7], vec!["b", "2", "y"]);
    }

    #[test]
    fn test_expand_varying_sizes() {
        let result = expand_compressed_requests(vec![
            vec!["a".to_string(), "b".to_string(), "c".to_string()],
            vec!["1".to_string()],
            vec!["x".to_string(), "y".to_string()],
        ]);
        assert_eq!(result.len(), 6); // 3×1×2
    }
}
