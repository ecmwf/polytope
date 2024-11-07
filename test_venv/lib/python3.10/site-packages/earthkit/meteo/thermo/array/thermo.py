# (C) Copyright 2021 ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.
#


import numpy as np

from earthkit.meteo import constants


def _valid_number(x):
    return x is not None and not np.isnan(x)


def celsius_to_kelvin(t):
    """Converts temperature values from Celsius to Kelvin.

    Parameters
    ----------
    t : number or ndarray
        Temperature in Celsius units

    Returns
    -------
    number or ndarray
        Temperature in Kelvin units

    """
    return t + constants.T0


def kelvin_to_celsius(t):
    """Converts temperature values from Kelvin to Celsius.

    Parameters
    ----------
    t : number or ndarray
        Temperature in Kelvin units

    Returns
    -------
    number or ndarray
        Temperature in Celsius units

    """
    return t - constants.T0


def specific_humidity_from_mixing_ratio(w):
    r"""Computes the specific humidity from mixing ratio.

    Parameters
    ----------
    w : number or ndarray
        Mixing ratio (kg/kg)

    Returns
    -------
    number or ndarray
        Specific humidity (kg/kg)


    The result is the specific humidity in kg/kg units. The computation is based on
    the following definition [Wallace2006]_:

    .. math::

        q = \frac {w}{1+w}

    """
    return w / (1 + w)


def mixing_ratio_from_specific_humidity(q):
    r"""Computes the mixing ratio from specific humidity.

    Parameters
    ----------
    q : number or ndarray
        Specific humidity (kg/kg)

    Returns
    -------
    number or ndarray
        Mixing ratio (kg/kg)


    The result is the mixing ratio in kg/kg units. The computation is based on
    the following definition [Wallace2006]_:

    .. math::

        w = \frac {q}{1-q}

    """
    return q / (1 - q)


def vapour_pressure_from_specific_humidity(q, p):
    r"""Computes the vapour pressure from specific humidity.

    Parameters
    ----------
    q: number or ndarray
        Specific humidity (kg/kg)
    p: number or ndarray
        Pressure (Pa)

    Returns
    -------
    number or ndarray
        Vapour pressure (Pa)


    The computation is based on the following formula [Wallace2006]_:

    .. math::

        e = \frac{p\;q}{\epsilon\; (1 + q(\frac{1}{\epsilon} -1 ))}

    with :math:`\epsilon =  R_{d}/R_{v}` (see :data:`earthkit.meteo.constants.epsilon`).

    """
    c = constants.epsilon * (1 / constants.epsilon - 1)
    return (p * q) / (constants.epsilon + c * q)


def vapour_pressure_from_mixing_ratio(w, p):
    r"""Computes the vapour pressure from mixing ratio.

    Parameters
    ----------
    w: number or ndarray
        Mixing ratio (kg/kg)
    p: number or ndarray
        Pressure (Pa)

    Returns
    -------
    number or ndarray
        Vapour pressure (Pa)


    The computation is based on the following formula:

    .. math::

        e = \frac{p\;w}{\epsilon + w}

    with :math:`\epsilon =  R_{d}/R_{v}` (see :data:`earthkit.meteo.constants.epsilon`).

    """
    return (p * w) / (constants.epsilon + w)


def specific_humidity_from_vapour_pressure(e, p, eps=1e-4):
    r"""Computes the specific humidity from vapour pressure.

    Parameters
    ----------
    e: number or ndarray
        Vapour pressure (Pa)
    p: number or ndarray
        Pressure (Pa)
    eps: number
        Where p - e < ``eps`` np.nan is returned.

    Returns
    -------
    number or ndarray
        Specific humidity (kg/kg)


    The computation is based on the following formula:

    .. math::

       q = \frac{\epsilon e}{p + e(\epsilon-1)}

    with :math:`\epsilon = R_{d}/R_{v}` (see :data:`earthkit.meteo.constants.epsilon`).

    """
    if eps <= 0:
        raise ValueError(f"specific_humidity_from_vapour_pressure(): eps={eps} must be > 0")

    v = np.asarray(p + (constants.epsilon - 1) * e)
    v[np.asarray(p - e) < eps] = np.nan
    return constants.epsilon * e / v


def mixing_ratio_from_vapour_pressure(e, p, eps=1e-4):
    r"""Computes the mixing ratio from vapour pressure.

    Parameters
    ----------
    e: number or ndarray
        Vapour pressure (Pa)
    p: number or ndarray
        Pressure (Pa)
    eps: number
        Where p - e < ``eps`` np.nan is returned.

    Returns
    -------
    number or ndarray
        Mixing ratio (kg/kg).


    The computation is based on the following formula:

    .. math::

       w = \frac{\epsilon e}{p - e}

    with :math:`\epsilon = R_{d}/R_{v}` (see :data:`earthkit.meteo.constants.epsilon`).

    """
    if eps <= 0:
        raise ValueError(f"mixing_ratio_from_vapour_pressure(): eps={eps} must be > 0")

    v = np.asarray(p - e)
    v[v < eps] = np.nan
    return constants.epsilon * e / v


