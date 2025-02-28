from qubed import Qube
from qubed.value_types import QEnum
from typing import Iterator
from ...engine.hullslicer import slice
from copy import deepcopy
# from ...shapes import ConvexPolytope

q = Qube.from_dict({
    "class=od": {
        "expver=0001": {"param=1/2/3/4/5": {}},
        "expver=0002": {"param=1": {}, "param=2": {}},
    },
    "class=rd": {
        "expver=0001": {
            "param=1/2/3": {},
            "expver=0001": {"param=1/2/3": {}, }
        },
        "expver=0002": {"param=1/2/3/4": {}},
    },
}).compress()

# polytopes_list = [ConvexPolytope(), ]


# def slice_poly(q: Qube, polytope):
#     def _slice_poly(q: Qube, poly):
#         for child in q.children:
#             # For each child, find the polytopes we should slice on that axis
#             right_unsliced_polytopes = []
#             for polytope in q.metadata["unsliced_polytopes"]:
#                 if q.key in polytope._axes:
#                     right_unsliced_polytopes.append(polytope)

#             for i, polytope in enumerate(right_unsliced_polytopes):
#                 lower, upper, slice_axis_idx = polytope.extents(q.key)


# def slice(q: Qube, request: dict) -> 'Qube':
#     def _slice(q: Qube, r: dict) -> Iterator[Qube]:
#         for child in q.children:
#             requested_values = r.get(child.key, [])
#             found_values = [v for v in requested_values if v in child.values]
#             if not found_values:
#                 continue
#             truncated_request = {k: v for k, v in r.items() if k != child.key}
#             children = list(_slice(child, truncated_request))

#             # If this node used to have children, i.e was not a leaf node,
#             # but as a result of filtering now has no children
#             # then filter it out.
#             if child.children and not children:
#                 continue

#             yield Qube.make(
#                 key=child.key,
#                 values=QEnum(found_values),
#                 metadata=child.metadata,
#                 children=children,
#             )

#     return Qube.root_node(list(_slice(q, request)))

def slice(q: Qube, request: dict) -> 'Qube':
    def _slice(q: Qube, r: dict) -> list[Qube]:
        result = []
        for child in q.children:
            requested_values = r.get(child.key, [])
            found_values = [v for v in requested_values if v in child.values]
            if not found_values:
                continue
            truncated_request = {k: v for k, v in r.items() if k != child.key}
            children = _slice(child, truncated_request)

            # If this node used to have children but now has none due to filtering, skip it.
            if child.children and not children:
                continue

            if len(found_values) > 1:
                result.extend([Qube.make(
                    key=child.key,
                    values=QEnum(val),
                    metadata=child.metadata,
                    children=children,
                ) for val in found_values])
            else:
                result.extend([Qube.make(
                    key=child.key,
                    values=QEnum(found_values),
                    metadata=child.metadata,
                    children=children
                )])

        return result

    return Qube.root_node(_slice(q, request))


request = {
    "expver": ["0001"],
    "class": ["rd", "od"],
    "param": ["1", "2", "3"],
}


print(q)
q = slice(q, request)

print(q)

# new_q = Qube.from_dict({
#     "expver=0001": {"param=1/2/3/4/5": {"level=0/1/2": {}}},
#     "expver=0001": {"param=1": {"level=3/4": {}}, "param=2": {"level=3/4": {}}},
# }).compress()

# new_q = Qube.from_dict({
#     "expver=0001": {"param=1/2/3/4/5": {"level=0/1/2": {}}, "param=1": {"level=3/4": {}}, "param=2": {"level=3/4": {}}},
#     # "expver=0001": {"param=1": {"level=3/4": {}}, "param=2": {"level=3/4": {}}},
# }).compress()

# print("HERE")
# print(new_q)

# print(new_q["expver", "0001"].children)


# def modified_slice(q: Qube, request: dict) -> 'Qube':
#     def _slice(q: Qube, r: dict) -> Iterator[Qube]:
#         for child in q.children:
#             requested_values = r.get(child.key, [])
#             found_values = [v for v in requested_values if v in child.values]
#             if not found_values:
#                 continue
#             print("HERE")
#             print(r.items())
#             for k, v in r.items():
#                 if k == "param":
#                     children = []
#                     if "1" in found_values:
#                         truncated_request = {"level": "2"}
#                         children.extend(list(_slice(child, truncated_request)))
#                     if "2" in found_values:
#                         truncated_request = {"level": ["1", "2", "3"]}
#                         children.extend(list(_slice(child, truncated_request)))
#                     if "3" in found_values:
#                         truncated_request = {"level": "2"}
#                         children.extend(list(_slice(child, truncated_request)))
#                 else:
#                     truncated_request = {k: v for k, v in r.items() if k != child.key}
#                     children = list(_slice(child, truncated_request))

