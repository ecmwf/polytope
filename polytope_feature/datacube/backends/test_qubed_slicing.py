from qubed import Qube
from qubed.value_types import QEnum
from typing import Iterator
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


def slice(q: Qube, request: dict) -> 'Qube':
    def _slice(q: Qube, r: dict) -> Iterator[Qube]:
        for child in q.children:
            requested_values = r.get(child.key, [])
            found_values = [v for v in requested_values if v in child.values]
            if not found_values:
                continue
            truncated_request = {k: v for k, v in r.items() if k != child.key}
            children = list(_slice(child, truncated_request))

            # If this node used to have children, i.e was not a leaf node,
            # but as a result of filtering now has no children
            # then filter it out.
            if child.children and not children:
                continue

            yield Qube.make(
                key=child.key,
                values=QEnum(found_values),
                metadata=child.metadata,
                children=children,
            )

    return Qube.root_node(list(_slice(q, request)))


request = {
    "expver": ["0001"],
    "class": ["rd", "od"],
    "param": ["1", "2", "3"],
}


print(q)
# q = slice(q, request)

# print(q)

# new_q = Qube.from_dict({
#     "expver=0001": {"param=1/2/3/4/5": {"level=0/1/2": {}}},
#     "expver=0001": {"param=1": {"level=3/4": {}}, "param=2": {"level=3/4": {}}},
# }).compress()

new_q = Qube.from_dict({
    "expver=0001": {"param=1/2/3/4/5": {"level=0/1/2": {}}, "param=1": {"level=3/4": {}}, "param=2": {"level=3/4": {}}},
    # "expver=0001": {"param=1": {"level=3/4": {}}, "param=2": {"level=3/4": {}}},
}).compress()

print("HERE")
print(new_q)

print(new_q["expver", "0001"].children)


def modified_slice(q: Qube, request: dict) -> 'Qube':
    def _slice(q: Qube, r: dict) -> Iterator[Qube]:
        for child in q.children:
            requested_values = r.get(child.key, [])
            found_values = [v for v in requested_values if v in child.values]
            if not found_values:
                continue
            print("HERE")
            print(r.items())
            for k, v in r.items():
                if k == "param":
                    if "1" in v:
                        truncated_request = {"level": "2"}
                        children = list(_slice(child, truncated_request))
                    if "2" in v:
                        truncated_request = {"level": ["1", "2", "3"]}
                        children = list(_slice(child, truncated_request))
                    if "3" in v:
                        truncated_request = {"level": "2"}
                        children = list(_slice(child, truncated_request))
                else:
                    truncated_request = {k: v for k, v in r.items() if k != child.key}
                    children = list(_slice(child, truncated_request))

            # If this node used to have children, i.e was not a leaf node,
            # but as a result of filtering now has no children
            # then filter it out.
            if child.children and not children:
                continue

            # for child in children:
            #     yield Qube.make(
            #         key=child.key,
            #         values=QEnum(found_values),
            #         metadata=child.metadata,
            #         children=list(child),
            #     )
            print("WHAT NODES DID WE CREATE?")
            print(Qube.make(
                key=child.key,
                values=QEnum(found_values),
                metadata=child.metadata,
                children=children,
            ))
            yield Qube.make(
                key=child.key,
                values=QEnum(found_values),
                metadata=child.metadata,
                children=children,
            )

    return Qube.root_node(list(_slice(q, request)))


print(modified_slice(new_q, request={
    "expver": ["0001"],
    "param": ["1", "2", "3"],
}))
