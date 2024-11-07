import xarray as xr

from .decoder import Decoder


class VerticalProfile(Decoder):
    def __init__(self, covjson):
        super().__init__(covjson)
        self.domains = self.get_domains()
        self.ranges = self.get_ranges()

    def get_domains(self):
        domains = []
        for coverage in self.coverage.coverages:
            domains.append(coverage["domain"])
        return domains

    def get_ranges(self):
        ranges = []
        for coverage in self.coverage.coverages:
            ranges.append(coverage["ranges"])
        return ranges

    def get_coordinates(self):
        coord_dict = {}
        for param in self.parameters:
            coord_dict[param] = []
        # Get x,y,z coords and unpack z coords and match to x,y coords
        for ind, domain in enumerate(self.domains):
            x = domain["axes"]["x"]["values"][0]
            y = domain["axes"]["y"]["values"][0]
            t = domain["axes"]["t"]["values"][0]
            zs = domain["axes"]["z"]["values"]
            num = self.mars_metadata[ind]["number"]
            for param in self.parameters:
                coords = []
                for z in zs:
                    # Have to replicate these coords for each parameter
                    # coordinates.append([x, y, z, t])
                    coords.append([x, y, z, num, t])
                coord_dict[param].append(coords)
        return coord_dict

    def get_values(self):
        values = {}
        for parameter in self.parameters:
            values[parameter] = []
            for range in self.ranges:
                values[parameter].append(range[parameter]["values"])
        return values

    def to_geopandas(self):
        pass

    def to_xarray(self):
        dims = ["x", "y", "t", "number", "z"]
        dataarraydict = {}

        for parameter in self.parameters:
            param_values = [[[self.get_values()[parameter]]]]
            for ind, value in enumerate(self.get_values()[parameter]):
                coords = self.get_coordinates()[parameter]
                x = [coords[ind][0][0]]
                y = [coords[ind][0][1]]
                t = [coords[ind][0][4]]
                num = [int(coord[0][3]) for coord in coords]
                coords_z = coords[ind]
                z = [int(coord[2]) for coord in coords_z]
                param_coords = {
                    "x": x,
                    "y": y,
                    "t": t,
                    "number": num,
                    "z": z,
                }
                dataarray = xr.DataArray(
                    param_values,
                    dims=dims,
                    coords=param_coords,
                    name=parameter,
                )
                dataarray.attrs["type"] = self.get_parameter_metadata(parameter)["type"]
                dataarray.attrs["units"] = self.get_parameter_metadata(parameter)["unit"]["symbol"]
                dataarray.attrs["long_name"] = self.get_parameter_metadata(parameter)["description"]
                dataarraydict[dataarray.attrs["long_name"]] = dataarray

        ds = xr.Dataset(dataarraydict)
        print(ds)
        for mars_metadata in self.mars_metadata[0]:
            if mars_metadata != "date" and mars_metadata != "step":
                ds.attrs[mars_metadata] = self.mars_metadata[0][mars_metadata]

        return ds
