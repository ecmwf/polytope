import mat73
import numpy as np
import plotly
import plotly.graph_objects as go
import xarray as xr

# from polytope.datacube.datacube_request_tree import DatacubeRequestTree
from polytope.datacube.xarray import XArrayDatacube
from polytope.engine.hullslicer import HullSlicer
from polytope.polytope import Polytope, Request
from polytope.shapes import Ellipsoid, Path

if __name__ == "__main__":

    # create background image
    data_array = mat73.loadmat("./example_mri/data/data.mat")
    data_array = data_array["MRI_defaced"]

    dims = data_array[230:360:5, 360:480:2, 40:140:2]
    data_array = xr.Dataset(
        data_vars=dict(param=(["x", "y", "z"], dims)),
        coords={
            "x": range(230, 360, 5),
            "y": range(360, 480, 2),
            "z": range(40, 140, 2),
        },
    )
    data_array = data_array.to_array()

    xx, yy, zz = np.meshgrid(data_array['x'], data_array['y'], data_array['z'], indexing='ij')
    vertices = np.vstack((xx.flatten(), yy.flatten(), zz.flatten())).T

    trace = go.Scatter3d(x=vertices[:, 0], y=vertices[:, 1], z=vertices[:, 2], mode='markers', marker=dict(
                size=2,
                color=data_array.values.flatten(),
                opacity=0.15,
                colorscale='emrld'
            ))
    fig = go.Figure(data=[trace])
    data = fig._data

    # load MRI data
    data_xarray = mat73.loadmat("./example_mri/data/data.mat")
    data_xarray = data_xarray["MRI_defaced"]
    print(data_xarray)
    non_nan_data = data_xarray[~np.isnan(data_xarray)]
    print(non_nan_data)
    vessel_indices = mat73.loadmat("./example_mri/data/vessel_indices.mat")
    vessel_indices = vessel_indices["vessel_locs_left"]
    print(vessel_indices)

    # need to transform data to an xarray datacube

    dims = data_xarray
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
    initial_shape = Ellipsoid(["x", "y", "z"], [0, 0, 0], [0.6, 0.6, 0.6])
    vessel = Path(["x", "y", "z"], initial_shape, *vessel_indices)

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

    vessel_3D = go.Scatter3d(x=x, y=y, z=z, mode="markers", marker=dict(size=1.5, color=intensity_color,
                                                                        colorscale="jet"))
    data = data.append(vessel_3D)

    fig.update_layout(scene=dict(xaxis=dict(showticklabels=False, title=''),
                                 yaxis=dict(showticklabels=False, title=''),
                                 zaxis=dict(showticklabels=False, title='')
                                 ))

    plotly.offline.plot(fig)
