# Copyright 2021 European Centre for Medium-Range Weather Forecasts (ECMWF)
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
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation nor
# does it submit to any jurisdiction.


class Result:
    def __init__(self, request_url, output_file, append, request_manager):
        """
        This class represents a submitted Polytope request, for which a URL
        is known and pollable for status or download.

        Calling the method 'download' of this class will call, in a
        synchronous mode, the Client.download method with the known request
        URL.
        """
        self.request_url = request_url
        self.output_file = output_file
        self.append = append
        self.request_manager = request_manager

    def download(self, **kwargs):
        """
        Download data of a request result.

        :param kwargs: Additional arguments to be sent to the
        Client.download method. The argument 'request_id' is automatically
        provided by the Result class and can't be overriden. The
        'output_file' argument is also provided by the class, but can be
        overriden.
        :type kwargs: dictionary
        :returns: None
        """

        params = {**kwargs}
        params_to_filter = ["request_id", "output_file", "append"]
        filtered = {}
        for param in params_to_filter:
            if param in params:
                p = params.pop(param)
                filtered[param] = p

        return self.request_manager.download(
            request_id=self.request_url,
            output_file=filtered.get("output_file", self.output_file),
            append=filtered.get("append", self.append),
            **params
        )

    def describe(self):
        """
        Describe a request result.

        :returns: Dictionary with description items.
        """
        return self.request_manager.describe(request_id=self.request_url)