class _EsComp:
    c1 = 611.21
    c3w = 17.502
    c4w = 32.19
    c3i = 22.587
    c4i = -0.7
    t0 = 273.16
    ti = t0 - 23
    PHASES = ["mixed", "water", "ice"]

    def _check_phase(self, phase):
        if phase not in _EsComp.PHASES:
            raise ValueError(
                f"saturation_vapour_pressure(): invalid phase={phase}! Allowed values = {_EsComp.PHASES}"
            )
        return True

    def compute_es(self, t, phase):
        self._check_phase(phase)
        if phase == "mixed":
            return self._es_mixed(t)
        elif phase == "water":
            return self._es_water(t)
        elif phase == "ice":
            return self._es_ice(t)

    def compute_slope(self, t, phase):
        self._check_phase(phase)
        if phase == "mixed":
            return self._es_mixed_slope(t)
        elif phase == "water":
            return self._es_water_slope(t)
        elif phase == "ice":
            return self._es_ice_slope(t)

    def t_from_es(self, es):
        v = np.log(es / self.c1)
        return (v * self.c4w - self.c3w * self.t0) / (v - self.c3w)

    def _es_water(self, t):
        return self.c1 * np.exp(self.c3w * (t - self.t0) / (t - self.c4w))

    def _es_ice(self, t):
        return self.c1 * np.exp(self.c3i * (t - self.t0) / (t - self.c4i))

    def _es_mixed(self, t):
        # Fraction of liquid water (=alpha):
        #   t <= ti => alpha=0
        #   t > ti and t < t0 => alpha=(t-ti)/(t0-ti))^2
        #   t >= t0 => alpha=1
        #
        # svp is interpolated between the ice and water phases:
        #   svp = alpha * es_water + (1.0 - alpha) * es_ice

        t = np.asarray(t)
        svp = np.zeros(t.shape)

        # ice range
        i_mask = t <= self.ti
        svp[i_mask] = self._es_ice(t[i_mask])

        # water range
        w_mask = t >= self.t0
        svp[w_mask] = self._es_water(t[w_mask])

        # mixed range
        m_mask = ~(i_mask | w_mask)
        alpha = np.square(t[m_mask] - self.ti) / np.square(self.t0 - self.ti)
        svp[m_mask] = alpha * self._es_water(t[m_mask]) + (1.0 - alpha) * self._es_ice(t[m_mask])
        return svp

    def _es_water_slope(self, t):
        return self._es_water(t) * (self.c3w * (self.t0 - self.c4w)) / np.square(t - self.c4w)

    def _es_ice_slope(self, t):
        return self._es_ice(t) * (self.c3i * (self.t0 - self.c4i)) / np.square(t - self.c4i)

    def _es_mixed_slope(self, t):
        t = np.asarray(t)
        d_svp = np.zeros(t.shape)

        # ice range
        i_mask = t <= self.ti
        d_svp[i_mask] = self._es_ice_slope(t[i_mask])

        # water range
        w_mask = t >= self.t0
        d_svp[w_mask] = self._es_water_slope(t[w_mask])

        # mixed range
        m_mask = ~(i_mask | w_mask)
        alpha = np.square(t[m_mask] - self.ti) / np.square(self.t0 - self.ti)
        d_alpha = (2.0 / np.square(self.t0 - self.ti)) * (t[m_mask] - self.ti)
        t_m = t[m_mask]
        d_svp[m_mask] = (
            d_alpha * self._es_water(t_m)
            + alpha * self._es_water_slope(t_m)
            - d_alpha * self._es_ice(t_m)
            + (1.0 - alpha) * self._es_ice_slope(t_m)
        )
        return d_svp


def saturation_vapour_pressure(t, phase="mixed"):
    r"""Computes the saturation vapour pressure from temperature with respect to a phase.

    Parameters
    ----------
    t: ndarray
        Temperature (K)
    phase: str, optional
        Defines the phase with respect to the saturation vapour pressure is computed.
        It is either “water”, “ice” or “mixed”.

    Returns
    -------
    ndarray
        Saturation vapour pressure (Pa)


    The algorithm was taken from the IFS model [IFS-CY47R3-PhysicalProcesses]_ (see Chapter 12).
    It uses the following formula when ``phase`` is "water" or "ice":

    .. math::

        e_{sat} = a_{1}\;exp \left(a_{3}\frac{t-273.16}{t-a_{4}}\right)

    where the parameters are set as follows:

    * ``phase`` = "water": :math:`a_{1}` =611.21 Pa, :math:`a_{3}` =17.502 and :math:`a_{4}` =32.19 K
    * ``phase`` = "ice": :math:`a_{1}` =611.21 Pa, :math:`a_{3}` =22.587 and :math:`a_{4}` =-0.7 K

    When ``phase`` is "mixed" the formula is based on the value of ``t``:

    * if :math:`t <= t_{i}`: the formula for ``phase`` = "ice" is used (:math:`t_{i} = 250.16 K`)
    * if :math:`t >= t_{0}`: the formula for ``phase`` = "water" is used (:math:`t_{0} = 273.16 K`)
    * for the range :math:`t_{i} < t < t_{0}` an interpolation is used between the "ice" and "water" phases:

    .. math::

        \alpha(t) e_{wsat}(t) + (1 - \alpha(t)) e_{isat}(t)

    with :math:`\alpha(t) = (\frac{t-t_{i}}{t_{0}-t_{i}})^2`.

    """
    return _EsComp().compute_es(t, phase)


def saturation_mixing_ratio(t, p, phase="mixed"):
    r"""Computes the saturation mixing ratio from temperature with respect to a phase.

    Parameters
    ----------
    t: ndarray
        Temperature (K)
    p: ndarray
        Pressure (Pa)
    phase: str
        Defines the phase with respect to the :func:`saturation_vapour_pressure` is computed.
        It is either “water”, “ice” or “mixed”.

    Returns
    -------
    ndarray
        Saturation mixing ratio (kg/kg)


    Equivalent to the following code:

    .. code-block:: python

        e = saturation_vapour_pressure(t, phase=phase)
        return mixing_ratio_from_vapour_pressure(e, p)

    """
    e = saturation_vapour_pressure(t, phase=phase)
    return mixing_ratio_from_vapour_pressure(e, p)


def saturation_specific_humidity(t, p, phase="mixed"):
    r"""Computes the saturation specific humidity from temperature with respect to a phase.

    Parameters
    ----------
    t: ndarray
        Temperature (K)
    p: ndarray
        Pressure (Pa)
    phase: str, optional
        Defines the phase with respect to the :func:`saturation_vapour_pressure` is computed.
        It is either “water”, “ice” or “mixed”.

    Returns
    -------
    ndarray
        Saturation specific humidity (kg/kg)


    Equivalent to the following code:

    .. code-block:: python

        e = saturation_vapour_pressure(t, phase=phase)
        return specific_humidity_from_vapour_pressure(e, p)

    """
    e = saturation_vapour_pressure(t, phase=phase)
    return specific_humidity_from_vapour_pressure(e, p)


def saturation_vapour_pressure_slope(t, phase="mixed"):
    r"""Computes the slope of saturation vapour pressure with respect to temperature.

    Parameters
    ----------
    t: ndarray
        Temperature (K)
    phase: str, optional
        Defines the phase with respect to the computation will be performed.
        It is either “water”, “ice” or “mixed”. See :func:`saturation_vapour_pressure`
        for details.

    Returns
    -------
    ndarray
        Slope of saturation vapour pressure (Pa/K)

    """
    return _EsComp().compute_slope(t, phase)


def saturation_mixing_ratio_slope(t, p, es=None, es_slope=None, phase="mixed", eps=1e-4):
    r"""Computes the slope of saturation mixing ratio with respect to temperature.

    Parameters
    ----------
    t: ndarray
        Temperature (K)
    p: ndarray
        Pressure (Pa)
    es: ndarray or None, optional
        :func:`saturation_vapour_pressure` pre-computed for the given ``phase`` (Pa)
    es_slope: ndarray or None, optional
        :func:`saturation_vapour_pressure_slope` pre-computed for the given ``phase`` (Pa/K)
    phase: str, optional
        Defines the phase with respect to the computation will be performed.
        It is either “water”, “ice” or “mixed”. See :func:`saturation_vapour_pressure`
        for details.
    eps: number
        Where p - es < ``eps`` np.nan is returned.

    Returns
    -------
    ndarray
        Slope of saturation mixing ratio (:math:`kg kg^{-1} K^{-1}`)


    The computation is based on the following formula:

    .. math::

        \frac{\partial w_{s}}{\partial t} = \frac{\epsilon\; p}{(p-e_{s})^{2}} \frac{d e_{s}}{d t}

    where

        * :math:`\epsilon = R_{d}/R_{v}` (see :data:`earthkit.meteo.constants.epsilon`).
        * :math:`e_{s}` is the :func:`saturation_vapour_pressure` for the given ``phase``

    """
    if eps <= 0:
        raise ValueError(f"saturation_mixing_ratio_slope(): eps={eps} must be > 0")
    if es is None:
        es = saturation_vapour_pressure(t, phase=phase)
    if es_slope is None:
        es_slope = saturation_vapour_pressure_slope(t, phase=phase)

    v = np.asarray(p - es)
    v[v < eps] = np.nan
    return constants.epsilon * es_slope * p / np.square(v)


