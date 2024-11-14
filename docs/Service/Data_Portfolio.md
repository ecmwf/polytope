# Data Portfolio

Polytope Feature Extraction only has access to data that is stored on an FDB. The dataset currently available via polyope feature extraction is the Operational Forecast. We plan to add Destination Earth Digital Twin data in the future.

## Operational Forecast Data

The following values available for each field specified are:

* `class` : `od`
* `stream` : `enfo` `oper`
* `type` : `fc` `pf` `cf`
* `levtype` : `sfc` `pl` `ml`
* `expver` : `0001`
* `domain` : `g`
* `step` : `0/to/360` (All steps may not be available between `0` and `360`)

If `type` is `enfo`:

* `number` : `0/to/50`

If `levtype` is `pl` or `ml` a `levelist` must be provided:

* `levelist` : `1/to/1000`

`pl` and `ml` also only contain a subset of parameters that are available