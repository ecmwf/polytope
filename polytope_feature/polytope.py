import logging
from typing import List

from .datacube.backends.datacube import Datacube
from .datacube.datacube_axis import UnsliceableDatacubeAxis
from .datacube.tensor_index_tree import TensorIndexTree
from .datacube.tree_rows import RowMerger
from .engine.hullslicer import HullSlicer
from .engine.nearest_grid import batches_point
from .engine.optimised_point_in_polygon_slicer import OptimisedPointInPolygonSlicer
from .engine.optimised_quadtree_slicer import OptimisedQuadTreeSlicer
from .engine.point_in_polygon_slicer import PointInPolygonSlicer
from .engine.quadtree_slicer import QuadTreeSlicer
from .options import PolytopeOptions
from .shapes import ConvexPolytope, Point, Product, Union
from .utility.combinatorics import group, tensor_product
from .utility.exceptions import AxisOverdefinedError
from .utility.list_tools import unique


class Request:
    """Encapsulates a request for data"""

    def __init__(self, *shapes):
        self.shapes = list(shapes)
        self.check_axes()

    def check_axes(self):
        """Check that all axes are defined by the combination of shapes, and that they are defined only once"""
        defined_axes = []

        for shape in self.shapes:
            for axis in shape.axes():
                if axis not in defined_axes:
                    defined_axes.append(axis)
                else:
                    raise AxisOverdefinedError(axis)

    def polytopes(self):
        """Returns the representation of the request as polytopes"""
        polytopes = []
        for shape in self.shapes:
            polytopes.extend(shape.polytope())
        return polytopes

    def __repr__(self):
        return_str = ""
        for shape in self.shapes:
            return_str += shape.__repr__() + "\n"
        return return_str


