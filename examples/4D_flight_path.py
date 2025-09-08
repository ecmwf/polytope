import numpy as np
import plotly
import plotly.graph_objects as go
from earthkit import data
from PIL import Image

from polytope_feature.datacube.backends.xarray import XArrayDatacube
from polytope_feature.engine.hullslicer import HullSlicer
from polytope_feature.polytope import Polytope, Request
from polytope_feature.shapes import Box, Path, Select


class Test:
    def setup_method(self):
        ds = data.from_source("file", "./examples/data/temp_model_levels.grib")
        array = ds.to_xarray()
        array = array.isel(time=0).t
        axis_options = {"longitude": {"cyclic": [0, 360.0]}}
        self.xarraydatacube = XArrayDatacube(array)
        for dim in array.dims:
            array = array.sortby(dim)
        self.array = array
        self.slicer = HullSlicer()
        self.API = Polytope(datacube=array, engine=self.slicer, axis_options=axis_options)

    def test_slice_shipping_route(self):
        colorscale = [
            [0.0, "rgb(30, 59, 117)"],
            [0.1, "rgb(46, 68, 21)"],
            [0.2, "rgb(74, 96, 28)"],
            [0.3, "rgb(115,141,90)"],
            [0.4, "rgb(122, 126, 75)"],
            [0.6, "rgb(122, 126, 75)"],
            [0.7, "rgb(141,115,96)"],
            [0.8, "rgb(223, 197, 170)"],
            [0.9, "rgb(237,214,183)"],
            [1.0, "rgb(255, 255, 255)"],
        ]

        def sphere(size, texture):
            N_lat = int(texture.shape[0])
            N_lon = int(texture.shape[1])
            theta = np.linspace(0, 2 * np.pi, N_lat)
            phi = np.linspace(0, np.pi, N_lon)

            # Set up coordinates for points on the sphere
            x0 = size * np.outer(np.cos(theta), np.sin(phi))
            y0 = size * np.outer(np.sin(theta), np.sin(phi))
            z0 = size * np.outer(np.ones(N_lat), np.cos(phi))

            # Set up trace
            return x0, y0, z0

        texture = np.asarray(Image.open("./examples/data/earth_image.jpg")).T
        radius = 1
        x, y, z = sphere(radius, texture)
        surf = go.Surface(x=x, y=y, z=z, surfacecolor=texture, colorscale=colorscale, hoverinfo="none")
        layout = go.Layout(scene=dict(aspectratio=dict(x=1, y=1, z=1)), spikedistance=0)
        fig = go.Figure(data=[surf], layout=layout)
        fig.update_layout(scene=dict(xaxis_showspikes=False, yaxis_showspikes=False))
        data = fig._data

        # Now add the flight path as a 3D shape...

        CDG_coords = [49.0081, 2.5509]
        LGA_coords = [40.7769, 286.126 - 360]
        LHR_coords = LGA_coords

        CDG_coords.append(np.timedelta64(0000000000000, "ns"))
        LHR_coords.append(np.timedelta64(4500000000000, "ns"))
        CDG_to_LHR = np.array(LHR_coords) - np.array(CDG_coords)
        mid_point1 = list(np.array(CDG_coords) + (3 * CDG_to_LHR / 20))
        mid_point1.append(30.0)
        mid_point2 = list(np.array(CDG_coords) + (17 * CDG_to_LHR / 20))
        mid_point2.append(30.0)
        CDG_coords.append(5.0)
        LHR_coords.append(5.0)

        route_point_CDG_LHR = [CDG_coords, mid_point1, mid_point2, LHR_coords]
        route_point_CDG_LHR = route_point_CDG_LHR[::-1]
        padded_point_upper = [0.23, 0.23, np.timedelta64(1850, "s"), 1.0]
        padded_point_lower = [-0.23, -0.23, np.timedelta64(-1850, "s"), 1.0]
        initial_shape = Box(["latitude", "longitude", "step", "hybrid"], padded_point_lower, padded_point_upper)

        flight_route_polytope = Path(["latitude", "longitude", "step", "hybrid"], initial_shape, *route_point_CDG_LHR)

        request = Request(flight_route_polytope, Select("time", ["2022-12-02T12:00:00"]))
        result = self.API.retrieve(request)

        lats = []
        longs = []
        levels = []
        parameter_values = []
        for i in range(len(result.leaves)):
            cubepath = result.leaves[i].flatten()
            lat = cubepath["latitude"]
            long = cubepath["longitude"]
            level = cubepath["hybrid"]
            lats.append(lat)
            longs.append(long)
            levels.append(level)
            t_idx = result.leaves[i].result[1]
            parameter_values.append(t_idx)
        parameter_values = np.array(parameter_values)

        # Get the right points of lat/long/alt
        lats = [(lat) * np.pi / 180 for lat in lats]
        longs = [(long - 180) * np.pi / 180 for long in longs]
        alts = [level / 2 for level in levels]

        x = []
        y = []
        z = []
        for i in range(len(lats)):
            x1 = radius * np.cos(longs[i]) * np.cos(lats[i])
            y1 = radius * np.sin(longs[i]) * np.cos(lats[i])
            z1 = radius * np.sin(lats[i]) + alts[i] / 300  # the 300 here should really be the earth of the radius
            x.append(x1)
            y.append(y1)
            z.append(z1)

        # Plot it using plotly in 3D shape
        flight_path = go.Scatter3d(
            x=x, y=y, z=z, mode="markers", marker=dict(size=1.5, color=parameter_values, colorscale="YlOrRd")
        )

        data.append(flight_path)
        fig = go.Figure(data=data)
        fig.update_layout(
            title_text="Contour lines over globe<br>(Click and drag to rotate)",
            showlegend=False,
            geo=dict(
                showland=True,
                showcountries=True,
                showocean=True,
                countrywidth=0.5,
                landcolor="rgb(230, 145, 56)",
                lakecolor="rgb(0, 255, 255)",
                oceancolor="rgb(0, 255, 255)",
                projection=dict(type="orthographic", rotation=dict(lon=-100, lat=40, roll=0)),
                lonaxis=dict(showgrid=True, gridcolor="rgb(102, 102, 102)", gridwidth=0.5),
                lataxis=dict(showgrid=True, gridcolor="rgb(102, 102, 102)", gridwidth=0.5),
            ),
        )

        fig.update_xaxes(showgrid=False)
        fig.update_scenes(hovermode=False)
        fig.update_xaxes(showspikes=False)
        fig.update_yaxes(showspikes=False)
        plotly.offline.plot(fig)
