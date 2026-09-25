import logging
import os

import numpy as np

from ..datacube.transformations.datacube_cyclic.datacube_cyclic import (
    DatacubeAxisCyclic,
)
from .engine import Engine

use_rust = False
try:
    from polytope_feature.polytope_rs import QuadTree

    use_rust = True
except (ModuleNotFoundError, ImportError) as e:
    print(f"Failed to load Rust extension with error: {e}, falling back to Python implementation.")
    from ..datacube.quadtree.quad_tree import QuadTree


class QuadTreeSlicer(Engine):
    def __init__(self, points):
        # here need to construct quadtree, which is specific to datacube
        # NOTE: should this be inside of the datacube instead that we create the quadtree?
        # TODO: maybe we create the quadtree as soon as we have an unstructured slicer type and return it
        # to the slicer somehow?
        quad_tree = QuadTree()
        # NOTE: the points here are assumed to be lat/lon implicitly
        points = [tuple(point) for point in points]
        logging.debug("Creating point cloud quadtree...")
        quad_tree.build_point_tree(points)
        logging.debug("Created point cloud quadtree")
        self.points = points
        self.quad_tree = quad_tree
        self.bulk_spatial = os.environ.get("POLYTOPE_BULK_SPATIAL") == "1"
        self.bulk_nearest_once = os.environ.get("POLYTOPE_BULK_NEAREST_ONCE") == "1"
        self.points_array = np.asarray(points) if self.bulk_spatial else None
        self.bulk_nearest_paths = set()

    def reset_bulk_state(self):
        self.bulk_nearest_paths.clear()

    def extract_single(self, datacube, polytope):
        # extract a single polygon
        # if need to find nearest points, then take alternative slicing method using quadtree to find nearest point
        axes = polytope.axes()
        assert len(axes) == 2
        assert "latitude" in axes and "longitude" in axes
        revert_axes = not (list(axes) == ["latitude", "longitude"])
        if use_rust:
            logging.debug("Using Rust for quadtree polygon query")
            if len(datacube.nearest_search) == 0:
                if revert_axes:
                    polytope_points = [tuple(reversed(point)) for point in polytope.points]
                else:
                    polytope_points = [tuple(point) for point in polytope.points]
                logging.debug("Querying quadtree")
                polygon_points = self.quad_tree.query_polygon(self.points, 0, polytope_points)
                logging.debug("Finished querying quadtree")
            else:
                k = datacube.nearest_search[tuple(polytope.axes())][1]
                if revert_axes:
                    nn_points = [tuple(reversed(pt)) for pt in datacube.nearest_search[tuple(polytope.axes())][0]]
                else:
                    nn_points = [tuple(pt) for pt in datacube.nearest_search[tuple(polytope.axes())][0]]
                polygon_points = []
                for nn_pt in nn_points:
                    polygon_points.extend(self.quad_tree.k_nearest_neighbor(nn_pt, k))
        else:
            if revert_axes:
                polytope.points = [tuple(reversed(point)) for point in polytope.points]
            polygon_points = self.quad_tree.query_polygon(polytope)
        return polygon_points

    def _build_branch(self, ax, node, datacube, next_nodes, api):
        if len(datacube.nearest_search) == 0:
            for polytope in node["unsliced_polytopes"]:
                if ax.name in polytope._axes:
                    self._build_sliceable_child(polytope, ax, node, datacube, next_nodes, api)
            del node["unsliced_polytopes"]
        else:
            if self.bulk_spatial and self.bulk_nearest_once:
                path_key = tuple(node.flatten().items())
                if path_key in self.bulk_nearest_paths:
                    node.remove_branch()
                    return
                self.bulk_nearest_paths.add(path_key)
            self._build_sliceable_child(node["unsliced_polytopes"].pop(), ax, node, datacube, next_nodes, api)

    def _build_sliceable_child(self, polytope, ax, node, datacube, next_nodes, api):
        lon_ax = datacube._axes["longitude"]

        # When the longitude axis is cyclic and the request polygon crosses the seam,
        # split it into canonical sub-polytopes before querying the point cloud.
        sub_polytopes = [polytope]
        if lon_ax.is_cyclic and len(datacube.nearest_search) == 0:
            for t in lon_ax.transformations:
                if isinstance(t, DatacubeAxisCyclic):
                    sub_polytopes = t.split_polytope_at_boundary(polytope, "longitude", lon_ax)
                    break

        # Query each sub-polytope and deduplicate by point-cloud index.
        extracted_points = []
        seen = set()
        for sub_poly in sub_polytopes:
            for value in self.extract_single(datacube, sub_poly):
                idx = value if use_rust else value.index
                if idx not in seen:
                    seen.add(idx)
                    extracted_points.append(idx if use_rust else value)

        if len(extracted_points) == 0:
            node.remove_branch()
            return

        lat_ax = ax
        if self.bulk_spatial and use_rust:
            assert self.points_array is not None
            indexes = np.asarray(extracted_points, dtype=np.int64)
            coordinates = self.points_array[indexes]
            # Match SortedList's existing coordinate order while retaining the
            # canonical backend index needed for range planning.
            output_order = np.lexsort((coordinates[:, 1], coordinates[:, 0]))
            node.create_bulk_merged_child([lat_ax, lon_ax], coordinates[output_order], indexes[output_order], [])
            return

        for value in extracted_points:
            # convert to float for slicing
            if use_rust:
                lat_val = self.points[value][0]
                lon_val = self.points[value][1]
            else:
                lat_val = value.item[0]
                lon_val = value.item[1]
            # store the native type
            grand_child, _ = node.create_merged_child([lat_ax, lon_ax], (lat_val, lon_val), [])
            # NOTE: the index of the point is stashed in the branches' result
            if use_rust:
                grand_child.indexes = [value]
            else:
                grand_child.indexes = [value.index]
            # grand_child["unsliced_polytopes"] = copy(node["unsliced_polytopes"])
            # grand_child["unsliced_polytopes"].remove(polytope)
