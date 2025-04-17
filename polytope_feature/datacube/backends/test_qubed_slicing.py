from qubed import Qube
from qubed.value_types import QEnum
from typing import Iterator
from ...engine.hullslicer import slice
from copy import deepcopy
import pandas as pd
from ..datacube_axis import UnsliceableDatacubeAxis
from ..transformations.datacube_mappers.datacube_mappers import DatacubeMapper
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

def slice_new(q: Qube, request: dict) -> 'Qube':
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


# print(q)
# q = slice(q, request)

# print(q)

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


def actual_slice(q: Qube, polytopes_to_slice, datacube_axes, datacube_transformations) -> 'Qube':

    def find_polytopes_on_axis(axis_name, polytopes):
        polytopes_on_axis = []
        # axis_name = q.key
        for poly in polytopes:
            if axis_name in poly._axes:
                polytopes_on_axis.append(poly)
        return polytopes_on_axis

    def change_poly_axis_type(axis_name, polytopes, datacube_axes):
        axis = datacube_axes[axis_name]
        # TODO: loop through the polytopes and change each polytopes's values according to axis
        if isinstance(axis, UnsliceableDatacubeAxis):
            return

        for poly in polytopes:
            i = 0
            for k, ax_name in enumerate(poly._axes):
                if ax_name == axis_name:
                    i = k
            for j, val in enumerate(poly.points):
                poly.points[j][i] = axis.to_float(axis.parse(poly.points[j][i]))

    def _axes_compressed():
        return {}

    def change_datacube_val_types(child: Qube, datacube_transformations):
        axis_name = child.key
        transformation = datacube_transformations.get(axis_name, None)
        child_vals = child.values
        new_vals = []
        for val in child_vals:
            if transformation:
                new_vals.append(transformation.transform_type(val))
            else:
                new_vals.append(val)

        return new_vals

    def transform_upper_lower(axis_name, lower, upper, datacube_axes):
        ax = datacube_axes[axis_name]
        if isinstance(ax, UnsliceableDatacubeAxis):
            return (lower, upper)
        tol = ax.tol
        lower = ax.from_float(lower - tol)
        upper = ax.from_float(upper + tol)

        return (lower, upper)

    def find_grid_axes():
        # TODO: handle grid axes
        pass

    def _slice(q: Qube, polytopes, datacube_axes, datacube_transformations) -> list[Qube]:
        result = []

        if len(q.children) == 0:
            # TODO: add "fake" axes and their nodes in order -> what about merged axes??
            mapper_transformation = None
            for transformation in datacube_transformations:
                if isinstance(transformation, DatacubeMapper):
                    mapper_transformation = transformation
            if not mapper_transformation:
                # There is no grid mapping
                pass
            else:
                # TODO: Slice on the two grid axes
                grid_axes = mapper_transformation._final_mapped_axes

                # TODO: Handle first grid axis
                polytopes_on_axis = find_polytopes_on_axis(grid_axes[0], polytopes)

                pass
            pass
        for i, child in enumerate(q.children):
            # find polytopes which are defined on axis child.key
            polytopes_on_axis = find_polytopes_on_axis(child.key, polytopes)

            # here now first change the values in the polytopes on the axis to reflect the axis type

            # for each polytope:
            for poly in polytopes_on_axis:
                # find extents of polytope on child.key
                lower, upper, slice_axis_idx = poly.extents(child.key)

                # find values on child that are within extents
                # here first change the child values of the datacube ie the Qubed tree to their right type with the transformation
                modified_vals = change_datacube_val_types(child, datacube_transformations)

                # here use the axis to transform lower and upper to right type too
                new_lower, new_upper = transform_upper_lower(child.key, lower, upper, datacube_axes)
                found_vals = [v for v in modified_vals if new_lower <= v <= new_upper]

                if len(found_vals) == 0:
                    continue

                # slice polytope along each value on child and keep resulting polytopes in memory
                sliced_polys = []
                for val in found_vals:
                    ax = datacube_axes[child.key]
                    if not isinstance(ax, UnsliceableDatacubeAxis):
                        fval = ax.to_float(val)
                        # slice polytope along the value and add sliced polytope to list of polytopes in memory
                        sliced_poly = slice(poly, child.key, fval, slice_axis_idx)
                        sliced_polys.append(sliced_poly)
                # decide if axis should be compressed or not according to polytope
                axis_compressed = _axes_compressed().get(child.key, False)
                # if it's not compressed, need to separate into different nodes to append to the tree
                if not axis_compressed and len(found_vals) > 1:
                    # TODO: if we have gone through all children, then can remove poly from list completely
                    # polytopes.remove(poly)
                    for i, found_val in enumerate(found_vals):
                        # TODO: before removing polytope here actually, we should be careful that all the values in the polytope are on this branch... so we can't just remove here in theory
                        # child_polytopes = deepcopy(polytopes)
                        child_polytopes = [p for p in polytopes if p != poly]
                        if sliced_polys[i]:
                            child_polytopes.append(sliced_polys[i])
                        children = _slice(child, child_polytopes, datacube_axes, datacube_transformations)
                        # If this node used to have children but now has none due to filtering, skip it.
                        if child.children and not children:
                            continue
                        # TODO: add the child_polytopes to the child.metadata/ ie change child.metadata here before passing?
                        if isinstance(found_val, pd.Timedelta) or isinstance(found_val, pd.Timestamp):
                            found_val = [str(found_val)]

                        # TODO: when we have an axis that we would like to merge with another, we should skip the node creation here
                        # and instead keep/cache the value to merge with the node from before??

                        print("HERE LOOK")
                        print(child.key)
                        print(found_val)
                        # print(children)
                        qube_node = Qube.make(key=child.key,
                                              values=QEnum(found_val),
                                              metadata=child.metadata,
                                              children=children)
                        result.append(qube_node)
                else:
                    # if it's compressed, then can add all found values in a single node
                    # polytopes.remove(poly)
                    # child_polytopes = deepcopy(polytopes)
                    child_polytopes = [p for p in polytopes if p != poly]
                    child_polytopes.extend([sliced_poly_ for sliced_poly_ in sliced_polys if sliced_poly_ is not None])
                    # create children
                    children = _slice(child, child_polytopes, datacube_axes, datacube_transformations)
                    # If this node used to have children but now has none due to filtering, skip it.
                    if child.children and not children:
                        continue

                    new_found_vals = []
                    for found_val in found_vals:
                        if isinstance(found_val, pd.Timedelta) or isinstance(found_val, pd.Timestamp):
                            print("DIDNT WE GO HERE?")
                            print(found_val)
                            print(str(found_val))
                            # found_val = [str(found_val)]
                            new_found_vals.append(str(found_val))
                        else:
                            new_found_vals.append(found_val)

                    print("WHAT ABOUT HERE?")
                    print(found_vals)
                    print(new_found_vals)
                    # TODO: add the child_polytopes to the child.metadata/ ie change child.metadata here before passing
                    result.extend([Qube.make(
                        key=child.key,
                        values=QEnum(new_found_vals),
                        metadata=child.metadata,
                        children=children
                    )])

        return result

    # change the polytope point types here
    for polytope in polytopes_to_slice:
        for axis in polytope._axes:
            change_poly_axis_type(axis, [polytope], datacube_axes)

    return Qube.root_node(_slice(q, polytopes_to_slice, datacube_axes, datacube_transformations))


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
