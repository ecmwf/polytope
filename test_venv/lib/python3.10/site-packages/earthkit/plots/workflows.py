import json

import earthkit.data

import earthkit.plots


class Parser:
    def __init__(self, workflow):
        self.workflow = workflow

    def to_dict(self, *args, **kwargs):
        raise NotImplementedError

    def process(self):
        workflow = self.to_dict()

        figure = earthkit.plots.Figure(**workflow.get("figure", dict()))

        for subplot_config in workflow.get("subplots", []):
            subplot_type = subplot_config.get("type", "subplot")
            subplot_kwargs = dict()
            if isinstance(subplot_type, dict):
                subplot_type, subplot_kwargs = list(subplot_type.items())[0]
            subplot = getattr(figure, f"add_{subplot_type}")(**subplot_kwargs)

            for plot_layer in subplot_config.get("plot_layers", []):
                method, kwargs = list(plot_layer.items())[0]
                data = earthkit.data.from_source("file", kwargs.pop("data"))
                getattr(subplot, method)(data, **kwargs)

            for ancillary_layer in subplot_config.get("ancillary_layers", []):
                method, kwargs = list(ancillary_layer.items())[0]
                getattr(subplot, method)(**kwargs)

        figure.save(**workflow.get("save", {"fname": "test.png"}))


class DictParser(Parser):
    def to_dict(self, *args, **kwargs):
        return self.workflow


class JSONParser(Parser):
    def to_dict(self, *args, **kwargs):
        with open(self.workflow, "r") as f:
            return json.load(f)


TEST_WORKFLOW = [
    {
        "figure": {"size": (6, 6)},
        "subplots": [
            {
                "type": {"map": {"domain": "Europe"}},
                "plot_layers": [
                    {
                        "block": {
                            "data": "2t-data.grib",
                            "colors": "turbo",
                            "levels": [-40, -30, -20, -10, 0, 10, 20, 30, 40],
                            "units": "celsius",
                        },
                    },
                ],
                "ancillary_layers": [
                    {"coastlines": {}},
                ],
            },
        ],
        "save": {"fname": "2t-tile.png"},
    }
]
