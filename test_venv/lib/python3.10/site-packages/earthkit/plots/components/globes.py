import io
import uuid
from pathlib import Path

from IPython.display import IFrame, Image

from earthkit.plots import ancillary

RESOLUTIONS = {
    "low": 10,
    "medium": 30,
    "high": 50,
    "very high": 150,
}


GLOBE_HTML = """
<head>
    <style> body {{ margin: 0; }} </style>

    <script src="https://unpkg.com/react/umd/react.production.min.js"></script>
    <script src="https://unpkg.com/react-dom/umd/react-dom.production.min.js"></script>
    <script src="https://unpkg.com/@babel/standalone"></script>

    <script src="https://unpkg.com/react-globe.gl"></script>
    <script src="https://unpkg.com/three/build/three.module.js"></script>
    <!--<script src="../../dist/react-globe.gl.js"></script>-->
  </head>

  <body>
    <div id="globeViz"></div>

  <script type="text/jsx" data-type="module">
    import * as THREE from '//unpkg.com/three/build/three.module.js';
    const globeMaterial = new THREE.MeshBasicMaterial();

  const {{ useState, useEffect }} = React;

  const World = () => {{

    const coastlines = {coastlines}

    return <Globe
      globeImageUrl="{img_url}"
      backgroundColor="#00000000"
      width={{{width}}}
      height={{{height}}}
      globeMaterial={{globeMaterial}}
    pathsData={{coastlines}}
    pathPoints="coords"
    pathPointLat={{p => p[1]}}
    pathPointLng={{p => p[0]}}
    pathPointAlt={{0.001}}
    pathColor="#555"
    pathStroke={{0.75}}
    pathTransitionDuration={{0}}
    />;
  }};

  ReactDOM.render(
    <World />,
    document.getElementById('globeViz')
  );
  </script>
  </body>
"""


def globe(
    data,
    style=None,
    out_fn=None,
    out_path=".",
    size=500,
    resolution="medium",
    how="block",
    **kwargs,
):
    """Generate an IFrame containing a templated javascript package."""
    # warnings.warn(
    #     "Generting interactive globes is an EXPERIMENTAL feature and may cause "
    #     "issues with your Jupyter session"
    # )

    import base64

    import cartopy.crs as ccrs
    import matplotlib.pyplot as plt

    from earthkit.plots import Figure

    img_url = "test.png"

    figsize = RESOLUTIONS[resolution]

    figure = Figure(left=0, right=1, bottom=0, top=1, size=(figsize, figsize))

    try:
        crs = data.projection().to_cartopy_crs()
    except AttributeError:
        crs = ccrs.PlateCarree()
    if crs.__class__.__name__ != "PlateCarree":
        crs = ccrs.PlateCarree()

    subplot = figure.add_map(crs=crs, domain=[-180, 180, -90, 90])
    getattr(subplot, how)(data, style=style, transform_first=True)
    extent = subplot.ax.get_extent()
    if extent != (-180.0, 180.0, -90.0, 90.0):
        subplot.ax.set_global()
    subplot.ax.set_frame_on(False)
    figure.save(img_url, pad_inches=0)
    plt.close()

    if not out_fn:
        out_fn = Path(f"{uuid.uuid4()}.html")

    # Generate the path to the output file
    out_path = Path(out_path)
    filepath = out_path / out_fn
    # Check the required directory path exists
    filepath.parent.mkdir(parents=True, exist_ok=True)

    image = Image(img_url)

    img_url = "data:image/png;base64," + base64.b64encode(image.data).decode("ascii")

    coastlines = ancillary.load("coastlines", "geo")

    # The open "wt" parameters are: write, text mode;
    with io.open(filepath, "wt", encoding="utf8") as outfile:
        # The data is passed in as a dictionary so we can pass different
        # arguments to the template
        outfile.write(
            GLOBE_HTML.format(
                img_url=img_url,
                width=size,
                height=size,
                coastlines=coastlines,
            )
        )

    return IFrame(src=filepath, width=size, height=size)
