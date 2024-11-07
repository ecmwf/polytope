# (C) Copyright 2021 ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.
#

import numpy as np


def cpf(clim, ens, sort_clim=True, sort_ens=True):
    """Compute Crossing Point Forecast (CPF)

    WARNING: this code is experimental, use at your own risk!

    Parameters
    ----------
    clim: numpy array (nclim, npoints)
        Per-point climatology
    ens: numpy array (nens, npoints)
        Ensemble forecast
    sort_clim: bool
        If True, sort the climatology first
    sort_ens: bool
        If True, sort the ensemble first

    Returns
    -------
    numpy array (npoints)
        CPF values
    """
    nclim, npoints = clim.shape
    nens, npoints_ens = ens.shape
    assert npoints == npoints_ens

    cpf = np.ones(npoints, dtype=np.float32)
    mask = np.zeros(npoints, dtype=np.bool_)

    if sort_clim:
        clim = np.sort(clim, axis=0)
    if sort_ens:
        ens = np.sort(ens, axis=0)

    for icl in range(1, nclim - 1):
        # quantile level of climatology
        tau_c = icl / (nclim - 1.0)
        for iq in range(nens):
            # quantile level of forecast
            tau_f = (iq + 1.0) / (nens + 1.0)
            if tau_f >= tau_c:
                # quantile values of forecast and climatology
                qv_f = ens[iq, :]
                qv_c = clim[icl, :]

                # lowest climate quantile: interpolate between 2 consecutive quantiles
                if iq < 2:
                    # quantile value and quantile level of climatology at previous
                    qv_c_2 = clim[icl - 1, :]
                    tau_c_2 = (icl - 1) / (nclim - 1)

                    # condition of crossing situtaion:
                    idx = (qv_f < qv_c) & (qv_c_2 < qv_c)

                    # intersection between two lines
                    tau_i = (tau_c * (qv_c_2[idx] - qv_f[idx]) + tau_c_2 * (qv_f[idx] - qv_c[idx])) / (
                        qv_c_2[idx] - qv_c[idx]
                    )

                    # populate matrix, no values below 0
                    cpf[idx] = np.maximum(tau_i, 0)
                    mask[idx] = True

                # check crossing cases
                idx = (qv_f < qv_c) & (~mask)
                cpf[idx] = tau_f
                mask[idx] = True

                # largest climate quantile: interpolate
                if iq == nens - 1:
                    qv_c_2 = clim[nclim - 1, :]
                    tau_c_2 = 1.0

                    idx = (qv_f > qv_c) & (qv_c_2 > qv_c) & (~mask)

                    tau_i = (tau_c * (qv_c_2[idx] - qv_f[idx]) + tau_c_2 * (qv_f[idx] - qv_c[idx])) / (
                        qv_c_2[idx] - qv_c[idx]
                    )

                    # populate matrix, no values above 1
                    cpf[idx] = np.minimum(tau_i, 1)

                # speed up process
                break

    return cpf
