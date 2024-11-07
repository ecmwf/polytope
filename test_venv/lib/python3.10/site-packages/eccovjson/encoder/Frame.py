from .encoder import Encoder


class Frame(Encoder):
    def __init__(self, type, domaintype):
        super().__init__(type, domaintype)
        self.covjson["domainType"] = "MultiPoint"

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
        coverage["domain"]["axes"]["t"] = {}
        coverage["domain"]["axes"]["t"]["values"] = coords["t"]
        coverage["domain"]["axes"]["composite"] = {}
        coverage["domain"]["axes"]["composite"]["dataType"] = ("tuple",)
        coverage["domain"]["axes"]["composite"]["coordinates"] = self.covjson["referencing"][0]["coordinates"]
        coverage["domain"]["axes"]["composite"]["values"] = coords["composite"]

    def add_range(self, coverage, values):
        for parameter in values.keys():
            param = self.convert_param_id_to_param(parameter)
            coverage["ranges"][param] = {}
            coverage["ranges"][param]["type"] = "NdArray"
            coverage["ranges"][param]["dataType"] = "float"
            coverage["ranges"][param]["shape"] = [len(values[parameter])]
            coverage["ranges"][param]["axisNames"] = [str(param)]
            coverage["ranges"][param]["values"] = values[parameter]  # [values[parameter]]

    def add_mars_metadata(self, coverage, metadata):
        coverage["mars:metadata"] = metadata

    def from_xarray(self, dataset):
        pass

    def from_polytope(self, result, request):
        values = [val.result for val in result.leaves]
        ancestors = [val.get_ancestors() for val in result.leaves]

        mars_metadata = {}
        coords = {}
        for key in request.keys():
            if key != "latitude" and key != "longitude" and key != "param" and key != "number" and key != "step":
                mars_metadata[key] = request[key]

        for param in request["param"].split("/"):
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

        new_metadata = mars_metadata.copy()
        # range_dict = {}
        vals = {}
        for param in request["param"].split("/"):
            param = self.convert_param_id_to_param(param)
            vals[param] = []
        coords = {}
        coords["composite"] = []
        coords["t"] = str(ancestors[0][1]).split("=")[1]

        for ind, feature in enumerate(ancestors[0]):
            if str(feature).split("=")[0] == "latitude":
                lat = ind
            elif str(feature).split("=")[0] == "longitude":
                long = ind
            elif str(feature).split("=")[0] == "param":
                param = ind
                param_id = str(feature).split("=")[1]

        for ind, ancestor in enumerate(ancestors):
            coord = []
            coord.append(str(ancestor[lat]).split("=")[1])
            coord.append(str(ancestor[long]).split("=")[1])
            coord.append("sfc")
            coords["composite"].append(coord)
            param_id = self.convert_param_id_to_param(str(ancestor[param]).split("=")[1])
            vals[param_id].append(values[ind])

        param = self.convert_param_id_to_param(request["param"].split("/")[0])
        coords["composite"] = coords["composite"][0 : len(vals[param])]

        self.add_coverage(new_metadata, coords, vals)
        return self.covjson
