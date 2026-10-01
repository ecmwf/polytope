import logging

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

    def extract_single(self, datacube, polytope):
        # extract a single polygon
        # if need to find nearest points, then take alternative slicing method using quadtree to find nearest point
        axes = polytope.axes()
        assert len(axes) == 2
        assert "latitude" in axes and "longitude" in axes
        revert_axes = not (list(axes) == ["latitude", "longitude"])
        if use_rust:
            if polytope.method == "nearest":
                logging.debug("Using Rust for quadtree k-nearest-neighbor query")
                k = polytope.k
                if revert_axes:
                    nn_points = [tuple(reversed(point)) for point in polytope.points]
                else:
                    nn_points = [tuple(point) for point in polytope.points]
                polygon_points = []
                for nn_pt in nn_points:
                    result = self.quad_tree.k_nearest_neighbor(nn_pt, k)
                    if result:
                        polygon_points.extend(result)
            else:
                logging.debug("Using Rust for quadtree polygon query")
                if revert_axes:
                    polytope_points = [tuple(reversed(point)) for point in polytope.points]
                else:
                    polytope_points = [tuple(point) for point in polytope.points]
                logging.debug("Querying quadtree")
                polygon_points = self.quad_tree.query_polygon(self.points, 0, polytope_points)
                logging.debug("Finished querying quadtree")
        else:
            if revert_axes:
                polytope.points = [tuple(reversed(point)) for point in polytope.points]
            polygon_points = self.quad_tree.query_polygon(polytope)
        return polygon_points

    def _build_branch(self, ax, node, datacube, next_nodes, api):
        # Process every polytope registered against this axis on this node
        # individually. Each polytope already carries its own query point(s),
        # method, k and tag, so there is no need to reach into the shared,
        # global `datacube.nearest_search` registry here: doing so previously
        # caused every polytope sharing the same (latitude, longitude) axes to
        # see (and get tagged with) results belonging to every other
        # registered point, whenever more than one nearest-neighbour Point
        # shape/value was requested in the same call (e.g. a Union of tagged
        # Points, or a single Point with several values).
        for polytope in list(node["unsliced_polytopes"]):
            if ax.name in polytope._axes:
                self._build_sliceable_child(polytope, ax, node, datacube, next_nodes, api)
        del node["unsliced_polytopes"]

    def _build_sliceable_child(self, polytope, ax, node, datacube, next_nodes, api):
        lon_ax = datacube._axes["longitude"]

        # When the longitude axis is cyclic and the request polygon crosses the seam,
        # split it into canonical sub-polytopes before querying the point cloud.
        # This only applies to polygon/box-style queries; nearest-neighbour queries
        # operate directly on query points and do not need seam-splitting.
        sub_polytopes = [polytope]
        if lon_ax.is_cyclic and polytope.method != "nearest":
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
                    extracted_points.append(value)

        if len(extracted_points) == 0:
            # Only remove the branch if nothing else (e.g. a sibling polytope
            # sharing this node, such as another tagged Point value) has
            # already added children here.
            if len(node.children) == 0:
                node.remove_branch()
            return

        lat_ax = ax
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
            # Stamp the tag: the polytope is fully resolved by this 2-D (lat, lon) slice,
            # so its tag (if any) belongs on the resulting leaf node.
            if polytope.tag is not None:
                grand_child.tags.add(polytope.tag)
            # grand_child["unsliced_polytopes"] = copy(node["unsliced_polytopes"])
            # grand_child["unsliced_polytopes"].remove(polytope)