class Polytope:
    def __init__(
        self,
        datacube,
        options=None,
        context=None,
    ):
        from .datacube import Datacube

        if options is None:
            options = {}

        self.compressed_axes = []
        self.context = context

        (
            axis_options,
            compressed_axes_options,
            config,
            alternative_axes,
            use_catalogue,
            engine_options,
        ) = PolytopeOptions.get_polytope_options(options)
        self.datacube = Datacube.create(
            datacube,
            config,
            axis_options,
            compressed_axes_options,
            alternative_axes,
            use_catalogue,
            self.context,
        )
        if engine_options == {}:
            for ax_name in self.datacube._axes.keys():
                engine_options[ax_name] = "hullslicer"
        self.engine_options = engine_options
        self.engines = self.create_engines()
        self.ax_is_unsliceable = {}

    def create_engines(self):
        engines = {}
        engine_types = set(self.engine_options.values())
        if "quadtree" in engine_types:
            # TODO: need to get the corresponding point cloud from the datacube
            quadtree_points = self.datacube.find_point_cloud()
            engines["quadtree"] = QuadTreeSlicer(quadtree_points)
        if "optimised_quadtree" in engine_types:
            # TODO: need to get the corresponding point cloud from the datacube
            quadtree_points = self.datacube.find_point_cloud()
            engines["optimised_quadtree"] = OptimisedQuadTreeSlicer(quadtree_points)
        if "hullslicer" in engine_types:
            engines["hullslicer"] = HullSlicer()
        if "point_in_polygon" in engine_types:
            points = self.datacube.find_point_cloud()
            engines["point_in_polygon"] = PointInPolygonSlicer(points)
        if "optimised_point_in_polygon" in engine_types:
            points = self.datacube.find_point_cloud()
            engines["optimised_point_in_polygon"] = OptimisedPointInPolygonSlicer(points)
        return engines

    def _unique_continuous_points(self, p: ConvexPolytope, datacube: Datacube):
        for i, ax in enumerate(p._axes):
            mapper = datacube.get_mapper(ax)
            if self.ax_is_unsliceable.get(ax, None) is None:
                self.ax_is_unsliceable[ax] = isinstance(mapper, UnsliceableDatacubeAxis)
            if self.ax_is_unsliceable[ax]:
                break
            for j, val in enumerate(p.points):
                p.points[j][i] = mapper.to_float(mapper.parse(p.points[j][i]))
        # Remove duplicate points
        unique(p.points)

    def slice(self, datacube, polytopes: List[ConvexPolytope]):
        """Low-level API which takes a polytope geometry object and uses it to slice the datacube"""

        for engine in set(self.engines.values()):
            engine.reset()

        self.find_compressed_axes(datacube, polytopes)
        # the last datacube axis holds the tree leaves (e.g. longitude); the slicer stores those as numpy arrays
        self.leaf_axis_name = next(reversed(datacube.axes.keys()))

        merge_rows = self._compress_union_rows(datacube, polytopes)
        # Leaves of merged union rows keep their values in ascending order instead of grid-index order
        # (see tree_rows.RowMerger); the batched nearest search builds its node in the same order.
        self.merge_leaf_rows = merge_rows

        # Convert the polytope points to float type to support triangulation and interpolation
        for p in polytopes:
            if isinstance(p, Product):
                for poly in p.polytope():
                    self._unique_continuous_points(poly, datacube)
            else:
                self._unique_continuous_points(p, datacube)

        groups, input_axes = group(polytopes)
        datacube.validate(input_axes)
        request = TensorIndexTree()
        row_merger = RowMerger(self.leaf_axis_name) if merge_rows else None

        axes = list(datacube.axes.values())
        engines = [self.find_engine(ax) for ax in axes]
        engine_of_axis = dict(zip(datacube.axes.keys(), engines))

        batching = {}

        def batches(polytope):
            """Whether an engine resolves this polytope together with the others on its axes.

            Answered once per polytope: a request of N points asks it for the same handful of Selects N
            times over, once per combination.
            """
            answer = batching.get(id(polytope))
            if answer is None:
                answer = batching[id(polytope)] = any(
                    engine.batches_polytope(polytope, datacube, self)
                    for engine in (engine_of_axis.get(name) for name in polytope.axes())
                    if engine is not None
                )
            return answer

        for shared, batched in self._group_combinations(tensor_product(groups), batches):
            r = TensorIndexTree()
            r["unsliced_polytopes"] = set(shared)
            current_nodes = [r]
            for ax, engine in zip(axes, engines):
                # The prefix is shared by every grouped combination, so hand all of their polytopes on this
                # axis to the engine at once, in request order (Engine.batched).
                engine.batched = on_axis = [p for p in batched if ax.name in p.axes()]
                if on_axis:
                    for node in current_nodes:
                        node["unsliced_polytopes"] = node["unsliced_polytopes"] | set(on_axis)
                next_nodes = []
                for node in current_nodes:
                    engine._build_branch(ax, node, datacube, next_nodes, self)
                current_nodes = next_nodes

            if row_merger is None:
                request.merge(r)
            else:
                row_merger.merge(request, r)
        if row_merger is not None:
            row_merger.finalise(request)
        return request

    # Off by default: the legacy CovJSON step encoder (covjsonkit ``walk_tree_step``, used for climate-dt polygons)
    # reads one point per leaf.  Set to True on an instance (or the class) to get one leaf per row for polygons/paths.
    _merge_union_rows = False

    def _compress_union_rows(self, datacube, polytopes):
        """Apply ``remove_compressed_axis_in_union`` unless the union's rows can be merged instead.

        A union of non-orthogonal shapes (the convex pieces of a polygon, the segments of a path) otherwise leaves
        the leaf axis uncompressed, i.e. one tree node per point.  When the leaf axis holds array leaves it stays
        compressed and the pieces' leaves are merged row by row (see ``tree_rows.RowMerger``), which gives the
        merged leaf per-point tags where its pieces are tagged differently.  Returns whether rows must be merged.
        """
        before = list(self.compressed_axes)
        self.remove_compressed_axis_in_union(polytopes)
        leaf = self.leaf_axis_name
        if not self._merge_union_rows or leaf not in before or leaf in self.compressed_axes:
            return False
        if self.engine_options.get(leaf) != "hullslicer":
            return False
        if not HullSlicer.is_array_leaf_axis(datacube.axes[leaf], self):
            return False
        self.compressed_axes = before
        return True

    @staticmethod
    def _flatten_combination(combination):
        polys = []
        for combi in combination:
            for poly in combi if isinstance(combi, list) else [combi]:
                if isinstance(poly, Product):
                    polys.extend(poly.polytope())
                else:
                    polys.append(poly)
        return polys

    @classmethod
    def _group_combinations(cls, combinations, batches_polytope):
        """Yield (shared_polytopes, batched_polytopes) per distinct tree prefix.

        Polytopes an engine batches (see Engine.batches_polytope) are split off; combinations whose
        remaining polytopes are identical (eg. every Point of a Union shares the same Selects) then only
        need their prefix built once.  The batched polytopes keep the order of the request, which is the
        order the engine resolving them reports its result in.
        """
        grouped = {}
        for c in combinations:
            shared, batched = [], {}
            for poly in cls._flatten_combination(c):
                if batches_polytope(poly):
                    batched[poly] = None
                else:
                    shared.append(poly)
            key = frozenset(shared) if batched else object()
            entry = grouped.setdefault(key, (shared, {}))
            entry[1].update(batched)
        return [(shared, list(batched)) for shared, batched in grouped.values()]

    def find_engine(self, ax):
        if ax.name not in self.engine_options:
            raise ValueError(f"No engine specified for axis {ax.name}")
        slicer_type = self.engine_options[ax.name]
        return self.engines[slicer_type]

    def switch_polytope_dim(self, request):
        """Keep a ``Point`` two-dimensional where the engine of its axes resolves both coordinates at once.

        That is the quadtree slicer on any point, and the hullslicer on a nearest point of a structured
        grid, which it resolves with every other nearest point of the request
        (:mod:`polytope_feature.engine.nearest_grid`).  Otherwise a point is decomposed into one
        1-D polytope per axis, which the engine then slices one axis at a time.
        """
        joint_axes = {ax for ax, slicer in self.engine_options.items() if slicer == "quadtree"}

        def resolved_jointly(shape):
            if not isinstance(shape, Point):
                return False
            if joint_axes.intersection(shape.axes()):
                return True
            return batches_point(shape, self.datacube, self)

        for shp in request.shapes:
            for shape in shp._shapes if isinstance(shp, Union) else [shp]:
                if resolved_jointly(shape):
                    shape.decompose_1D = False

    def retrieve(self, request: Request, method="standard"):
        """Higher-level API which takes a request and uses it to slice the datacube"""
        logging.info("Starting request for %s ", self.context)
        self.datacube.check_branching_axes(request)
        self.switch_polytope_dim(request)
        self.datacube.nearest_search = {}
        for polytope in request.polytopes():
            if polytope.method == "nearest":
                # Register the query point(s) with the tag of the polytope they come from, so the
                # backend can attach the right tag to each nearest point once it is resolved.
                query_points = polytope.values if polytope.is_flat else polytope.points
                points, _, tags = self.datacube.nearest_search.setdefault(tuple(polytope.axes()), ([], polytope.k, []))
                points.extend(list(pt) for pt in query_points)
                tags.extend([polytope.tag] * len(query_points))
        request_tree = self.slice(self.datacube, request.polytopes())
        logging.info("Created request tree for %s ", self.context)
        self.datacube.get(request_tree, self.context)
        logging.info("Retrieved data for %s ", self.context)
        return request_tree

    def find_compressed_axes(self, datacube, polytopes):
        # First determine compressable axes from input polytopes
        compressable_axes = []
        for polytope in polytopes:
            if polytope.is_orthogonal:
                for ax in polytope.axes():
                    compressable_axes.append(ax)
        # Cross check this list with list of compressable axis from datacube
        # (should not include any merged or coupled axes)
        for compressed_axis in compressable_axes:
            if compressed_axis in datacube.compressed_axes:
                self.compressed_axes.append(compressed_axis)

        k, last_value = _, datacube.axes[k] = datacube.axes.popitem()
        self.compressed_axes.append(k)

    def remove_compressed_axis_in_union(self, polytopes):
        """Drop one entry of the last compressed axis per union polytope defined on it.

        ``find_compressed_axes`` appends the axis once per orthogonal polytope that defines it, so a union
        of N orthogonal shapes (the points of a timeseries) leaves the leaf axis compressed while a union
        of N non-orthogonal pieces (a polygon's triangles, which are not compressable) uncompresses it.
        That is what decides whether a request's leaf values are one array per row or one node per point,
        so the count of the entries matters, not just which axes are there.
        """
        if len(self.compressed_axes) == 0:
            return
        last = self.compressed_axes[-1]
        removals = sum(1 for p in polytopes if p.is_in_union and last in p.axes())
        if removals == 0:
            return
        if removals < self.compressed_axes.count(last):
            # The axis survives every removal, so it stays the last one and each removal takes an earlier
            # entry: drop the first ``removals`` of them in one pass instead of one O(n) list removal per
            # polytope (which costs 15 s for the 100 000 points of a timeseries request).
            kept = []
            for axis in self.compressed_axes:
                if removals and axis == last:
                    removals -= 1
                    continue
                kept.append(axis)
            self.compressed_axes = kept
            return
        # The last axis runs out mid-way and the one before it takes over, so replay the removals in order.
        for p in polytopes:
            if p.is_in_union:
                for axis in p.axes():
                    if axis in self.compressed_axes:
                        if axis == self.compressed_axes[-1]:
                            self.compressed_axes.remove(axis)
