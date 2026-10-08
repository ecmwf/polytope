import logging

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
        self.points_array = np.asarray(points, dtype=np.float64).reshape(-1, 2)

    # All lat/lon polytopes of a node are resolved together into a single bulk leaf.
    batches_polytopes = True

    def _query_points(self, polytope):
        revert_axes = list(polytope.axes()) != ["latitude", "longitude"]
        return [tuple(reversed(pt)) if revert_axes else tuple(pt) for pt in polytope.points]

    def extract_single(self, datacube, polytope):
        """Return the point-cloud indexes selected by one polytope."""
        axes = polytope.axes()
        assert len(axes) == 2
        assert "latitude" in axes and "longitude" in axes
        if polytope.method == "nearest":
            # Each nearest polytope carries its own query point(s) and k, so it can be
            # resolved on its own: this keeps the result (and tag) tied to the request.
            idxs = []
            for query in self._query_points(polytope):
                if use_rust:
                    idxs.extend(self.quad_tree.k_nearest_neighbor(query, polytope.k) or [])
                else:
                    idxs.extend(self._python_knn(query, polytope.k))
            return idxs
        if use_rust:
            return self.quad_tree.query_polygon(self.points, 0, self._query_points(polytope))
        if list(axes) != ["latitude", "longitude"]:
            polytope.points = self._query_points(polytope)
        return [node.index for node in self.quad_tree.query_polygon(polytope)]

    def _python_knn(self, query, k):
        dists = np.sum((self.points_array - np.asarray(query)) ** 2, axis=1)
        k = min(k, len(dists))
        nearest = np.argpartition(dists, k - 1)[:k]
        return nearest[np.argsort(dists[nearest])].tolist()

    def _sub_polytopes(self, polytope, datacube):
        # A polygon crossing the cyclic longitude seam is split into canonical pieces
        # before querying the point cloud. Nearest queries work on points directly.
        lon_ax = datacube._axes["longitude"]
        if lon_ax.is_cyclic and polytope.method != "nearest":
            for t in lon_ax.transformations:
                if isinstance(t, DatacubeAxisCyclic):
                    return t.split_polytope_at_boundary(polytope, "longitude", lon_ax)
        return [polytope]

    def _build_branch(self, ax, node, datacube, next_nodes, api):
        # Resolve every lat/lon polytope on this node in one pass, recording which
        # polytope tags select each point.
        point_tags = {}
        for polytope in node["unsliced_polytopes"]:
            if ax.name not in polytope.axes():
                continue
            for sub_poly in self._sub_polytopes(polytope, datacube):
                for idx in self.extract_single(datacube, sub_poly):
                    tags = point_tags.setdefault(int(idx), set())
                    if polytope.tag is not None:
                        tags.add(polytope.tag)
        del node["unsliced_polytopes"]

        if len(point_tags) == 0:
            node.remove_branch()
            return

        indexes = np.fromiter(point_tags.keys(), dtype=np.int64, count=len(point_tags))
        coordinates = self.points_array[indexes]
        # Sort by (lat, lon) to match the legacy per-point leaf order while retaining the
        # canonical backend index needed for range planning.
        order = np.lexsort((coordinates[:, 1], coordinates[:, 0]))
        tags = [point_tags[int(i)] for i in indexes[order]]
        lon_ax = datacube._axes["longitude"]
        if getattr(datacube, "bulk_grid_leaves", False):
            # One array-backed leaf for the whole selection.
            node.create_bulk_merged_child([ax, lon_ax], coordinates[order], indexes[order], [], point_tags=tags)
            return
        # One leaf per point, as the tree looked before bulk leaves existed.
        for (lat_val, lon_val), index, point_tags_of_point in zip(coordinates[order], indexes[order], tags):
            child, _ = node.create_merged_child([ax, lon_ax], (float(lat_val), float(lon_val)), [])
            # NOTE: the index of the point is stashed in the branches' result
            child.indexes = [int(index)]
            child.tags.update(point_tags_of_point)
