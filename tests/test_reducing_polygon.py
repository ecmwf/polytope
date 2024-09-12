import geopandas as gpd
from shapely.geometry import shape

from polytope.shapes import Polygon


class TestReducedPolygonShape:
    def setup_method(self, method):
        pass

    def test_reduced_polygon_shape(self):

        # Generate 200 + random points

        shapefile = gpd.read_file("~/Downloads/World_Seas_IHO_v3/World_Seas_IHO_v3.shp")
        print(shapefile)
        polygons = []
        mediterranean_seas = ["Ionian Sea"]
        for i in range(100):
            country = shapefile.iloc[i]
            if country["NAME"] in mediterranean_seas:
                print(country["NAME"])
                multi_polygon = shape(country["geometry"])
                if multi_polygon.geom_type == "MultiPolygon":
                    true_polygons = list(multi_polygon.geoms)
                    for true_polygon in true_polygons:
                        polygons.append(true_polygon)
                else:
                    polygons.append(multi_polygon)
        polygons_list = []

        for polygon in polygons:
            xx, yy = polygon.exterior.coords.xy
            polygon_points = [list(a) for a in zip(xx, yy)]
            polygons_list.append(polygon_points)

        points = polygons_list[0]
        print(len(points))


        # Now create a list of x,y points for each polygon

        for polygon in polygons:
            xx, yy = polygon.exterior.coords.xy
            polygon_points = [list(a) for a in zip(xx, yy)]
            polygons_list.append(polygon_points)

        import time
        time1 = time.time()
        poly = Polygon(["lat", "lon"], points)
        print("Time taken")
        print(time.time() - time1)

        print(len(poly._points))
        print(len(points))

        assert len(poly._points) < len(points)

        import matplotlib.pyplot as plt

        plt.plot(*polygons[0].exterior.xy)

        reduced_poly_xs = [point[0] for point in poly._points]
        reduced_poly_ys = [point[1] for point in poly._points]

        plt.plot(reduced_poly_xs, reduced_poly_ys, color="red")

        plt.show()