def saturation_specific_humidity_slope(t, p, es=None, es_slope=None, phase="mixed", eps=1e-4):
    r"""Computes the slope of saturation specific humidity with respect to temperature.

    Parameters
    ----------
    t: ndarray
        Temperature (K)
    p: ndarray
        Pressure (Pa)
    es: ndarray or None, optional
        :func:`saturation_vapour_pressure` pre-computed for the given ``phase`` (Pa)
    es_slope: ndarray or None, optional
        :func:`saturation_vapour_pressure_slope` pre-computed for the given ``phase`` (Pa/K)
    phase: str, optional
        Defines the phase with respect to the computation will be performed.
        It is either “water”, “ice” or “mixed”. See :func:`saturation_vapour_pressure`
        for details.
    eps: number
        Where p - es < ``eps`` np.nan is returned.

    Returns
    -------
    ndarray
        Slope of saturation specific humidity (:math:`kg kg^{-1} K^{-1}`)


    The computation is based on the following formula:

    .. math::

        \frac{\partial q_{s}}{\partial t} =
        \frac{\epsilon\; p}{(p+e_{s}(\epsilon - 1))^{2}} \frac{d e_{s}}{d t}

    where

        * :math:`\epsilon = R_{d}/R_{v}` (see :data:`earthkit.meteo.constants.epsilon`).
        * :math:`e_{s}` is the :func:`saturation_vapour_pressure` for the given ``phase``

    """
    if eps <= 0:
        raise ValueError(f"saturation_specific_humidity_slope(): eps={eps} must be > 0")
    if es is None:
        es = saturation_vapour_pressure(t, phase=phase)
    if es_slope is None:
        es_slope = saturation_vapour_pressure_slope(t, phase=phase)

    v = np.asarray(np.square(p + es * (constants.epsilon - 1.0)))
    v[np.asarray(p - es) < eps] = np.nan
    return constants.epsilon * es_slope * p / v


def temperature_from_saturation_vapour_pressure(es):
    r"""Compute the temperature from saturation vapour pressure.

    Parameters
    ----------
    es: ndarray
        :func:`saturation_vapour_pressure` (Pa)

    Returns
    -------
    ndarray
        Temperature (K). For zero ``es`` values returns np.nan.


    The computation is always based on the "water" phase of
    the :func:`saturation_vapour_pressure` formulation irrespective of the
    phase ``es`` was computed to.

    """
    return _EsComp().t_from_es(es)


def relative_humidity_from_dewpoint(t, td):
    r"""Computes the relative humidity from dewpoint temperature.

    Parameters
    ----------
    t: ndarray
        Temperature (K)
    td: ndarray
        Dewpoint (K)

    Returns
    -------
    ndarray
        Relative humidity (%)


    The computation is based on the following formula:

    .. math::

        r = 100 \frac {e_{wsat}(td)}{e_{wsat}(t)}

    where :math:`e_{wsat}` is the :func:`saturation_vapour_pressure` over water.

    """
    e = saturation_vapour_pressure(td, phase="water")
    es = saturation_vapour_pressure(t, phase="water")
    return 100.0 * e / es


def relative_humidity_from_specific_humidity(t, q, p):
    r"""Computes the relative humidity from specific humidity.

    Parameters
    ----------
    t: ndarray
        Temperature (K)
    q: ndarray
        Specific humidity (kg/kg)
    p: ndarray
        Pressure (Pa)

    Returns
    -------
    ndarray
        Relative humidity (%)


    The computation is based on the following formula:

    .. math::

        r = 100 \frac {e(q, p)}{e_{msat}(t)}

    where:

        * :math:`e` is the vapour pressure (see :func:`vapour_pressure_from_specific_humidity`)
        * :math:`e_{msat}` is the :func:`saturation_vapour_pressure` based on the "mixed" phase

    """
    svp = saturation_vapour_pressure(t)
    e = vapour_pressure_from_specific_humidity(q, p)
    return 100.0 * e / svp


def specific_humidity_from_dewpoint(td, p):
    r"""Computes the specific humidity from dewpoint.

    Parameters
    ----------
    td: ndarray
        Dewpoint (K)
    p: ndarray
        Pressure (Pa)

    Returns
    -------
    ndarray
        Specific humidity (kg/kg)


    The computation starts with determining the vapour pressure:

    .. math::

        e(q, p) = e_{wsat}(td)

    where:

        * :math:`e` is the vapour pressure (see :func:`vapour_pressure_from_specific_humidity`)
        * :math:`e_{wsat}` is the :func:`saturation_vapour_pressure` over water
        * :math:`q` is the specific humidity

    Then `q` is computed from :math:`e` using :func:`specific_humidity_from_vapour_pressure`.

    """
    svp = saturation_vapour_pressure(td, phase="water")
    return specific_humidity_from_vapour_pressure(svp, p)


def mixing_ratio_from_dewpoint(td, p):
    r"""Computes the mixing ratio from dewpoint.

    Parameters
    ----------
    td: ndarray
        Dewpoint (K)
    p: ndarray
        Pressure (Pa)

    Returns
    -------
    ndarray
        Specific humidity (kg/kg)


    The computation starts with determining the vapour pressure:

    .. math::

        e(w, p) = e_{wsat}(td)

    where:

        * :math:`e` is the vapour pressure (see :func:`vapour_pressure_from_mixing_ratio`)
        * :math:`e_{wsat}` is the :func:`saturation_vapour_pressure` over water
        * :math:`w` is the mixing ratio

    Then `w` is computed from :math:`e` using :func:`mixing_ratio_from_vapour_pressure`.

    """
    svp = saturation_vapour_pressure(td, phase="water")
    return mixing_ratio_from_vapour_pressure(svp, p)


