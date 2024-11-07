from earthkit.plots.components.figures import Figure
from earthkit.plots.schemas import schema


def _quickplot(function):
    def wrapper(*args, return_subplot=True, **kwargs):
        figure = Figure()
        subplot = figure.add_subplot()
        getattr(subplot, function.__name__)(*args, **kwargs)
        for method in schema.quickplot_workflow:
            getattr(subplot, method)()
        if return_subplot:
            return subplot
        else:
            subplot.show()

    return wrapper


@_quickplot
def line(*args, **kwargs):
    """Quick plot"""


plot = line


@_quickplot
def bar(*args, **kwargs):
    """Quick plot"""


@_quickplot
def scatter(*args, **kwargs):
    """Quick plot"""


@_quickplot
def block(*args, **kwargs):
    """Quick plot"""


@_quickplot
def contour(*args, **kwargs):
    """Quick plot"""


@_quickplot
def contourf(*args, **kwargs):
    """Quick plot"""
