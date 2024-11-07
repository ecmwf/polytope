# Copyright 2024, European Centre for Medium Range Weather Forecasts.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


class GridSpec:
    """
    A specification of a grid used in a Source.

    Parameters
    ----------
    data : earthkit.plots.sources.Source
        The data object containing the grid metadata.
    """

    @classmethod
    def from_data(cls, data):
        """
        Identify and create a GridSpec object from the given data.

        Parameters
        ----------
        data : earthkit.plots.sources.Source
            The data object containing the grid metadata.
        """
        for kls in [HEALPix, ReducedGG]:
            for key in kls.CRITERIA:
                value = data.metadata(key, default=None)
                if isinstance(value, list) and len(value) == 1:
                    value = value[0]
                if kls.CRITERIA[key] != value:
                    break
            else:
                break
        else:
            return
        return kls(data)

    def __init__(self, data):
        self.data = data

    def to_dict(self):
        return NotImplementedError


class ReducedGG(GridSpec):
    """A reduced Gaussian grid specification."""

    CRITERIA = {"gridType": "reduced_gg"}

    def to_dict(self):
        n = self.data.metadata("N", default=None)
        if n is not None:
            if self.data.metadata("isOctahedral", default=0):
                g = f"O{n}"
            else:
                g = f"N{n}"
        return {"grid": g}


class HEALPix(GridSpec):
    """A HEALPix grid specification."""

    CRITERIA = {"gridType": "healpix"}

    def to_dict(self):
        n = self.data.metadata("Nside", default=None)
        o = self.data.metadata("orderingConvention", default=None)
        if isinstance(o, list):
            o = o[0]
            n = n[0]
        if n is not None and o is not None:
            return {"grid": f"H{n}", "ordering": o}