def specific_humidity_from_relative_humidity(t, r, p):
    r"""Computes the specific humidity from relative_humidity.

    Parameters
    ----------
    t: ndarray
        Temperature (K)
    r: ndarray
        Relative humidity(%)
    p: ndarray
        Pressure (Pa)

    Returns
    -------
    ndarray
        Specific humidity (kg/kg) units


    The computation starts with determining the the vapour pressure:

    .. math::

        e(q, p) = r\; \frac{e_{msat}(t)}{100}

    where:

        * :math:`e` is the vapour pressure (see :func:`vapour_pressure`)
        * :math:`e_{msat}` is the :func:`saturation_vapour_pressure` based on the "mixed" phase
        * :math:`q` is the specific humidity

    Then :math:`q` is computed from :math:`e` using :func:`specific_humidity_from_vapour_pressure`.

    """
    e = r * saturation_vapour_pressure(t) / 100.0
    return specific_humidity_from_vapour_pressure(e, p)


def dewpoint_from_relative_humidity(t, r):
    r"""Compute the dewpoint temperature from relative humidity.

    Parameters
    ----------
    t: ndarray
        Temperature (K)
    r: ndarray
        Relative humidity (%)

    Returns
    -------
    ndarray
        Dewpoint temperature (K). For zero ``r`` values returns np.nan.


    The computation starts with determining the the saturation vapour pressure over
    water at the dewpoint temperature:

    .. math::

        e_{wsat}(td) = \frac{r\; e_{wsat}(t)}{100}

    where:

    * :math:`e_{wsat}` is the :func:`saturation_vapour_pressure` over water
    * :math:`td` is the dewpoint.

    Then :math:`td` is computed from :math:`e_{wsat}(td)` by inverting the
    equations used in :func:`saturation_vapour_pressure`.

    """
    es = saturation_vapour_pressure(t, phase="water") * r / 100.0
    return temperature_from_saturation_vapour_pressure(es)


def dewpoint_from_specific_humidity(q, p):
    r"""Compute the dewpoint temperature from specific humidity.

    Parameters
    ----------
    q: ndarray
        Specific humidity (kg/kg)
    p: ndarray
        Pressure (Pa)

    Returns
    -------
    ndarray
        Dewpoint temperature (K). For zero ``q`` values returns np.nan.


    The computation starts with determining the the saturation vapour pressure over
    water at the dewpoint temperature:

    .. math::

        e_{wsat}(td) = e(q, p)

    where:

        * :math:`e` is the vapour pressure (see :func:`vapour_pressure_from_specific_humidity`)
        * :math:`e_{wsat}` is the :func:`saturation_vapour_pressure` over water
        * :math:`td` is the dewpoint

    Then :math:`td` is computed from :math:`e_{wsat}(td)` by inverting the equations
    used in :func:`saturation_vapour_pressure`.

    """
    return temperature_from_saturation_vapour_pressure(vapour_pressure_from_specific_humidity(q, p))


def virtual_temperature(t, q):
    r"""Computes the virtual temperature from temperature and specific humidity.

    Parameters
    ----------
    t: number or ndarray
        Temperature (K)s
    q: number or ndarray
        Specific humidity (kg/kg)

    Returns
    -------
    number or ndarray
        Virtual temperature (K)


    The computation is based on the following formula [Wallace2006]_:

    .. math::

        t_{v} = t (1 + \frac{1 - \epsilon}{\epsilon} q)

    with :math:`\epsilon = R_{d}/R_{v}` (see :data:`earthkit.meteo.constants.epsilon`).

    """
    c1 = (1.0 - constants.epsilon) / constants.epsilon
    return t * (1.0 + c1 * q)


def virtual_potential_temperature(t, q, p):
    r"""Computes the virtual potential temperature from temperature and specific humidity.

    Parameters
    ----------
    t: number or ndarray
        Temperature (K)
    q: number or ndarray
        Specific humidity (kg/kg)
    p: number or ndarray
        Pressure (Pa)

    Returns
    -------
    number or ndarray
        Virtual potential temperature (K)


    The computation is based on the following formula:

    .. math::

        \Theta_{v} = \theta (1 + \frac{1 - \epsilon}{\epsilon} q)

    where:

        * :math:`\Theta` is the :func:`potential_temperature`
        * :math:`\epsilon = R_{d}/R_{v}` (see :data:`earthkit.meteo.constants.epsilon`).

    """
    c1 = (1.0 - constants.epsilon) / constants.epsilon
    return potential_temperature(t, p) * (1.0 + c1 * q)


def potential_temperature(t, p):
    r"""Computes the potential temperature.

    Parameters
    ----------
    t: number or ndarray
        Temperature (K)
    p: number or ndarray
        Pressure (Pa)

    Returns
    -------
    number or ndarray
        Potential temperature (K)


    The computation is based on the following formula [Wallace2006]_:

    .. math::

       \theta = t (\frac{10^{5}}{p})^{\kappa}

    with :math:`\kappa = R_{d}/c_{pd}` (see :data:`earthkit.meteo.constants.kappa`).

    """
    return t * np.power(constants.p0 / p, constants.kappa)


def temperature_from_potential_temperature(th, p):
    r"""Computes the temperature from potential temperature.

    Parameters
    ----------
    th: number or ndarray
        Potential temperature (K)
    p: number or ndarray
        Pressure (Pa)

    Returns
    -------
    number or ndarray
        Temperature (K)


    The computation is based on the following formula:

    .. math::

       t = \theta (\frac{p}{10^{5}})^{\kappa}

    with :math:`\kappa = R_{d}/c_{pd}` (see :data:`earthkit.meteo.constants.kappa`).

    """
    return th * np.power(p / constants.p0, constants.kappa)


def pressure_on_dry_adiabat(t, t_def, p_def):
    r"""Computes the pressure on a dry adiabat.

    Parameters
    ----------
    t: number or ndarray
        Temperature on the dry adiabat (K)
    t_def: number or ndarray
        Temperature defining the dry adiabat (K)
    p_def: number or ndarray
        Pressure defining the dry adiabat (Pa)

    Returns
    -------
    number or ndarray
        Pressure on the dry adiabat (Pa)


    The computation is based on the following formula:

    .. math::

       p = p_{def} (\frac{t}{t_{def}})^{\frac{1}{\kappa}}

    with :math:`\kappa =  R_{d}/c_{pd}` (see :data:`earthkit.meteo.constants.kappa`).

    """
    return p_def * np.power(t / t_def, 1 / constants.kappa)


def temperature_on_dry_adiabat(p, t_def, p_def):
    r"""Computes the temperature on a dry adiabat.

    Parameters
    ----------
    p: number or ndarray
        Pressure on the dry adiabat (Pa)
    t_def: number or ndarray
        Temperature defining the dry adiabat (K)
    p_def: number or ndarray
        Pressure defining the dry adiabat (Pa)

    Returns
    -------
    number or ndarray
        Temperature on the dry adiabat (K)


    The computation is based on the following formula:

    .. math::

       t = t_{def} (\frac{p}{p_{def}})^{\kappa}

    with :math:`\kappa =  R_{d}/c_{pd}` (see :data:`earthkit.meteo.constants.kappa`).

    """
    return t_def * np.power(p / p_def, constants.kappa)


