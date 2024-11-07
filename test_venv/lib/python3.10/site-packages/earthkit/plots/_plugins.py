from importlib.metadata import entry_points
from pathlib import Path


def register_plugins():
    plugins = dict()
    for plugin in entry_points(group="earthkit.plots.plugins"):
        path = Path(plugin.load().__file__).parents[0]
        plugins[plugin.name] = {
            "identities": path / "identities",
            "schema": path / "schema.yml",
            "styles": path / "styles",
        }
        for key, value in plugins[plugin.name].items():
            if not value.exists():
                plugins[plugin.name][key] = None
    return plugins


PLUGINS = register_plugins()
