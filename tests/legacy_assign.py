"""The per-range result assignment that ``FDBDatacube.assign_fdb_output_to_nodes`` replaced.

Kept to prove that the flat (``values_flat``) path writes exactly the same ``values`` and ``result`` into the tree,
and to measure what it cost (``performance/tree_memory.py --legacy``).  It reads the same bookkeeping as the new
path (``FieldRequests``), takes one numpy object per request range from ``result.values`` and accumulates the
chunks of every leaf of the whole call before concatenating them, which is what made a HEALPix request hold
millions of live numpy objects.
"""

from polytope_feature.datacube.tree_values import finalise_result, restore_value_order


def legacy_assign_fdb_output_to_nodes(datacube, output_iterator, fdb_requests_decoding_info):
    chunks_by_node = {}
    for k, result in enumerate(output_iterator):
        field_requests, _field_index = fdb_requests_decoding_info[k]
        original_indices = field_requests.original_indices
        fdb_node_ranges = field_requests.node_ranges
        sorted_ranges = field_requests.ranges
        sorted_fdb_range_nodes = [fdb_node_ranges[i] for i in original_indices]
        for i in range(len(sorted_fdb_range_nodes)):
            n = sorted_fdb_range_nodes[i][0]
            owner = getattr(n, "_result_owner", n)
            entry = chunks_by_node.get(id(owner))
            if entry is None:
                entry = chunks_by_node[id(owner)] = (owner, [])
            if len(result.values) == 0:
                # no data was found for this path in the fdb: one None per point of this range
                n_points = sorted_ranges[i][1] - sorted_ranges[i][0]
                entry[1].append([None] * n_points)
            else:
                entry[1].append(result.values[i])
    for owner, chunks in chunks_by_node.values():
        result = finalise_result(chunks)
        order = datacube._leaf_result_orders.get(id(owner))
        if order is not None:
            # results arrive in grid-index order; put them back in the order of the leaf's values
            result = restore_value_order(result, order)
        if len(owner.result) != 0:
            result = finalise_result([list(owner.result), list(result)])
        owner.result = result


def use_legacy_assignment(monkeypatch):
    """Make every ``FDBDatacube.get`` in this test use the per-range assignment."""
    from polytope_feature.datacube.backends.fdb import FDBDatacube

    monkeypatch.setattr(FDBDatacube, "assign_fdb_output_to_nodes", legacy_assign_fdb_output_to_nodes)