def lcl_temperature(t, td, method="davies"):
    r"""Computes the Lifting Condenstaion Level (LCL) temperature from dewpoint.

    Parameters
    ----------
    t: number or ndarray
        Temperature at the start level (K)
    td: number or ndarray
        Dewpoint at the start level (K)
    method: str, optional
        The computation method: "davies" or "bolton".

    Returns
    -------
    number or ndarray
        Temperature of the LCL (K)


    The actual computation is based on the ``method``:

    * "davies": the formula by [DaviesJones1983]_ is used (it is also used by the IFS model):

        .. math::

            t_{LCL} =
            td - (0.212 + 1.571\times 10^{-3} (td - t_{0}) - 4.36\times 10^{-4} (t - t_{0})) (t - td)

      where :math:`t_{0}` is the triple point of water (see :data:`earthkit.meteo.constants.T0`).

    * "bolton": the formula by [Bolton1980]_ is used:

        .. math::

            t_{LCL} = 56.0 +  \frac{1}{\frac{1}{td - 56} + \frac{log(\frac{t}{td})}{800}}

    """
    # Davies-Jones formula
    if method == "davies":
        t_lcl = td - (0.212 + 1.571e-3 * (td - constants.T0) - 4.36e-4 * (t - constants.T0)) * (t - td)
        return t_lcl
    # Bolton formula
    elif method == "bolton":
        return 56.0 + 1 / (1 / (td - 56) + np.log(t / td) / 800)
    else:
        raise ValueError(f"lcl_temperature: invalid method={method} specified!")


def lcl(t, td, p, method="davies"):
    r"""Computes the temperature and pressure of the Lifting Condenstaion Level (LCL) from dewpoint.

    Parameters
    ----------
    t: number or ndarray
        Temperature at the start level (K)
    td: number or ndarray
        Dewpoint at the start level (K)
    p: number or ndarray
        Pressure at the start level (Pa)
        method: str
    method: str, optional
        The computation method: "davies" or "bolton".

    Returns
    -------
    number or ndarray
        Temperature of the LCL (K)
    number or ndarray
        Pressure of the LCL (Pa)


    The LCL temperature is determined by :func:`lcl_temperature` with the given ``method``
    and the pressure is computed with :math:`t_{LCL}` using :func:`pressure_on_dry_adiabat`.

    """
    t_lcl = lcl_temperature(t, td, method=method)
    p_lcl = pressure_on_dry_adiabat(t_lcl, t, p)
    return t_lcl, p_lcl


class _ThermoState:
    def __init__(self, t=None, td=None, q=None, w=None, p=None):
        self.t = t
        self.td = td
        self.q = q
        self.w = w
        self.p = p
        self.e = None
        self.es = None
        self.ws = None
        self.qs = None


class _EptComp:
    CM = {}
    c_lambda = 1.0 / constants.kappa

    @staticmethod
    def make(method):
        return _EptComp.CM[method]()

    def is_mixing_ratio_based(self):
        return True

    def compute_ept(self, t=None, td=None, q=None, p=None):
        if td is None and q is None:
            raise ValueError("ept: either td or q must have a valid value!")

        # compute dewpoint since all the methods require it
        if td is None:
            td = dewpoint_from_specific_humidity(q, p)

        ths = _ThermoState(t=t, td=td, q=q, p=p)
        return self._ept(ths)

    def compute_ept_sat(self, t, p):
        ths = _ThermoState(t=t, p=p)
        return self._th_sat(ths) * np.exp(self._G_sat(ths))

    def compute_wbpt(self, ept):
        t0 = 273.16
        x = ept / t0
        a = [7.101574, -20.68208, 16.11182, 2.574631, -5.205688]
        b = [1.0, -3.552497, 3.781782, -0.6899655, -0.5929340]
        return ept - np.exp(np.polynomial.polynomial.polyval(x, a) / np.polynomial.polynomial.polyval(x, b))

    def compute_t_on_ma_stipanuk(self, ept, p):
        if isinstance(p, np.ndarray):
            t = np.full(p.shape, constants.T0 - 20)
        elif isinstance(ept, np.ndarray):
            t = np.full(ept.shape, constants.T0 - 20)
        else:
            t = constants.T0 - 20
        max_iter = 12
        dt = 120.0
        for _ in range(max_iter):
            ths = _ThermoState(t=t, p=p)
            dt /= 2.0
            t += np.sign(ept * np.exp(self._G_sat(ths, scale=-1.0)) - self._th_sat(ths)) * dt
        # ths.t = t
        # return ept - self._th_sat(ths) * np.exp(self._G_sat(ths))
        return t

    def compute_t_on_ma_davies(self, ept, p):
        def _k1(pp):
            """Function k1 in the article."""
            a = [-53.737, 137.81, -38.5]
            return np.polynomial.polynomial.polyval(pp, a)

        def _k2(pp):
            """Function k2 in the article."""
            a = [-0.384, 56.831, -4.392]
            return np.polynomial.polynomial.polyval(pp, a)

        def _D(p):
            """Function D in the article."""
            return 1.0 / (0.1859e-5 * p + 0.6512)

        max_iter = 1
        A = 2675
        t0 = 273.16

        if not isinstance(p, np.ndarray):
            p = np.full(ept.shape, p)

        tw = ept.copy()
        pp = np.power(p / constants.p0, constants.kappa)
        te = ept * pp
        c_te = np.power(t0 / te, _EptComp.c_lambda)

        # initial guess
        mask = c_te > _D(p)
        if np.any(mask):
            es = saturation_vapour_pressure(te[mask])
            ws = mixing_ratio_from_vapour_pressure(es, p[mask])
            d_es = saturation_vapour_pressure_slope(te[mask])
            tw[mask] = te[mask] - t0 - (A * ws) / (1 + A * ws * d_es / es)

        mask = (1 <= c_te) & (c_te <= _D(p))
        tw[mask] = _k1(pp[mask]) - _k2(pp[mask]) * c_te[mask]

        mask = (0.4 <= c_te) & (c_te < 1)
        tw[mask] = (_k1(pp[mask]) - 1.21) - (_k2(pp[mask]) - 1.21) * c_te[mask]

        mask = c_te < 0.4
        tw[mask] = (_k1(pp[mask]) - 2.66) - (_k2(pp[mask]) - 1.21) * c_te[mask] + 0.58 / c_te[mask]
        # tw has to be converted to Kelvin
        tw = celsius_to_kelvin(tw)

        # np.place(tw, tw > 362.16, 362.1)
        # print(f"ept={ept}")
        # print(f"tw={tw}")

        for i in range(max_iter):
            ths = _ThermoState(t=tw, p=p)
            ths.c_tw = np.power(t0 / ths.t, _EptComp.c_lambda)
            ths.es = saturation_vapour_pressure(ths.t)
            if self.is_mixing_ratio_based():
                ths.ws = mixing_ratio_from_vapour_pressure(ths.es, ths.p)
            else:
                ths.qs = specific_humidity_from_vapour_pressure(ths.es, ths.p)
            f_val = self._f(ths)
            # print(f"{i}")
            # print(f" p={p}")
            # print(f" t={ths.t}")
            # print(f" f_val={f_val}")
            # print(f" f_val_cte={f_val - c_te}")
            # print(f" d_lnf={self._d_lnf(ths)}")
            # print(tw[mask].shape)
            # print(f_val.shape)
            tw -= (f_val - c_te) / (f_val * self._d_lnf(ths))
            # print(f"tw={tw}")

        # when ept is derived with the Bolton methods the iteration breaks down for extremeley
        # hot and humid conditions (roughly about t > 50C and r > 95%) and results in negative
        # tw values!
        np.place(tw, tw <= 0, np.nan)

        # ths = _ThermoState(t=tw, p=p)
        # return ept - self._th_sat(ths) * np.exp(self._G_sat(ths))
        return tw


