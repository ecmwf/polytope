from ..datacube.index_tree import IndexTree
from ..datacube.quad_tree import QuadTree
from .engine import Engine


class QuadTreeSlicer(Engine):
    def __init__(self, points):
        # here need to construct quadtree, which is specific to datacube
        # NOTE: should this be inside of the datacube instead that we create the quadtree?
        quad_tree = QuadTree()
        quad_tree.build_point_tree(points)
        self.quad_tree = quad_tree

    # method to slice polygon against quadtree
    def extract(self, datacube, polytopes):
        # need to find the points to extract within the polytopes (polygons here in 2D)
        request = IndexTree()
        extracted_points = []
        for polytope in polytopes:
            assert len(polytope._axes) == 2
            extracted_points.extend(self.extract_single(datacube, polytope))

        # what data format do we return extracted points as? Append those points to the index tree?
        for point in extracted_points:
            # append each found leaf to the tree
            lat = point.rect[0]
            lon = point.rect[1]
            result = point.item
            # TODO: make finding the axes objects nicer?
            lat_axis = datacube.axes[polytope._axes[0]]
            lat_child = request.create_child(lat_axis, lat)
            lon_axis = datacube.axes[polytope._axes[1]]
            lon_child = lat_child.create_child(lon_axis, lon)
            lon_child.result = result
        return request

    def extract_single(self, datacube, polytope):
        # extract a single polygon

        # need to find points of the datacube contained within the polytope
        # We do this by intersecting the datacube point cloud quad tree with the polytope here
        polygon_points = self.quad_tree.query_polygon(polytope)
        return polygon_points
