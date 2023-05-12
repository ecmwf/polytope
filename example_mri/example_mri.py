import mat73
import numpy as np
import plotly
import plotly.graph_objects as go
import xarray as xr

from polytope.datacube.xarray import XArrayDatacube
from polytope.engine.hullslicer import HullSlicer
from polytope.polytope import Polytope, Request
from polytope.shapes import Ellipsoid, Union

if __name__ == "__main__":
    data = mat73.loadmat("./example_mri/data/data.mat")
    data = data["MRI_defaced"]
    print(data)
    non_nan_data = data[~np.isnan(data)]
    print(non_nan_data)
    print(len(non_nan_data))
    vessel_indices = mat73.loadmat("./example_mri/data/vessel_indices.mat")
    vessel_indices = vessel_indices["vessel_locs_left"]
    print(vessel_indices)

    # need to transform data to an xarray datacube

    dims = data
    array = xr.Dataset(
        data_vars=dict(param=(["x", "y", "z"], dims)),
        coords={
            "x": range(0, 1024),
            "y": range(0, 768),
            "z": range(0, 176),
        },
    )

    xarraydatacube = XArrayDatacube(array)
    slicer = HullSlicer()
    API = Polytope(datacube=array, engine=slicer)

    # for each of the vessel indices, transform to a polytope point object
    first_polytope_point = Ellipsoid(["x", "y", "z"], vessel_indices[0], [0.6, 0.6, 0.6])
    vessel = first_polytope_point
    for i in range(len(vessel_indices)-1):
        point = vessel_indices[i+1]
        polytope_point = Ellipsoid(["x", "y", "z"], point, [1, 1, 1])
        vessel = Union(["x", "y", "z"], polytope_point, vessel)
    # retrieve the points from the datacube using polytope
    request = Request(vessel)
    result = API.retrieve(request)

    # plot the found points in 3D... maybe try to put a skull 3D image in background?
    x = []
    y = []
    z = []
    parameter_values = []
    for i in range(len(result.leaves)):
        cubepath = result.leaves[i].flatten()
        x.append(cubepath["x"])
        y.append(cubepath["y"])
        z.append(cubepath["z"])
        parameter_values.append(result.leaves[i].result["param"].item())
    intensity_color = np.array(parameter_values)

    trace = go.Surface(z=data[200:360])

    # create the layout
    layout = go.Layout(
        title='3D Surface Plot',
        scene=dict(
            xaxis=dict(title='X Axis'),
            yaxis=dict(title='Y Axis'),
            zaxis=dict(title='Z Axis')
        )
    )

    # create the figure
    fig = go.Figure(data=[trace], layout=layout)
    data = fig._data

    vessel_3D = go.Scatter3d(
        x=x, y=y, z=z, mode="markers", marker=dict(size=1.5, color=intensity_color, colorscale="viridis")
    )
    data.append(vessel_3D)
    fig = go.Figure(data=data)

    plotly.offline.plot(fig)