class _EptCompIfs(_EptComp):
    def __init__(self):
        self.K0 = constants.Lv / constants.c_pd

    def is_mixing_ratio_based(self):
        return False

    def _ept(self, ths):
        th = potential_temperature(ths.t, ths.p)
        t_lcl = lcl_temperature(ths.t, ths.td, method="davies")
        if ths.q is None:
            ths.q = specific_humidity_from_dewpoint(ths.td, ths.p)
        return th * np.exp(self.K0 * ths.q / t_lcl)

    def _th_sat(self, ths):
        return potential_temperature(ths.t, ths.p)

    def _G_sat(self, ths, scale=1.0):
        qs = saturation_specific_humidity(ths.t, ths.p)
        return (scale * self.K0) * qs / ths.t

    def _d_G_sat(self, ths):
        if ths.qs is None:
            ths.qs = saturation_specific_humidity(ths.t, ths.p)
        return (
            -self.K0 * ths.qs / (ths.t**2)
            + self.K0 * saturation_specific_humidity_slope(ths.t, ths.p) / ths.t
        )

    def _f(self, ths):
        return ths.c_tw * np.exp(self._G_sat(ths, scale=-self.c_lambda))

    def _d_lnf(self, ths):
        return -self.c_lambda * (1 / ths.t + self._d_G_sat(ths))


class _EptCompBolton35(_EptComp):
    def __init__(self):
        self.K0 = 2675.0
        self.K3 = 0.28

    def _ept(self, ths):
        t_lcl = lcl_temperature(ths.t, ths.td, method="bolton")
        if ths.q is None:
            w = mixing_ratio_from_dewpoint(ths.td, ths.p)
        else:
            w = mixing_ratio_from_specific_humidity(ths.q)
        th = ths.t * np.power(constants.p0 / ths.p, constants.kappa * (1 - self.K3 * w))
        return th * np.exp(self.K0 * w / t_lcl)

    def _th_sat(self, ths):
        if ths.ws is None:
            ths.ws = saturation_mixing_ratio(ths.t, ths.p)
        return ths.t * np.power(constants.p0 / ths.p, constants.kappa * (1 - self.K3 * ths.ws))

    def _G_sat(self, ths, scale=1.0):
        if ths.ws is None:
            ths.ws = saturation_mixing_ratio(ths.t, ths.p)
        return (scale * self.K0) * ths.ws / ths.t

    def _d_G_sat(self, ths):
        return (
            -self.K0 * ths.ws / np.square(ths.t)
            + self.K0 * saturation_mixing_ratio_slope(ths.t, ths.p) / ths.t
        )

    def _f(self, ths):
        # print(f" c_tw={ths.c_tw}")
        # print(f" es_frac={ths.es / ths.p}")
        # print(f" exp={self._G_sat(ths, scale=-self.c_lambda)}")
        return (
            ths.c_tw
            * np.power(ths.p / constants.p0, self.K3 * ths.ws)
            * np.exp(self._G_sat(ths, scale=-self.c_lambda))
        )

    def _d_lnf(self, ths):
        return -self.c_lambda * (
            1 / ths.t
            + self.K3 * np.log(ths.p / constants.p0) * saturation_vapour_pressure_slope(ths.t)
            + self._d_G_sat(ths)
        )


class _EptCompBolton39(_EptComp):
    def __init__(self):
        # Comment on the Bolton formulas. The constants used by Bolton to
        # derive the formulas differ from the ones used by earthkit.meteo E.g.
        #           Bolton   earthkit.meteo
        #  Rd       287.04   287.0597
        #  cpd      1005.7   1004.79
        #  kappa    0.2854   0.285691
        #  epsilon  0.6220   0.621981

        self.K0 = 3036.0
        self.K1 = 1.78
        self.K2 = 0.448
        self.K4 = 0.28

    def _ept(self, ths):
        t_lcl = lcl_temperature(ths.t, ths.td, method="bolton")
        if ths.q is None:
            w = mixing_ratio_from_dewpoint(ths.td, ths.p)
        else:
            w = mixing_ratio_from_specific_humidity(ths.q)

        e = vapour_pressure_from_mixing_ratio(w, ths.p)
        th = potential_temperature(ths.t, ths.p - e) * np.power(ths.t / t_lcl, self.K4 * w)
        return th * np.exp((self.K0 / t_lcl - self.K1) * w * (1.0 + self.K2 * w))

    def _th_sat(self, ths):
        if ths.es is None:
            ths.es = saturation_vapour_pressure(ths.t)
            ths.es[ths.p - ths.es < 1e-4] = np.nan
        return potential_temperature(ths.t, ths.p - ths.es)

    def _G_sat(self, ths, scale=1.0):
        if ths.es is None:
            ths.es = saturation_vapour_pressure(ths.t)
            ths.es[ths.p - ths.es < 1e-4] = np.nan
        # print(f" es={ths.es}")
        ws = mixing_ratio_from_vapour_pressure(ths.es, ths.p)
        # print(f" ws={ws}")
        return ((scale * self.K0) / ths.t - (scale * self.K1)) * ws * (1.0 + self.K2 * ws)

    def _d_G_sat(self, ths):
        # print(f" d_ws={saturation_mixing_ratio_slope(ths.t, ths.p)}")
        return -self.K0 * (ths.ws + self.K2 * np.square(ths.ws)) / (np.square(ths.t)) + (
            self.K0 / ths.t - self.K1
        ) * (1 + (2 * self.K2) * ths.ws) * saturation_mixing_ratio_slope(ths.t, ths.p)

    def _f(self, ths):
        # print(f" c_tw={ths.c_tw}")
        # print(f" es_frac={ths.es / ths.p}")
        # print(f" exp={self._G_sat(ths, scale=-self.c_lambda)}")
        return ths.c_tw * (1 - ths.es / ths.p) * np.exp(self._G_sat(ths, scale=-self.c_lambda))

    def _d_lnf(self, ths):
        return -self.c_lambda * (
            1 / ths.t
            + constants.kappa * saturation_vapour_pressure_slope(ths.t) / (ths.p - ths.es)
            + self._d_G_sat(ths)
        )