#             # If this node used to have children, i.e was not a leaf node,
#             # but as a result of filtering now has no children
#             # then filter it out.
#             if child.children and not children:
#                 continue

#             # for child in children:
#             #     yield Qube.make(
#             #         key=child.key,
#             #         values=QEnum(found_values),
#             #         metadata=child.metadata,
#             #         children=list(child),
#             #     )
#             print("WHAT NODES DID WE CREATE?")
#             print(Qube.make(
#                 key=child.key,
#                 values=QEnum(found_values),
#                 metadata=child.metadata,
#                 children=children,
#             ))
#             yield Qube.make(
#                 key=child.key,
#                 values=QEnum(found_values),
#                 metadata=child.metadata,
#                 children=children,
#             )

#     return Qube.root_node(list(_slice(q, request)))


# print(modified_slice(new_q, request={
#     "expver": ["0001"],
#     "param": ["1", "2", "3"],
# }))


def actual_slice(q: Qube, polytopes_to_slice) -> 'Qube':

    def find_polytopes_on_axis(q: Qube, polytopes):
        polytopes_on_axis = []
        axis_name = q.key
        for poly in polytopes:
            if axis_name in poly._axes:
                polytopes_on_axis.append(poly)
        return polytopes_on_axis

    def _axes_compressed():
        return {}

    def _slice(q: Qube, polytopes) -> list[Qube]:
        result = []
        for child in q.children:
            # find polytopes which are defined on axis child.key
            polytopes_on_axis = find_polytopes_on_axis(child, polytopes)
            # for each polytope:
            for poly in polytopes_on_axis:
                # find extents of polytope on child.key
                lower, upper, slice_axis_idx = poly.extents(child.key)
                # find values on child that are within extents
                found_vals = [v for v in child.values if lower <= v <= upper]
                # slice polytope along each value on child and keep resulting polytopes in memory
                sliced_polys = []
                for val in found_vals:
                    # slice polytope along the value and add sliced polytope to list of polytopes in memory
                    sliced_poly = slice(poly, child.key, val, slice_axis_idx)
                    sliced_polys.append(sliced_poly)

                # decide if axis should be compressed or not according to polytope
                axis_compressed = _axes_compressed.get(child.key, False)
                # if it's not compressed, need to separate into different nodes to append to the tree
                if not axis_compressed and len(found_vals) > 1:
                    for i, found_val in enumerate(found_vals):
                        child_polytopes = deepcopy(polytopes)
                        child_polytopes.remove(poly)
                        child_polytopes.append(sliced_polys[i])
                        children = _slice(child, child_polytopes)
                        # If this node used to have children but now has none due to filtering, skip it.
                        if child.children and not children:
                            continue
                        # TODO: add the child_polytopes to the child.metadata/ ie change child.metadata here before passing
                        qube_node = Qube.make(key=child.key,
                                              values=QEnum(found_val),
                                              metadata=child.metadata,
                                              children=children)
                        result.append(qube_node)
                else:
                    # if it's compressed, then can add all found values in a single node
                    child_polytopes = deepcopy(polytopes)
                    child_polytopes.remove(poly)
                    child_polytopes.extend(sliced_polys)
                    # create children
                    children = _slice(child, child_polytopes)
                    # If this node used to have children but now has none due to filtering, skip it.
                    if child.children and not children:
                        continue
                    # TODO: add the child_polytopes to the child.metadata/ ie change child.metadata here before passing
                    result.extend([Qube.make(
                        key=child.key,
                        values=QEnum(found_vals),
                        metadata=child.metadata,
                        children=children
                    )])

        return result

    return Qube.root_node(_slice(q, polytopes_to_slice))


# TODO: OLD CODE TO MODIFY
    # requested_values = r.get(child.key, [])
    # found_values = [v for v in requested_values if v in child.values]
    # if not found_values:
    #     continue
    # truncated_request = {k: v for k, v in r.items() if k != child.key}
    # children = _slice(child, truncated_request)

    # # If this node used to have children but now has none due to filtering, skip it.
    # if child.children and not children:
    #     continue

    # if len(found_values) > 1:
    #     result.extend([Qube.make(
    #         key=child.key,
    #         values=QEnum(val),
    #         metadata=child.metadata,
    #         children=children,
    #     ) for val in found_values])
    # else:
    #     result.extend([Qube.make(
    #         key=child.key,
    #         values=QEnum(found_values),
    #         metadata=child.metadata,
    #         children=children
    #     )])
