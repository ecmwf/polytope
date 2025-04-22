from qubed import Qube
from qubed.value_types import QEnum
from qubed.set_operations import union
from ...engine.hullslicer import slice
import pandas as pd
from ..datacube_axis import UnsliceableDatacubeAxis
from ..transformations.datacube_mappers.datacube_mappers import DatacubeMapper
from ...shapes import ConvexPolytope, Product
from ...utility.combinatorics import group, tensor_product


def _actual_slice(q: Qube, polytopes_to_slice, datacube_axes, datacube_transformations) -> 'Qube':

    def find_polytopes_on_axis(axis_name, polytopes):
        polytopes_on_axis = []
        for poly in polytopes:
            if axis_name in poly._axes:
                polytopes_on_axis.append(poly)
        return polytopes_on_axis

    def change_poly_axis_type(axis_name, polytopes, datacube_axes):
        axis = datacube_axes[axis_name]
        # loop through the polytopes and change each polytopes's values according to axis
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

    def _slice_second_grid_axis(axis_name, polytopes, datacube_axes, datacube_transformations, second_axis_vals) -> list[Qube]:
        result = []
        polytopes_on_axis = find_polytopes_on_axis(axis_name, polytopes)

        for poly in polytopes_on_axis:
            lower, upper, slice_axis_idx = poly.extents(axis_name)

            new_lower, new_upper = transform_upper_lower(axis_name, lower, upper, datacube_axes)
            found_vals = [v for v in second_axis_vals if new_lower <= v <= new_upper]

            if len(found_vals) == 0:
                continue

            # slice polytope along each value on child and keep resulting polytopes in memory
            sliced_polys = []
            for val in found_vals:
                ax = datacube_axes[axis_name]
                if not isinstance(ax, UnsliceableDatacubeAxis):
                    fval = ax.to_float(val)
                    # slice polytope along the value and add sliced polytope to list of polytopes in memory
                    sliced_poly = slice(poly, axis_name, fval, slice_axis_idx)
                    sliced_polys.append(sliced_poly)
            # decide if axis should be compressed or not according to polytope
            # NOTE: actually the second grid axis will always be compressed

            # if it's not compressed, need to separate into different nodes to append to the tree

            new_found_vals = []
            for found_val in found_vals:
                if isinstance(found_val, pd.Timedelta) or isinstance(found_val, pd.Timestamp):
                    new_found_vals.append(str(found_val))
                else:
                    new_found_vals.append(found_val)

            # NOTE this was the last axis so we do not have children...

            result.extend([Qube.make(
                key=axis_name,
                values=QEnum(new_found_vals),
                metadata={},
                children={}
            )])
        return result

    def _slice(q: Qube, polytopes, datacube_axes, datacube_transformations) -> list[Qube]:
        result = []

        if len(q.children) == 0:
            # add "fake" axes and their nodes in order -> what about merged axes??
            mapper_transformation = None
            for transformation in list(datacube_transformations.values()):
                if isinstance(transformation, DatacubeMapper):
                    mapper_transformation = transformation
            if not mapper_transformation:
                # There is no grid mapping
                pass
            else:
                # Slice on the two grid axes
                grid_axes = mapper_transformation._mapped_axes

                # Handle first grid axis
                polytopes_on_axis = find_polytopes_on_axis(grid_axes[0], polytopes)

                for poly in polytopes_on_axis:
                    lower, upper, slice_axis_idx = poly.extents(grid_axes[0])

                    first_ax_vals = mapper_transformation.first_axis_vals()

                    new_lower, new_upper = transform_upper_lower(grid_axes[0], lower, upper, datacube_axes)
                    found_vals = [v for v in first_ax_vals if new_lower <= v <= new_upper]

                    if len(found_vals) == 0:
                        continue

                    # slice polytope along each value on child and keep resulting polytopes in memory
                    sliced_polys = []
                    for val in found_vals:
                        ax = datacube_axes[grid_axes[0]]
                        if not isinstance(ax, UnsliceableDatacubeAxis):
                            fval = ax.to_float(val)
                            # slice polytope along the value and add sliced polytope to list of polytopes in memory
                            sliced_poly = slice(poly, grid_axes[0], fval, slice_axis_idx)
                            sliced_polys.append(sliced_poly)
                    # decide if axis should be compressed or not according to polytope
                    # NOTE: actually the first grid axis will never be compressed
                    axis_compressed = _axes_compressed().get(grid_axes[0], False)

                    # if it's not compressed, need to separate into different nodes to append to the tree
                    for i, found_val in enumerate(found_vals):
                        child_polytopes = [p for p in polytopes if p != poly]
                        if sliced_polys[i]:
                            child_polytopes.append(sliced_polys[i])

                        second_axis_vals = mapper_transformation.second_axis_vals([found_val])

                        # get second axis children through slicing
                        children = _slice_second_grid_axis(
                            grid_axes[1], child_polytopes, datacube_axes, datacube_transformations, second_axis_vals)
                        # If this node used to have children but now has none due to filtering, skip it.
                        if not children:
                            continue
                        if isinstance(found_val, pd.Timedelta) or isinstance(found_val, pd.Timestamp):
                            found_val = [str(found_val)]

                        # TODO: when we have an axis that we would like to merge with another, we should skip the node creation here
                        # and instead keep/cache the value to merge with the node from before??

                        qube_node = Qube.make(key=grid_axes[0],
                                              values=QEnum([found_val]),
                                              metadata={},
                                              children=children)
                        result.append(qube_node)

        for i, child in enumerate(q.children):
            # find polytopes which are defined on axis child.key
            polytopes_on_axis = find_polytopes_on_axis(child.key, polytopes)

            # here now first change the values in the polytopes on the axis to reflect the axis type

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
                    for i, found_val in enumerate(found_vals):
                        child_polytopes = [p for p in polytopes if p != poly]
                        if sliced_polys[i]:
                            child_polytopes.append(sliced_polys[i])
                        children = _slice(child, child_polytopes, datacube_axes, datacube_transformations)
                        # If this node used to have children but now has none due to filtering, skip it.
                        if child.children and not children:
                            continue
                        if isinstance(found_val, pd.Timedelta) or isinstance(found_val, pd.Timestamp):
                            found_val = [str(found_val)]

                        # TODO: when we have an axis that we would like to merge with another, we should skip the node creation here
                        # and instead keep/cache the value to merge with the node from before??

                        qube_node = Qube.make(key=child.key,
                                              values=QEnum(found_val),
                                              metadata=child.metadata,
                                              children=children)
                        result.append(qube_node)
                else:
                    # if it's compressed, then can add all found values in a single node
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
                            new_found_vals.append(str(found_val))
                        else:
                            new_found_vals.append(found_val)

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


