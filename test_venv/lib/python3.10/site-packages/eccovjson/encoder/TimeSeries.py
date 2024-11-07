from datetime import datetime, timedelta

import pandas as pd

from .encoder import Encoder


class TimeSeries(Encoder):
    def __init__(self, type, domaintype):
        super().__init__(type, domaintype)

    def add_coverage(self, mars_metadata, coords, values):
        new_coverage = {}
        new_coverage["mars:metadata"] = {}
        new_coverage["type"] = "Coverage"
        new_coverage["domain"] = {}
        new_coverage["ranges"] = {}
        self.add_mars_metadata(new_coverage, mars_metadata)
        self.add_domain(new_coverage, coords)
        self.add_range(new_coverage, values)
        self.covjson["coverages"].append(new_coverage)

    def add_domain(self, coverage, coords):
        coverage["domain"]["type"] = "Domain"
        coverage["domain"]["axes"] = {}
        coverage["domain"]["axes"]["x"] = {}
        coverage["domain"]["axes"]["y"] = {}
        coverage["domain"]["axes"]["z"] = {}
        coverage["domain"]["axes"]["t"] = {}
        coverage["domain"]["axes"]["x"]["values"] = coords["x"]
        coverage["domain"]["axes"]["y"]["values"] = coords["y"]
        coverage["domain"]["axes"]["z"]["values"] = coords["z"]
        coverage["domain"]["axes"]["t"]["values"] = coords["t"]

    def add_range(self, coverage, values):
        for parameter in values.keys():
            param = self.convert_param_id_to_param(parameter)
            coverage["ranges"][param] = {}
            coverage["ranges"][param]["type"] = "NdArray"
            coverage["ranges"][param]["dataType"] = "float"
            coverage["ranges"][param]["shape"] = [len(values[parameter])]
            coverage["ranges"][param]["axisNames"] = [str(param)]
            coverage["ranges"][param]["values"] = values[parameter]

    def add_mars_metadata(self, coverage, metadata):
        coverage["mars:metadata"] = metadata

    def from_xarray(self, dataset):
        for parameter in dataset.data_vars:
            if parameter == "Temperature":
                self.add_parameter("t")
            elif parameter == "Pressure":
                self.add_parameter("p")
        self.add_reference(
            {
                "coordinates": ["x", "y", "z"],
                "system": {
                    "type": "GeographicCRS",
                    "id": "http://www.opengis.net/def/crs/OGC/1.3/CRS84",
                },
            }
        )
        for num in dataset["number"].values:
            dv_dict = {}
            for dv in dataset.data_vars:
                dv_dict[dv] = list(dataset[dv].sel(number=num).values[0][0][0])
            self.add_coverage(
                {
                    "number": num,
                    "type": "forecast",
                    "step": 0,
                },
                {
                    "x": list(dataset["x"].values),
                    "y": list(dataset["y"].values),
                    "z": list(dataset["z"].values),
                    "t": [str(x) for x in dataset["t"].values],
                },
                dv_dict,
            )
        return self.covjson

    def from_polytope(self, result):
        ancestors = [val.get_ancestors() for val in result.leaves]
        values = [val.result for val in result.leaves]

        columns = []
        df_dict = {}
        # Create empty dataframe
        for feature in ancestors[0]:
            columns.append(str(feature).split("=")[0])
            df_dict[str(feature).split("=")[0]] = []

        # populate dataframe
        for ancestor in ancestors:
            for feature in ancestor:
                df_dict[str(feature).split("=")[0]].append(str(feature).split("=")[1])
        values = [val.result for val in result.leaves]
        df_dict["values"] = values
        df = pd.DataFrame(df_dict)

        params = df["param"].unique()

        for param in params:
            self.add_parameter(param)

        self.add_reference(
            {
                "coordinates": ["x", "y", "z"],
                "system": {
                    "type": "GeographicCRS",
                    "id": "http://www.opengis.net/def/crs/OGC/1.3/CRS84",
                },
            }
        )
        steps = df["step"].unique()

        mars_metadata = {}
        mars_metadata["class"] = df["class"].unique()[0]
        mars_metadata["expver"] = df["expver"].unique()[0]
        mars_metadata["levtype"] = df["levtype"].unique()[0]
        mars_metadata["type"] = df["type"].unique()[0]
        mars_metadata["date"] = df["date"].unique()[0]
        mars_metadata["domain"] = df["domain"].unique()[0]
        mars_metadata["stream"] = df["stream"].unique()[0]

        coords = {}
        coords["x"] = list(df["latitude"].unique())
        coords["y"] = list(df["longitude"].unique())
        coords["z"] = ["sfc"]
        coords["t"] = []

        # convert step into datetime
        date_format = "%Y%m%dT%H%M%S"
        date = pd.Timestamp(mars_metadata["date"]).strftime(date_format)
        start_time = datetime.strptime(date, date_format)
        for step in steps:
            # add current date to list by converting it to iso format
            stamp = start_time + timedelta(hours=int(step))
            coords["t"].append(stamp.isoformat())
            # increment start date by timedelta

        if "number" not in df.columns:
            new_metadata = mars_metadata.copy()
            range_dict = {}
            for param in params:
                df_param = df[df["param"] == param]
                range_dict[param] = df_param["values"].values.tolist()
            self.add_coverage(new_metadata, coords, range_dict)
        else:
            for number in df["number"].unique():
                new_metadata = mars_metadata.copy()
                new_metadata["number"] = number
                df_number = df[df["number"] == number]
                range_dict = {}
                for param in params:
                    df_param = df_number[df_number["param"] == param]
                    range_dict[param] = df_param["values"].values.tolist()
                self.add_coverage(new_metadata, coords, range_dict)

        return self.covjson
