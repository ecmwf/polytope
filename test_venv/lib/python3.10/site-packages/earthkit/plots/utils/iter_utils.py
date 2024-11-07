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


def symmetrical_iter(lst):
    """
    Iterate over an iterable from both ends simultaneously.

    Parameters
    ----------
    lst : iterable
        The iterable to iterate over.
    """
    mid = (len(lst) + 1) // 2
    for x, y in zip(lst[:mid], lst[::-1]):
        if x is y:
            yield x
        else:
            yield (x, y)
