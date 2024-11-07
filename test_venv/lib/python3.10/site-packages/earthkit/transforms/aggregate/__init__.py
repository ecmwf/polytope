from earthkit.transforms.aggregate import climatology, general, spatial, temporal
from earthkit.transforms.aggregate.general import reduce, resample, rolling_reduce

try:
    from earthkit.data.utils.module_inputs_wrapper import (
        transform_function_inputs,
        transform_module_inputs,
    )
except ImportError:
    pass
else:
    general = transform_module_inputs(general)
    temporal = transform_module_inputs(temporal)
    climatology = transform_module_inputs(climatology)
    spatial = transform_module_inputs(spatial)
    reduce = transform_function_inputs(reduce)
    rolling_reduce = transform_function_inputs(rolling_reduce)
    resample = transform_function_inputs(resample)

__all__ = [
    "__version__",
    "general",
    "temporal",
    "climatology",
    "spatial",
    "reduce",
    "resample",
    "rolling_reduce",
]
