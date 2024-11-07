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

import collections


def recursive_dict_update(original_dict, update_dict):
    """
    Recursively update a dictionary with keys and values from another dictionary.

    Parameters
    ----------
    original_dict : dict
        The original dictionary to be updated (in place).
    update_dict : dict
        The dictionary containing keys to be updated in the original dictionary.
    """
    for k, v in update_dict.items():
        if isinstance(v, collections.abc.Mapping):
            original_dict[k] = recursive_dict_update(original_dict.get(k, {}), v)
        else:
            original_dict[k] = v
    return original_dict
