# Data Portfolio

Polytope feature extraction only has access to data that is stored on an FDB. The dataset currently available via Polyope feature extraction is the operational forecast. We plan to add Destination Earth Digital Twin data in the future.

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

`pl` and `ml` also only contain a subset of parameters that are available in grid point. These are:

* `pl`
    * `o3`
    * `clwc`
    * `q`
    * `pv`
    * `ciwc`
    * `cc`
* `ml`
    * `q`
    * `cat`
    * `o3`
    * `clwc`
    * `ciwc`
    * `cc`
    * `cswc`
    * `crwe`
    * `ttpha`

For `sfc` most `param`s should be available.

Only data that is contained in the operational FDB can be requested via Polytope feature extraction, the FDB usually only contains the last two days of forecasts.

We sometimes limit the size of requests for area features such as bounding box and polygon to maintain quality of service.
