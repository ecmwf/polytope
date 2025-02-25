# Data Portfolio

Polytope feature extraction only has access to data that is stored on an FDB. The datasets currently available via Polyope feature extraction are the operational ECMWF forecast, as well as the data produced by the Destination Earth Extremes and Climate digital twins.

## Operational Forecast Data

The following key value pairs are available via Polytope:

* `class` : `od`
* `stream` : `enfo` `oper`
* `type` : `fc` `pf` `cf`
* `levtype` : `sfc` `pl` `ml`
* `expver` : `0001`
* `domain` : `g`
* `step` : `0/to/360` (All steps may not be available between `0` and `360`)

If `type` is `enfo`:

* `number` : `0/to/50`

If `levtype` is `pl` or `ml`, a `levelist` must be provided:

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

For `sfc`, most `params` will be available but not all.

Only data that is contained in the operational FDB can be requested via Polytope feature extraction. The FDB usually only contains the last two days of forecasts.

We sometimes limit the size of requests for area features such as bounding box and polygon to maintain quality of service.

Access to operational data is limited by our release schedule.


## Extremes DT Data

The following values available for each field specified are:

* `class` : `d1`
* `dataset` : `extremes-dt`
* `stream` : `oper` `wave`
* `type` : `fc`
* `levtype` : `sfc` `pl` `hl`
* `expver` : `0001`
* `domain` : `g`
* `step` : `0/to/96`

If `levtype` is `pl`, a `levelist` must be provided:

* `levelist` : `1/to/1000`

If `levtype` is `hl`, a `levelist` must be provided:

* `levtype` : `100`

`pl` and `hl` also only contain a subset of parameters that are available in grid point. These are:

* `pl`
    * `Geopotential`
    * `Temperature`
    * `U component of wind`
    * `V component of wind`
    * `Specific humidity`
    * `Relative humidity`
* `hl`
    * `100 metre U wind component`
    * `100 metre V wind component `

For `sfc` most `params` are available.

For `stream` : `wave` the following parameters are available:

* `Mean zero-crossing wave period`
* `Significant height of combined wind waves and swell`
* `Mean wave direction`
* `Peak wave period`
* `Mean wave period`

Only Extremes-DT data from the past 15 days can be accessed by users.


## Climate DT Data

The following values available for each field specified are:

* `class` : `d1`
* `dataset` : `climate-dt`
* `activity` : `ScenarioMIP` `story-nudging` `CMIP6`
* `model`: `IFS-NEMO`
* `generation` : `1`
* `realization`: `1`
* `resolution`: `standard` `high`
* `time`: `0000/to/2300`
* `stream` : `clte` 
* `type` : `fc`
* `levtype` : `sfc` `pl` `o2d`
* `expver` : `0001`
* `domain` : `g`

If `levtype` is `pl`, a `levelist` must be provided:

* `levelist` : `1/to/1000`

`pl` is currently being scanned and new parameters will become available as time passes. This is also the case for `o2d`.

For `sfc`, most `params` are available.

Currently, only data for `dates` between `2020` and `2050` is available.

## Open Data

The following key value pairs are available via Polytope:

* `class` : `ai`
* `stream` : `oper`
* `type` : `fc`
* `levtype` : `sfc` `pl` `ml`
* `expver` : `0001`
* `domain` : `g`
* `step` : `0/to/360` (All steps may not be available between `0` and `360`)

If `levtype` is `pl` or `ml`, a `levelist` must be provided:

* `levelist` : `1/to/1000`

`pl` and `ml` also only contain a subset of parameters that are available in grid point. 

For `sfc`, most `params` will be available but not all.

Only data that is contained in the open data FDB can be requested via Polytope feature extraction. The FDB usually only contains the last two-four days of forecasts.

We sometimes limit the size of requests for area features such as bounding box and polygon to maintain quality of service.

Access to open data is limited by our release schedule.
