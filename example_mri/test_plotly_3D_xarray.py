import mat73
import numpy as np
import plotly.graph_objects as go
import xarray as xr

data = mat73.loadmat("./example_mri/data/data.mat")
data = data["MRI_defaced"]
# Create sample xarray data
dims = data[200:360:10, 410:460, 90:120]
data = xr.Dataset(
    data_vars=dict(param=(["x", "y", "z"], dims)),
    coords={
        "x": range(0, 16),
        "y": range(0, 50),
        "z": range(0, 30),
    },
)
data = data.to_array()
# Create the vertices
xx, yy, zz = np.meshgrid(data['x'], data['y'], data['z'], indexing='ij')
vertices = np.vstack((xx.flatten(), yy.flatten(), zz.flatten())).T

# Create the trace
trace = go.Scatter3d(x=vertices[:, 0], y=vertices[:, 1], z=vertices[:, 2], mode='markers', marker=dict(
            size=2,
            color=data.values.flatten(),
            opacity=0.3,  # set opacity to 50%
            colorscale='Viridis'  # choose a color scale
        ))

# Create the figure and add the trace
fig = go.Figure(data=trace)

# Update the layout
fig.update_layout(scene=dict(xaxis_title='X Axis', yaxis_title='Y Axis', zaxis_title='Z Axis'))

# Show the figure
fig.show()
