# (C) Copyright 2023 ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.
#

from earthkit.regrid.db import find


def interpolate(values, in_grid=None, out_grid=None, method="linear", **kwargs):
    interpolator = _find_interpolator(values)
    if interpolator is None:
        raise ValueError(f"Cannot interpolate data with type={type(values)}")

    return interpolator(
        values, in_grid=in_grid, out_grid=out_grid, method=method, **kwargs
    )


def _find_interpolator(values):
    for interpolator in INTERPOLATORS:
        if interpolator.match(values):
            return interpolator
    return None


def _interpolate(values, in_grid, out_grid, method, **kwargs):
    z, shape = find(in_grid, out_grid, method, **kwargs)

    if z is None:
        raise ValueError(f"No matrix found! {in_grid=} {out_grid=} {method=}")

    # This should check for 1D (GG) and 2D (LL) matrices
    values = values.reshape(-1, 1)

    values = z @ values

    return values.reshape(shape)


class NumpyInterpolator:
    @staticmethod
    def match(values):
        import numpy as np

        return isinstance(values, np.ndarray)

    def __call__(self, values, **kwargs):
        in_grid = kwargs.pop("in_grid")
        out_grid = kwargs.pop("out_grid")
        method = kwargs.pop("method")
        return _interpolate(values, in_grid, out_grid, method, **kwargs)


class FieldListInterpolator:
    @staticmethod
    def match(values):
        try:
            import earthkit.data

            return isinstance(values, earthkit.data.FieldList)
        except ImportError:
            return False

    def __call__(self, values, **kwargs):
        import earthkit.data

        ds = values
        in_grid = kwargs.pop("in_grid")
        if in_grid is not None:
            raise ValueError("in_grid cannot be used for FieldList interpolation")
        out_grid = kwargs.pop("out_grid")
        method = kwargs.pop("method")

        r = earthkit.data.FieldList()
        for f in ds:
            vv = f.to_numpy(flatten=True)
            v_res = _interpolate(
                vv,
                f.metadata().gridspec,
                out_grid,
                method,
                **kwargs,
            )
            md_res = f.metadata().override(gridspec=out_grid)
            r += ds.from_numpy(v_res, md_res)

        return r


INTERPOLATORS = [NumpyInterpolator(), FieldListInterpolator()]
