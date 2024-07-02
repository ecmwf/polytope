# (C) Copyright 2021 ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.
#

import numpy as np

"""
Collection of meteorological constants in SI units.
"""

# Thermodynamics. Values were taken form the IFS CY47r3 documentation.

R = 8.31451
r"""Universal gas constant [:math:`J K^{-1} mol^{-1}`].
See [IFS-CY47R3-PhysicalProcesses]_ (Chapter 12)."""

Rd = 287.0597
r"""Gas constant for dry air [:math:`J kg^{-1} K^{-1}`].
See [IFS-CY47R3-PhysicalProcesses]_ (Chapter 12)."""

Rv = 461.51
r"""Gas constant for water vapour [:math:`J kg^{-1} K^{-1}`].
 See [IFS-CY47R3-PhysicalProcesses]_ (Chapter 12)."""

c_pd = 1004.79
r"""Specific heat of dry air on constant pressure [:math:`J kg^{-1} K^{-1}`].
See [IFS-CY47R3-PhysicalProcesses]_ (Chapter 12)."""

c_pv = 1846.1
r"""Specific heat of water vapour on constant pressure [:math:`J kg^{-1} K^{-1}`].
See [IFS-CY47R3-PhysicalProcesses]_ (Chapter 12)."""

Lv = 2.5008e6
r"""Latent heat of vapourisation [:math:`J kg^{-1}`]."""

kappa = 0.285691
r"""Kappa coefficient used in adiabatic equations :math:`\kappa = \frac{R_{d}}{C_{pd}}`."""

p0 = 1e5
r"""Reference pressure used in potential temperature calculations [Pa]."""

epsilon = 0.621981
r"""Epsilon coefficient used in humidity formulas :math:`\epsilon = \frac{R_{d}}{R_{v}}`."""

T0 = 273.16
r"""Triple point of water [K]."""

g = 9.80665
r"""Gravitational acceleration on the surface of the Earth [:math:`m s^{-2}`].
See [IFS-CY47R3-PhysicalProcesses]_ (Chapter 12)."""

R_earth = 6371229
r"""Average radius of the Earth [:math:`m`]. See [IFS-CY47R3-PhysicalProcesses]_
 (Chapter 12)."""

solar_day = 86400
r"""Length of the solar day [:math:`s`]."""

sideral_year = 365.25 * solar_day * 2 * np.pi / 6.283076
r"""Length of the sideral year [:math:`s`].
Defined as :math:`\frac{2\pi\times 365.25\times solar\_day}{6.283076}`."""

sideral_day = solar_day / (1.0 + solar_day / sideral_year)
r"""Length of the sideral day [:math:`s`].
Defined as :math:`\frac{solar\_day}{1 + \frac{solar\_day}{sideral\_year}}`."""

omega = 2.0 * np.pi / sideral_day
r"""Rotation rate of the Earth [:math:`s^{-1}`].
Defined as :math:`\frac{2\pi}{sideral\_day}`."""

degree = 180.0 / np.pi
r"""Factor for converting radians to degrees."""

radian = 1.0 / degree
r"""Factor for converting degrees to radians."""