_EptComp.CM = {
    "ifs": _EptCompIfs,
    "bolton35": _EptCompBolton35,
    "bolton39": _EptCompBolton39,
}


def ept_from_dewpoint(t, td, p, method="ifs"):
    r"""Computes the equivalent potential temperature from dewpoint.

    Parameters
    ----------
    t: number or ndarray
        Temperature (K)
    td: number or ndarray
        Dewpoint (K)
    p: number or ndarray
        Pressure (Pa)
    method: str, optional
        Specifies the computation method. The possible values are: "ifs", "bolton35", "bolton39".

    Returns
    -------
    number or ndarray
        Equivalent potential temperature (K)


    The actual computation is based on the value of ``method``:

    * "ifs": the formula from the IFS model [IFS-CY47R3-PhysicalProcesses]_ (Chapter 6.11) is used:

        .. math::

            \Theta_{e} = \Theta\; exp(\frac{L_{v}\; q}{c_{pd}\; t_{LCL}})

    * "bolton35": Eq (35) from [Bolton1980]_ is used:


        .. math::

            \Theta_{e} = \Theta (\frac{10^{5}}{p})^{\kappa 0.28 w} exp(\frac{2675 w}{t_{LCL}})

    * "bolton39": Eq (39) from [Bolton1980]_ is used:

        .. math::

            \Theta_{e} =
            t (\frac{10^{5}}{p-e})^{\kappa} (\frac{t}{t_{LCL}})^{0.28 w} exp[(\frac{3036}{t_{LCL}} -
            1.78)w(1+0.448\; w)]

    where:

        * :math:`\Theta` is the :func:`potential_temperature`
        * :math:`t_{LCL}` is the temperature at the Lifting Condestation Level computed
          with :func:`lcl_temperature` using option:

            * method="davis" when ``method`` is "ifs"
            * method="bolton" when ``method`` is "bolton35" or "bolton39"
        * :math:`q` is the specific humidity computed with :func:`specific_humidity_from_dewpoint`
        * :math:`w`: is the mixing ratio computed with :func:`mixing_ratio_from_dewpoint`
        * :math:`e` is the vapour pressure computed with :func:`vapour_pressure_from_mixing_ratio`
        * :math:`L_{v}`: is the latent heat of vaporisation
          (see :data:`earthkit.meteo.constants.Lv`)
        * :math:`c_{pd}` is the specific heat of dry air on constant pressure
          (see :data:`earthkit.meteo.constants.c_pd`)
        * :math:`\kappa = R_{d}/c_{pd}` (see :data:`earthkit.meteo.constants.kappa`)

    """
    return _EptComp.make(method).compute_ept(t=t, td=td, p=p)


def ept_from_specific_humidity(t, q, p, method="ifs"):
    r"""Computes the equivalent potential temperature from specific humidity.

    Parameters
    ----------
    t: number or ndarray
        Temperature (K)
    q: number or ndarray
        Specific humidity (kg/kg)
    p: number or ndarray
        Pressure (Pa)
    method: str, optional
        Specifies the computation method. The possible values are: "ifs",
        "bolton35", "bolton39. See :func:`ept_from_dewpoint` for details.

    Returns
    -------
    number or ndarray
        Equivalent potential temperature (K)


    The computations are the same as in :func:`ept_from_dewpoint`
    (the dewpoint is computed from q with :func:`dewpoint_from_specific_humidity`).

    """
    return _EptComp.make(method).compute_ept(t=t, q=q, p=p)


def saturation_ept(t, p, method="ifs"):
    r"""Computes the saturation equivalent potential temperature.

    Parameters
    ----------
    t: number or ndarray
        Temperature (K)
    p: number or ndarray
        Pressure (Pa)
    method: str, optional
        Specifies the computation method. The possible values are: "ifs", "bolton35", "bolton39".

    Returns
    -------
    number or ndarray
        Saturation equivalent potential temperature (K)


    The actual computation is based on the ``method``:

    * "ifs": The formula is based on the equivalent potential temperature definition used
       in the IFS model [IFS-CY47R3-PhysicalProcesses]_ (see Chapter 6.11) :

        .. math::

            \Theta_{esat} = \Theta\; exp(\frac{L_{v}\; q_{sat}}{c_{pd}\; t})

    * "bolton35": Eq (35) from [Bolton1980]_ is used:

        .. math::

            \Theta_{e} = \Theta (\frac{10^{5}}{p})^{\kappa 0.28 w_{sat}}\; exp(\frac{2675\; w_{sat}}{t})

    * "bolton39": Eq (39) from [Bolton1980]_ is used:

        .. math::

            \Theta_{e} =
            t (\frac{10^{5}}{p-e_{sat}})^{\kappa} exp[(\frac{3036}{t} - 1.78)w_{sat}(1+0.448\; w_{sat})]

    where:

        * :math:`\Theta` is the :func:`potential_temperature`
        * :math:`e_{sat}` is the :func:`saturation_vapor_pressure`
        * :math:`q_{sat}` is the :func:`saturation_specific_humidity`
        * :math:`w_{sat}` is the :func:`saturation_mixing_ratio`
        * :math:`L_{v}` is the specific latent heat of vaporization (see :data:`earthkit.meteo.constants.Lv`)
        * :math:`c_{pd}` is the specific heat of dry air on constant pressure
          (see :data:`earthkit.meteo.constants.c_pd`)

    """
    return _EptComp.make(method).compute_ept_sat(t, p)


def temperature_on_moist_adiabat(ept, p, ept_method="ifs", t_method="bisect"):
    r"""Computes the temperature on a moist adiabat (pseudoadiabat)

    Parameters
    ----------
    ept: number or ndarray
        Equivalent potential temperature defining the moist adiabat (K)
    p: number or ndarray
        Pressure on the moist adiabat (Pa)
    ept_method: str, optional
        Specifies the computation method that was used to compute ``ept``. The possible
        values are: "ifs", "bolton35", "bolton39".
        (See :func:`ept_from_dewpoint` for details.)
    t_method: str, optional
        Specifies the iteration method along the moist adiabat to find the temperature
        for the given ``p`` pressure. The possible values are as follows:

        * "bisect": a bisection method is used as defined in [Stipanuk1973]_
        * "newton": Newtons's method is used as defined by Eq (2.6) in [DaviesJones2008]_.
          For extremely hot and humid conditions (``ept`` > 800 K) depending on
          ``ept_method`` the computation might not be carried out
          and np.nan will be returned.


    Returns
    -------
    number or ndarray
        Temperature on the moist adiabat (K). For values where the computation cannot
        be carried out np.nan is returned.

    """
    cm = _EptComp.make(ept_method)
    if t_method == "bisect":
        return cm.compute_t_on_ma_stipanuk(ept, p)
    elif t_method == "newton":
        return cm.compute_t_on_ma_davies(ept, p)
    else:
        raise ValueError(f"temperature_on_moist_adiabat: invalid t_method={t_method} specified!")


