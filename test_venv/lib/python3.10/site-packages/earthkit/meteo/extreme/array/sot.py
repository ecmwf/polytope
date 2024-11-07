# (C) Copyright 2021 ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.
#

import numpy as np


def sot_func(qc_tail, qc, qf, eps=-1e-4, lower_bound=-10, upper_bound=10):
    """Compute basic Shift of Tails (SOT)
    using already computed percentiles

    Parameters
    ----------
    qc_tail: numpy array (npoints)
        Tail percentile value (99% or 1%)
        Model climatology
    qc: numpy array (npoints)
        Upper or lower percentile (at 90% or 10%)
        Model climatology
    qf: numpy array (npoints)
        Upper or lower percentile (at 90% or 10%)
        Ensemble forecast
    eps: (float)
        Epsilon factor for zero values
    missing: (float)
        missing points values where denominator is zero

    Returns
    -------
    numpy array (npoints)
        SOT values
    """
    # avoid divided by zero warning
    err = np.seterr(divide="ignore", invalid="ignore")

    min_den = np.fmax(eps, 0)
    sot = np.where(np.fabs(qc_tail - qc) > min_den, (qf - qc_tail) / (qc_tail - qc), np.nan)

    # revert to original error state
    np.seterr(**err)

    mask_missing = np.isnan(sot)

    # upper and lower bounds
    mask2 = np.logical_and(np.logical_not(mask_missing), sot < lower_bound)
    sot[mask2] = lower_bound
    mask3 = np.logical_and(np.logical_not(mask_missing), sot > upper_bound)
    sot[mask3] = upper_bound

    return sot


def sot(clim, ens, perc, eps=-1e4):
    """Compute Shift of Tails (SOT)
    from climatology percentiles (sorted)
    and ensemble forecast (not sorted)

    Parameters
    ----------
    clim: numpy array (nclim, npoints)
        Model climatology (percentiles)
    ens: numpy array (nens, npoints)
        Ensemble forecast
    perc: int
        Percentile value (typically 10 or 90)
    eps: (float)
        Epsilon factor for zero values

    Returns
    -------
    numpy array (npoints)
        SOT values
    """
    if not (isinstance(perc, int) or isinstance(perc, np.int64)) or (perc < 2 or perc > 98):
        raise Exception("Percentile value should be and Integer between 2 and 98, is {}".format(perc))

    if clim.shape[0] != 101:
        raise Exception(
            "Climatology array should contain 101 percentiles, it has {} values".format(clim.shape)
        )

    qc = clim[perc]
    # if eps>0, set to zero everything below eps
    if eps > 0:
        ens = np.where(ens < eps, 0.0, ens)
        qc = np.where(qc < eps, 0.0, qc)

    qf = np.percentile(ens, q=perc, axis=0)
    if perc > 50:
        qc_tail = clim[99]
    elif perc < 50:
        qc_tail = clim[1]
    else:
        raise Exception(
            "Percentile value to be computed cannot be 50 for sot, has to be in the upper or lower half"
        )

    sot = sot_func(qc_tail, qc, qf, eps=eps)

    return sot


def sot_unsorted(clim, ens, perc, eps=-1e4):
    """Compute Shift of Tails (SOT)
    from climatology percentiles (sorted)
    and ensemble forecast (not sorted)

    Parameters
    ----------
    clim: numpy array (nclim, npoints)
        Model climatology (percentiles)
    ens: numpy array (nens, npoints)
        Ensemble forecast
    perc: int
        Percentile value (typically 10 or 90)
    eps: (float)
        Epsilon factor for zero values

    Returns
    -------
    numpy array (npoints)
        SOT values
    """
    if not (isinstance(perc, int) or isinstance(perc, np.int64)) or (perc < 2 or perc > 98):
        raise Exception("Percentile value should be and Integer between 2 and 98, is {}".format(perc))

    if clim.shape[0] != 101:
        raise Exception(
            "Climatology array should contain 101 percentiles, it has {} values".format(clim.shape)
        )

    if eps > 0:
        ens = np.where(ens < eps, 0.0, ens)
        clim = np.where(clim < eps, 0.0, clim)

    qf = np.percentile(ens, q=perc, axis=0)
    qc = np.percentile(clim, q=perc, axis=0)
    if perc > 50:
        perc_tail = 99
    elif perc < 50:
        perc_tail = 1
    else:
        raise Exception(
            "Percentile value to be computed cannot be 50 for sot, has to be in the upper or lower half"
        )
    qc_tail = np.percentile(clim, q=perc_tail, axis=0)

    sot = sot_func(qc_tail, qc, qf, eps=eps)

    return sot
