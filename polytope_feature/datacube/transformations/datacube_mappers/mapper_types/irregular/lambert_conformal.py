import math

from ..irregular import IrregularGridMapper

# import numpy as np


class LambertConformalGridMapper(IrregularGridMapper):
    def __init__(self, base_axis, mapped_axes, resolution, is_spherical, nv,  nx, ny, LoVInDegrees,
                 Dx, Dy, latFirstInRadians, lonFirstInRadians, LoVInRadians, Latin1InRadians,
                 Latin2InRadians, LaDInRadians,
                 radius=None, earthMinorAxisInMetres=None, earthMajorAxisInMetres=None,
                 md5_hash=None, axis_reversed=None):
        self._mapped_axes = mapped_axes
        self._base_axis = base_axis
        self._resolution = resolution
        self._axis_reversed = False
        self.compressed_grid_axes = [self._mapped_axes[1]]
        if md5_hash is not None:
            self.md5_hash = md5_hash
        else:
            self.md5_hash = _md5_hash.get(resolution, None)

        self.is_spherical = is_spherical

        if self.is_spherical:
            self.radius = radius
        else:
            self.earthMinorAxisInMetres = earthMinorAxisInMetres
            self.earthMajorAxisInMetres = earthMajorAxisInMetres

        self.nv = nv
        self.nx = nx
        self.ny = ny
        self.LoVInDegrees = LoVInDegrees
        self.Dx = Dx
        self.Dy = Dy
        self.latFirstInRadians = latFirstInRadians
        self.lonFirstInRadians = lonFirstInRadians
        self.LoVInRadians = LoVInRadians
        self.Latin1InRadians = Latin1InRadians
        self.Latin2InRadians = Latin2InRadians
        self.LaDInRadians = LaDInRadians

        self.epsilon = 1e-10
        self.M_PI_2 = math.pi / 2
        self.M_PI = math.pi
        self.M_PI_4 = math.pi / 4

        self.rad2deg = 180 / math.pi
        self.deg2rad = math.pi / 180

    def normalise_longitude_in_degrees(self, lon):
        while lon < 0:
            lon += 360
        while lon > 360:
            lon -= 360
        return lon

    def adjust_lon_radians(self, lon):
        if lon > self.M_PI:
            lon -= 2 * self.M_PI
        if lon < -self.M_PI:
            lon += 2 * self.M_PI
        return lon

    def compute_phi(self, eccent, ts):
        max_iter = 15
        eccnth = 0.5 * eccent
        phi = self.M_PI_2 - 2 * math.atan(ts)
        for i in range(max_iter + 1):
            sinpi = math.sin(phi)
            con = eccent * sinpi
            dphi = self.M_PI_2 - 2 * math.atan(ts * (math.pow(((1-con) / (1 + con)), eccnth))) - phi
            phi += dphi
            if math.abs(dphi) <= 1e-10:
                return phi
        return 0

    def compute_m(self, eccent, sinphi, cosphi):
        con = eccent * sinphi
        return ((cosphi) / math.sqrt(1 - con * con))

    def compute_t(self, eccent, phi, sinphi):
        con = eccent * sinphi
        com = 0.5 * eccent
        con = math.pow(((1 - con) / (1 + con)), com)
        return (math.tan(0.5 * (self.M_PI_2 - phi)) / con)

    def calculate_eccentricity(self, minor, major):
        temp = minor / major
        return math.sqrt(1 - temp * temp)

    def xy2lonlat(self, radius, n, f, rho0_bare, LoVInRadians, x, y):
        x /= radius
        y /= radius
        y = rho0_bare - y
        rho = math.hypot(x, y)
        if rho != 0:
            if n < 0:
                rho = - rho
                x = -x
                y = -y
            latRadians = 2 * math.atan(math.pow(f/rho, 1/n)) - self.M_PI_2
            lonRadians = math.atan2(x, y) / n
            lonDeg = (lonRadians + LoVInRadians) * self.rad2deg
            latDeg = latRadians * self.rad2deg
        else:
            lonDeg = 0
            latDeg = (self.M_PI_2 if n > 0.0 else -self.M_PI_2) * self.rad2deg
        return (lonDeg, latDeg)

    def get_latlons_sphere(self):

        if abs(self.Latin1InRadians - self.Latin2InRadians) < 1e-09:
            n = math.sin(self.Latin1InRadians)
        else:
            num = math.log(math.cos(self.Latin1InRadians) / math.cos(self.Latin2InRadians))
            denom = math.log(math.tan(self.M_PI_4 + self.Latin2InRadians / 2.0) /
                             math.tan(self.M_PI_4 + self.Latin1InRadians / 2.0))
            n = num/denom

        f = (math.cos(self.Latin1InRadians) * math.pow(math.tan(self.M_PI_4 + self.Latin1InRadians / 2.0), n)) / n
        rho = self.radius * f * math.pow(math.tan(self.M_PI_4 + self.latFirstInRadians / 2.0), -n)
        rho0_bare = f * math.pow(math.tan(self.M_PI_4 + self.LaDInRadians / 2.0), -n)
        rho0 = self.radius * rho0_bare
        lonDiff = self.lonFirstInRadians - self.LoVInRadians

        # # Normalize longitude difference
        if lonDiff > math.pi:
            lonDiff -= 2 * math.pi
        if lonDiff < -math.pi:
            lonDiff += 2 * math.pi

        angle = n * lonDiff
        x0 = rho * math.sin(angle)
        y0 = rho0 - rho * math.cos(angle)

        # Allocate output arrays
        # lats_ = np.empty(self.nv, dtype=float)
        # lons_ = np.empty(self.nv, dtype=float)
        coords = []

        # Fill in latitude and longitude arrays
        for j in range(self.ny):
            y = y0 + j * self.Dy
            for i in range(self.nx):
                # index = i + j * self.nx
                x = x0 + i * self.Dx
                lonDeg, latDeg = self.xy2lonlat(self.radius, n, f, rho0_bare, self.LoVInRadians, x, y)
                lonDeg = self.normalise_longitude_in_degrees(lonDeg)
                # lons_[index] = lonDeg
                # lats_[index] = latDeg
                coords.append([latDeg, lonDeg])

        return coords

    def get_latlons_oblate(self):
        i = 0
        j = 0
        e = self.calculate_eccentricity(self.earthMinorAxisInMetres, self.earthMajorAxisInMetres)
        sin_po = math.sin(self.Latin1InRadians)
        cos_po = math.cos(self.Latin1InRadians)
        con = sin_po
        ms1 = self.compute_m(e, sin_po, cos_po)
        ts1 = self.compute_t(e, self.Latin1InRadians, sin_po)

        sin_po = math.sin(self.Latin2InRadians)
        cos_po = math.cos(self.Latin2InRadians)
        ms2 = self.compute_m(e, sin_po, cos_po)
        ts2 = self.compute_t(e, self.Latin2InRadians, sin_po)
        sin_po = math.sin(self.LaDInRadians)
        ts0 = self.compute_t(e, self.LaDInRadians, sin_po)

        if math.abs(self.Latin1InRadians - self.Latin2InRadians) > self.epsilon:
            ns = math.log(ms1 / ms2) / math.log(ts1 / ts2)
        else:
            ns = con

        F_cst = ms1 / (ns * math.pow(ts1, ns))
        rh = self.earthMajorAxisInMetres * F_cst * math.pow(ts0, ns)

        con = math.abs(math.abs(self.latFirstInRadians) - self.M_PI_2)

        if con > self.epsilon:
            sinphi = math.sin(self.latFirstInRadians)
            ts = self.compute_t(e, self.latFirstInRadians, sinphi)
            rh1 = self.earthMajorAxisInMetres * F_cst * math.pow(ts, ns)
        else:
            con = self.latFirstInRadians * ns
            rh1 = 0

        theta = ns * self.adjust_lon_radians(self.lonFirstInRadians - self.LoVInRadians)
        x0 = rh1 * math.sin(theta)
        y0 = rh - rh1 * math.cos(theta)
        x0 = - x0
        y0 = -y0

        coords = []

        false_easting = x0
        false_northing = y0
        for j in range(self.ny):
            y = j * self.Dy
            for i in range(self.nx):
                # index = i + j * self.nx
                x = i * self.Dx
                _x = x - false_easting
                _y = rh - y + false_northing
                rh1 = math.sqrt(_x * _x + _y * _y)
                con = 1
                if ns <= 0:
                    rh1 = -rh1
                    con = -con
                theta = 0
                if rh1 != 0:
                    theta = math.atan2((con*_x), (con*_y))
                if (rh1 != 0) or (ns > 0.0):
                    con = 1 / ns
                    ts = math.pow((rh1 / (self.earthMajorAxisInMetres * F_cst)), con)
                    latRad = self.compute_phi(e, ts)
                else:
                    latRad = - self.M_PI_2
                lonRad = self.adjust_lon_radians(theta / ns + self.LoVInRadians)
                latDeg = latRad * self.rad2deg
                lonDeg = self.normalise_longitude_in_degrees(lonRad * self.rad2deg)
                coords.append([latDeg, lonDeg])
        return coords

    def get_latlons(self):
        if self.is_spherical:
            return self.get_latlons_sphere()
        else:
            return self.get_latlons_oblate()


_md5_hash = {}
