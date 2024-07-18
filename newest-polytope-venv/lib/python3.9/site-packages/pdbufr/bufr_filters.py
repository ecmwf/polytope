# (C) Copyright 2019- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import logging
import typing as T

import attr

LOG = logging.getLogger(__name__)


@attr.attrs(auto_attribs=True, frozen=True)
class BufrFilter:
    filter: T.Union[slice, T.Set[T.Any], T.Callable[[T.Any], bool]]

    @classmethod
    def from_user(cls, user_filter: T.Any) -> "BufrFilter":
        filter: T.Union[slice, T.Set[T.Any], T.Callable[[T.Any], bool]]

        if isinstance(user_filter, slice):
            if user_filter.step is not None:
                LOG.warning(f"slice filters ignore the step {user_filter.step}")
            filter = user_filter
        elif isinstance(user_filter, T.Iterable) and not isinstance(user_filter, str):
            filter = set(user_filter)
        elif callable(user_filter):
            filter = user_filter
        else:
            filter = {user_filter}
        return cls(filter)

    def match(self, value: T.Any) -> bool:
        if value is None:
            return False
        if isinstance(self.filter, slice):
            if self.filter.start is not None and value < self.filter.start:
                return False
            elif self.filter.stop is not None and value > self.filter.stop:
                return False
        elif callable(self.filter):
            return bool(self.filter(value))
        elif value not in self.filter:
            return False
        return True

    def max(self) -> T.Any:
        if isinstance(self.filter, slice):
            return self.filter.stop
        elif callable(self.filter):
            return None
        else:
            return max(self.filter)


def is_match(
    message: T.Mapping[str, T.Any],
    compiled_filters: T.Dict[str, BufrFilter],
    required: bool = True,
) -> bool:
    matches = 0
    for k in message:
        if k not in compiled_filters:
            continue
        if compiled_filters[k].match(message[k]):
            matches += 1
        else:
            return False
    if required and matches < len(compiled_filters):
        return False
    return True