def actual_slice(q: Qube, polytopes_to_slice, datacube_axes, datacube_transformations):
    # for p in polytopes_to_slice:
    # if isinstance(p, Product):
    #     for poly in p.polytope():
    #         self._unique_continuous_points(poly, datacube)
    # else:
    #     self._unique_continuous_points(p, datacube)

    groups, input_axes = group(polytopes_to_slice)
    # datacube.validate(input_axes)
    # request = TensorIndexTree()
    combinations = tensor_product(groups)

    sub_trees = []

    # NOTE: could optimise here if we know combinations will always be for one request.
    # Then we do not need to create a new index tree and merge it to request, but can just
    # directly work on request and return it...

    for c in combinations:
        # r = TensorIndexTree()
        new_c = []
        for combi in c:
            if isinstance(combi, list):
                new_c.extend(combi)
            else:
                new_c.append(combi)
        # NOTE TODO: here some of the polys in new_c can be a Product shape instead of a ConvexPolytope
        # -> need to go through the polytopes in new_c and replace the Products with their sub-ConvexPolytopes
        final_polys = []
        for poly in new_c:
            if isinstance(poly, Product):
                final_polys.extend(poly.polytope())
            else:
                final_polys.append(poly)

        # Get the sliced Qube for each combi
        r = _actual_slice(q, final_polys, datacube_axes, datacube_transformations)
        sub_trees.append(r)

    final_tree = sub_trees[0]

    for sub_tree in sub_trees[1:]:
        union(final_tree, sub_tree)
    return final_tree