def wet_bulb_temperature_from_dewpoint(t, td, p, ept_method="ifs", t_method="bisect"):
    r"""Computes the pseudo adiabatic wet bulb temperature from dewpoint.

    Parameters
    ----------
    t: number or ndarray
        Temperature (K)
    td: number or ndarray
        Dewpoint (K)
    p: number or ndarray
        Pressure (Pa)
    ept_method: str, optional
        Specifies the computation method for the equivalent potential temperature.
        The possible values are: "ifs", "bolton35", "bolton39".
        (See :func:`ept_from_dewpoint` for details.)
    t_method: str, optional
        Specifies the method to find the temperature along the moist adiabat defined
        by the equivalent potential temperature. The possible values are as follows:

        * "bisect": :func:`temperature_on_moist_adiabat` with ``t_method`` = "bisect" is used
        * "newton": :func:`temperature_on_moist_adiabat` with ``t_method`` = "newton" is used

    Returns
    -------
    number or ndarray
        Wet bulb temperature (K)


    The computation is based on Normand's rule [Wallace2006]_ (Chapter 3.5.6):

    * first the equivalent potential temperature is computed with the given
    ``ept_method`` (using :func:`ept_from_dewpoint`). This defines the moist adiabat.
    * then the wet bulb potential temperature is determined as the temperature at
      pressure ``p`` on the moist adiabat with the given ``t_method``.

    """
    ept = ept_from_dewpoint(t, td, p, method=ept_method)
    return temperature_on_moist_adiabat(ept, p, ept_method=ept_method, t_method=t_method)


def wet_bulb_temperature_from_specific_humidity(t, q, p, ept_method="ifs", t_method="bisect"):
    r"""Computes the pseudo adiabatic wet bulb temperature from specific humidity.

    Parameters
    ----------
    t: number or ndarray
        Temperature (K)
    q: number or ndarray
        Specific humidity (kg/kg)
    p: number or ndarray
        Pressure (Pa)
    ept_method: str, optional
        Specifies the computation method for the equivalent potential temperature.
        The possible values are: "ifs", "bolton35", "bolton39".
        (See :func:`ept_from_dewpoint` for details.)
    t_method: str, optional
        Specifies the method to find the temperature along the moist adiabat
        defined by the equivalent potential temperature. The possible values are
        as follows:

        * "bisect": :func:`temperature_on_moist_adiabat` with ``t_method`` = "bisect" is used
        * "newton": :func:`temperature_on_moist_adiabat` with ``t_method`` = "newton" is used

    Returns
    -------
    number or ndarray
        Wet bulb temperature (K)


    The computation is based on Normand's rule [Wallace2006]_ (Chapter 3.5.6):

    * first the equivalent potential temperature is computed with the given
      ``ept_method`` (using :func:`ept_from_dewpoint`). This defines the moist adiabat.
    * then the wet bulb potential temperature is determined as the temperature at
      pressure ``p`` on the moist adiabat with the given ``t_method``.

    """
    ept = ept_from_specific_humidity(t, q, p, method=ept_method)
    return temperature_on_moist_adiabat(ept, p, ept_method=ept_method, t_method=t_method)


def wet_bulb_potential_temperature_from_dewpoint(t, td, p, ept_method="ifs", t_method="direct"):
    r"""Computes the pseudo adiabatic wet bulb potential temperature from dewpoint.

    Parameters
    ----------
    t: number or ndarray
        Temperature (K)
    td: number or ndarray
        Dewpoint (K)
    p: number or ndarray
        Pressure (Pa)
    ept_method: str, optional
        Specifies the computation method for the equivalent potential temperature.
        The possible values are: "ifs", "bolton35", "bolton39".
        (See :func:`ept_from_dewpoint` for details.)
    t_method: str, optional
        Specifies the method to find the temperature along the moist adiabat defined
        by the equivalent potential temperature. The possible values are as follows:

        * "direct": the rational formula defined by Eq (3.8) in [DaviesJones2008]_ is used
        * "bisect": :func:`temperature_on_moist_adiabat` with ``t_method`` = "bisect" is used
        * "newton": :func:`temperature_on_moist_adiabat` with ``t_method`` = "newton" is used

    Returns
    -------
    number or ndarray
        Wet bulb potential temperature (K)


    The computation is based on Normand's rule [Wallace2006]_ (Chapter 3.5.6):

    * first the equivalent potential temperature is computed with the given
      ``ept_method`` (using :func:`ept_from_dewpoint`). This defines the moist adiabat.
    * then the wet bulb potential temperature is determined as the temperature at
      pressure :math:`10^{5}` Pa on the moist adiabat with the given ``t_method``.

    """
    ept = ept_from_dewpoint(t, td, p, method=ept_method)
    if t_method == "direct":
        return _EptComp.make(ept_method).compute_wbpt(ept)
    else:
        return temperature_on_moist_adiabat(ept, constants.p0, ept_method=ept_method, t_method=t_method)


def wet_bulb_potential_temperature_from_specific_humidity(t, q, p, ept_method="ifs", t_method="direct"):
    r"""Computes the pseudo adiabatic wet bulb potential temperature from specific humidity.

    Parameters
    ----------
    t: number or ndarray
        Temperature (K)
    q: number or ndarray
        Specific humidity (kg/kg)
    p: number or ndarray
        Pressure (Pa)
    ept_method: str, optional
        Specifies the computation method for the equivalent potential temperature.
        The possible values are: "ifs", "bolton35", "bolton39".
        (See :func:`ept_from_dewpoint` for details.)
    t_method: str, optional
        Specifies the method to find the temperature along the moist adiabat
        defined by the equivalent potential temperature. The possible values are as follows:

        * "direct": the rational formula defined by Eq (3.8) in [DaviesJones2008]_ is used
        * "bisect": :func:`temperature_on_moist_adiabat` with ``t_method`` = "bisect" is used
        * "newton": :func:`temperature_on_moist_adiabat` with ``t_method`` = "newton" is used

    Returns
    -------
    number or ndarray
        Wet bulb potential temperature (K)


    The computations are the same as in
    :func:`wet_bulb_potential_temperature_from_dewpoint`
    (the dewpoint is computed from q with :func:`dewpoint_from_specific_humidity`).

    """
    ept = ept_from_specific_humidity(t, q, p, method=ept_method)
    if t_method == "direct":
        return _EptComp.make(ept_method).compute_wbpt(ept)
    else:
        return temperature_on_moist_adiabat(ept, constants.p0, ept_method=ept_method, t_method=t_method)
