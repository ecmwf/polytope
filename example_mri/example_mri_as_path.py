import mat73
import numpy as np

# import plotly
# import plotly.graph_objects as go
import xarray as xr

# from polytope.datacube.datacube_request_tree import DatacubeRequestTree
from polytope.datacube.xarray import XArrayDatacube
from polytope.engine.hullslicer import HullSlicer
from polytope.polytope import Polytope, Request
from polytope.shapes import Ellipsoid, Path


def format_stats_nicely(stats):
    for key in stats.keys():
        print(key)
        print("-----------------------" + "\n")
        actual_stats = stats[key]
        actual_stats_keys = list(actual_stats.keys())
        print(str(actual_stats_keys[0]) + "\t" + str(actual_stats_keys[1]) + "\t" + str(actual_stats_keys[2])
              + "\t" + str(actual_stats_keys[3]))
        print(str(actual_stats[actual_stats_keys[0]]) + "\t" + str(actual_stats[actual_stats_keys[1]]) + "\t"
              + str(actual_stats[actual_stats_keys[2]]) + "\t" + str(actual_stats[actual_stats_keys[3]]))
        print("\n")


if __name__ == "__main__":

    # create background image
    # data_array = mat73.loadmat("./example_mri/data/data.mat")
    # data_array = data_array["MRI_defaced"]
    # print(np.size(data_array))
    # dims = data_array[230:480:5, 300:520:6, 40:140:2]
    # data_array = xr.Dataset(
    #     data_vars=dict(param=(["x", "y", "z"], dims)),
    #     coords={
    #         "x": range(230, 480, 5),
    #         "y": range(300, 520, 6),
    #         "z": range(40, 140, 2),
    #     },
    # )
    # data_array = data_array.to_array()

    # xx, yy, zz = np.meshgrid(data_array['x'], data_array['y'], data_array['z'], indexing='ij')
    # vertices = np.vstack((xx.flatten(), yy.flatten(), zz.flatten())).T

    # trace = go.Scatter3d(x=vertices[:, 0], y=vertices[:, 1], z=vertices[:, 2], mode='markers', marker=dict(
    #             size=3,
    #             color=data_array.values.flatten(),
    #             opacity=0.05,
    #             colorscale='emrld'
    #         ))
    # fig = go.Figure(data=[trace])
    # data = fig._data

    # load MRI data
    data_xarray = mat73.loadmat("./example_mri/data/data.mat")
    data_xarray = data_xarray["MRI_defaced"]
    # print(data_xarray)
    non_nan_data = data_xarray[~np.isnan(data_xarray)]
    # print(non_nan_data)
    vessel_indices = mat73.loadmat("./example_mri/data/vessel_indices.mat")
    vessel_indices = vessel_indices["vessel_locs_left"]
    # print(vessel_indices)

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
    result, stats = API.retrieve_debugging(request)
    print("stats")
    print("=====================")
    print("\n")
    format_stats_nicely(stats)

    # # plot the found points in 3D... maybe try to put a skull 3D image in background?
    # x = []
    # y = []
    # z = []
    # parameter_values = []
    # for i in range(len(result.leaves)):
    #     cubepath = result.leaves[i].flatten()
    #     if 230 < cubepath["x"] < 360:
    #         if 360 < cubepath["y"] < 480:
    #             if 40 < cubepath["z"] < 140:
    #                 x.append(cubepath["x"])
    #                 y.append(cubepath["y"])
    #                 z.append(cubepath["z"])
    #                 parameter_values.append(result.leaves[i].result["param"].item())
    # intensity_color = np.array(parameter_values)
    # print(len(x))
    # print((max(x)-min(x))*(max(y)-min(y))*(max(z)-min(z))*8)

    # vessel_3D = go.Scatter3d(x=x, y=y, z=z, mode="markers", marker_color='blanchedalmond', marker_size=1.5)
    # data = data.append(vessel_3D)

    # fig.update_layout(scene=dict(xaxis=dict(showticklabels=False, title=''),
    #                              yaxis=dict(showticklabels=False, title=''),
    #                              zaxis=dict(showticklabels=False, title='')
    #                              ))

    # plotly.offline.plot(fig)
