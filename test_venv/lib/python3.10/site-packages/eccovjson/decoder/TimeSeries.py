import datetime as dt

import xarray as xr

from .decoder import Decoder


class TimeSeries(Decoder):
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

    def get_values(self):
        values = {}
        for parameter in self.parameters:
            values[parameter] = []
            for range in self.ranges:
                values[parameter].append(range[parameter]["values"])
            # values[parameter] = [
            #    value for sublist in values[parameter] for value in sublist
            # ]
        return values

    def get_coordinates(self):
        coord_dict = {}
        for param in self.parameters:
            coord_dict[param] = []
        # Get x,y,z,t coords and unpack t coords and match to x,y,z coords
        for ind, domain in enumerate(self.domains):
            x = domain["axes"]["x"]["values"][0]
            y = domain["axes"]["y"]["values"][0]
            z = domain["axes"]["z"]["values"][0]
            fct = self.mars_metadata[ind]["date"]
            ts = domain["axes"]["t"]["values"]
            num = self.mars_metadata[ind]["number"]
            for param in self.parameters:
                coords = []
                for t in ts:
                    # Have to replicate these coords for each parameter
                    # coordinates.append([x, y, z, t])
                    coords.append([x, y, z, fct, t, num])
                coord_dict[param].append(coords)
        return coord_dict

    def to_geopandas(self):
        pass

    # function to convert covjson to xarray dataset
    def to_xarray(self):
        dims = ["x", "y", "z", "number", "t"]
        dataarraydict = {}

        # Get coordinates
        for parameter in self.parameters:
            param_values = [[[self.get_values()[parameter]]]]
            for ind, fc_time_vals in enumerate(self.get_values()[parameter]):
                coords = self.get_coordinates()[parameter]
                x = [coords[ind][0][0]]
                y = [coords[ind][0][1]]
                z = [coords[ind][0][2]]
                # fct = [
                #    dt.datetime.strptime((coord[0][3]), "%Y%m%d") for coord in coords
                # ]
                num = [int(coord[0][5]) for coord in coords]
                coords_fc = coords[ind]
                try:
                    t = [dt.datetime.strptime(coord[4], "%Y-%m-%d %H:%M:%S") for coord in coords_fc]
                except ValueError:
                    t = [dt.datetime.strptime(coord[4], "%Y-%m-%dT%H:%M:%S") for coord in coords_fc]

                param_coords = {"x": x, "y": y, "z": z, "number": num, "t": t}
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
        for mars_metadata in self.mars_metadata[0]:
            if mars_metadata != "date" and mars_metadata != "step":
                ds.attrs[mars_metadata] = self.mars_metadata[0][mars_metadata]

        return ds


"""
    def to_xarray(self):
        dims = ["x", "y", "z", "fct", "t"]
        dataarraydict = {}

        # Get coordinates
        for parameter in self.parameters:
            param_values = [[[self.get_values()[parameter]]]]
            for ind, fc_time_vals in enumerate(self.get_values()[parameter]):
                coords = self.get_coordinates()[parameter]
                x = [coords[ind][0][0]]
                y = [coords[ind][0][1]]
                z = [coords[ind][0][2]]

                fct = [
                    dt.datetime.strptime((coord[0][3]), "%Y%m%d") for coord in coords
                ]
                coords_fc = coords[ind]
                t = [
                    dt.datetime.strptime(coord[4], "%Y-%m-%d %H:%M:%S")
                    for coord in coords_fc
                ]

                param_coords = {"x": x, "y": y, "z": z, "fct": fct, "t": t}
                dataarray = xr.DataArray(
                    param_values,
                    dims=dims,
                    coords=param_coords,
                    name=parameter,
                )

                dataarray.attrs["type"] = self.get_parameter_metadata(parameter)["type"]
                dataarray.attrs["units"] = self.get_parameter_metadata(parameter)[
                    "unit"
                ]["symbol"]
                dataarray.attrs["long_name"] = self.get_parameter_metadata(parameter)[
                    "description"
                ]
                dataarraydict[dataarray.attrs["long_name"]] = dataarray

        ds = xr.Dataset(dataarraydict)
        for mars_metadata in self.mars_metadata[0]:
            if mars_metadata != "date" and mars_metadata != "step":
                ds.attrs[mars_metadata] = self.mars_metadata[0][mars_metadata]

        return ds
"""
