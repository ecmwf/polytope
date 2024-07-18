# (C) Copyright 2019- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import collections
import datetime
import typing as T

import attr
import eccodes  # type: ignore
import numpy as np

from pdbufr.high_level_bufr.bufr import bufr_code_is_coord

from . import bufr_filters


def rank_from_key(key: str) -> int:
    rank_text, sep, _ = key.rpartition("#")
    if sep == "#":
        return int(rank_text[1:])
    else:
        return 0


@attr.attrs(auto_attribs=True, frozen=True)
class BufrKey:
    level: int
    rank: int
    name: str

    @classmethod
    def from_level_key(cls, level: int, key: str) -> "BufrKey":
        rank_text, sep, name = key.rpartition("#")
        if sep == "#":
            rank = int(rank_text[1:])
        else:
            rank = 0
        return cls(level, rank, name)

    @property
    def key(self) -> str:
        if self.rank:
            prefix = f"#{self.rank}#"
        else:
            prefix = ""
        return prefix + self.name


@attr.attrs(auto_attribs=True)
class UncompressedBufrKey:
    current_rank: int
    ref_rank: int
    name: str

    @classmethod
    def from_key(cls, key: str) -> "UncompressedBufrKey":
        rank_text, sep, name = key.rpartition("#")
        try:
            if sep == "#":
                rank = int(rank_text[1:])
            else:
                rank = 0
        except:
            rank = 0

        return cls(rank, 0, name)

    def update_rank(self, key: str) -> None:
        self.current_rank = rank_from_key(key)

    def adjust_ref_rank(self) -> None:
        self.ref_rank = self.current_rank

    @property
    def relative_key(self) -> str:
        if self.current_rank > 0:
            rel_rank = self.current_rank - self.ref_rank
            prefix = f"#{rel_rank}#"
        else:
            prefix = ""
        return prefix + self.name


IS_KEY_COORD = {"subsetNumber": True, "operator": False}


class MessageWrapper:
    """Makes it possible to use context manager and is_coord method for all
    types of messages."""

    WRAP: T.Dict[T.Any, T.Any] = {}

    def __init__(self, d: T.Any):
        self.d = d
        self.wrap_enter = not hasattr(d, "__enter__")
        self.wrap_exit = not hasattr(d, "__exit__")
        self.wrap_is_coord = not hasattr(d, "is_coord")

    @staticmethod
    def wrap(m: T.Any) -> T.Any:
        t = type(m)
        w = MessageWrapper.WRAP.get(t, None)
        if w is None:
            w = not all(
                [
                    hasattr(m, "__enter__"),
                    hasattr(m, "__exit__"),
                    hasattr(m, "is_coord"),
                ]
            )

            MessageWrapper.WRAP[t] = w

        if not w:
            return m
        else:
            return MessageWrapper(m)

    def __enter__(self) -> T.Any:
        if self.wrap_enter:
            return self.d
        else:
            return self.d.__enter__()

    def __exit__(self, *args) -> None:  # type: ignore
        if self.wrap_exit:
            pass
        else:
            self.d.__exit__(*args)

    def __iter__(self):  # type: ignore
        return self.d.__iter__()

    def __getitem__(self, key: str) -> T.Any:
        return self.d[key]

    def __getattr__(self, fname):  # type: ignore
        def call_func(*args, **kwargs):  # type: ignore
            return getattr(self.d, fname, *args, **kwargs)

        return call_func

    def is_coord(self, key: str) -> bool:
        if self.wrap_is_coord:
            try:
                return bufr_code_is_coord(self.d[key + "->code"])
            except Exception:
                return False
        else:
            return self.d.is_coord(key)  # type: ignore


class IsCoordCache:
    """Caches if a BUFR key is a coordinate descriptor"""

    def __init__(self, message: T.Any) -> None:
        self.message = message
        self.cache: T.Dict[str, bool] = {}

    def check(self, key: str, name: str) -> bool:
        c = self.cache.get(name, None)
        if c is None:
            if name in IS_KEY_COORD:
                c = IS_KEY_COORD[name]
                self.cache[name] = c
                return c
            else:
                try:
                    c = self.message.is_coord(key)
                    self.cache[name] = c
                    return c
                except:
                    return False
        return c


def message_structure(message: T.Any) -> T.Iterator[T.Tuple[int, str]]:
    level = 0
    coords: T.Dict[str, int] = collections.OrderedDict()

    message = MessageWrapper.wrap(message)
    is_coord_cache = IsCoordCache(message)

    for key in message:
        name = key.rpartition("#")[2]

        is_coord = is_coord_cache.check(key, name)
        while is_coord and name in coords:
            _, level = coords.popitem()  # OrderedDict.popitem uses LIFO order

        yield (level, key)

        if is_coord:
            coords[name] = level
            level += 1


def filter_keys(
    message: T.Mapping[str, T.Any],
    include: T.Container[str] = (),
) -> T.Iterator[BufrKey]:
    for level, key in message_structure(message):
        bufr_key = BufrKey.from_level_key(level, key)
        if include == () or bufr_key.name in include or bufr_key.key in include:
            yield bufr_key


def make_message_uid(message: T.Mapping[str, T.Any]) -> T.Tuple[T.Optional[int], ...]:
    message_uid: T.Tuple[T.Optional[int], ...]

    message_uid = (
        message["edition"],
        message["masterTableNumber"],
        message["numberOfSubsets"],
    )

    descriptors: T.Union[int, T.List[int]] = message["unexpandedDescriptors"]
    if isinstance(descriptors, int):
        message_uid += (descriptors, None)
    else:
        message_uid += tuple(descriptors) + (None,)

    delayed_keys = (
        "delayedDescriptorReplicationFactor",
        "shortDelayedDescriptorReplicationFactor",
        "extendedDelayedDescriptorReplicationFactor",
    )

    for k in delayed_keys:
        try:
            delayed_descriptors = message[k]
        except KeyError:
            delayed_descriptors = []

        if isinstance(delayed_descriptors, int):
            message_uid += (delayed_descriptors, None)
        else:
            message_uid += tuple(delayed_descriptors) + (None,)

    return message_uid


def filter_keys_cached(
    message: T.Mapping[str, T.Any],
    cache: T.Dict[T.Tuple[T.Hashable, ...], T.List[BufrKey]],
    include: T.Iterable[str] = (),
) -> T.List[BufrKey]:
    message_uid = make_message_uid(message)
    include_uid = tuple(sorted(include))
    filtered_message_uid: T.Tuple[T.Hashable, ...] = message_uid + include_uid
    if filtered_message_uid not in cache:
        cache[filtered_message_uid] = list(filter_keys(message, include_uid))
    return cache[filtered_message_uid]


def datetime_from_bufr(
    observation: T.Dict[str, T.Any], prefix: str, datetime_keys: T.List[str]
) -> datetime.datetime:
    hours = observation.get(prefix + datetime_keys[3], 0)
    minutes = observation.get(prefix + datetime_keys[4], 0)
    seconds = observation.get(prefix + datetime_keys[5], 0.0)
    microseconds = int(seconds * 1_000_000) % 1_000_000
    datetime_list = [observation[prefix + k] for k in datetime_keys[:3]]
    datetime_list += [hours, minutes, int(seconds), microseconds]
    return datetime.datetime(*datetime_list)


def wmo_station_id_from_bufr(
    observation: T.Dict[str, T.Any], prefix: str, keys: T.List[str]
) -> int:
    block_number = int(observation[prefix + keys[0]])
    station_number = int(observation[prefix + keys[1]])
    return block_number * 1000 + station_number


def wmo_station_position_from_bufr(
    observation: T.Dict[str, T.Any], prefix: str, keys: T.List[str]
) -> T.List[float]:
    longitude = float(observation[prefix + keys[0]])  # easting (X)
    latitude = float(observation[prefix + keys[1]])  # northing (Y)
    heightOfStationGroundAboveMeanSeaLevel = float(
        observation.get(prefix + keys[2], 0.0)
    )
    return [longitude, latitude, heightOfStationGroundAboveMeanSeaLevel]


def CRS_from_bufr(
    observation: T.Dict[str, T.Any], prefix: str, keys: T.List[str]
) -> T.Optional[str]:
    bufr_CRS = int(observation.get(prefix + keys[0], 0))
    CRS_choices = {
        0: "EPSG:4326",  # WGS84
        1: "EPSG:4258",  # ETRS89
        2: "EPSG:4269",  # NAD83
        3: "EPSG:4314",  # DHDN
        4: None,  # TODO: get ellipsoid axes from descriptors 001152 and 001153
        # and create an CRS using pyproj.crs.CRS.from_cf(...) (s.below)
        5: None,  # TODO: create an CRS using pyproj.crs.CRS.from_cf(...) (s. below)
        eccodes.CODES_MISSING_LONG: "EPSG:4326",  # WGS84
    }
    """
    Note to CRS:4
    -------------
    Ellipsoidal datum using the International Reference Meridian and the International
    Reference Pole as the prime meridian and prime pole, respectively, and the origin
    of the International Terrestrial Reference System (ITRS) (see Note 2). The
    International Reference Meridian, International Reference Pole and ITRS are
    maintained by the International Earth Rotation and Reference Systems
    Service (IERS)

    (2) When Code figure 4 is used to specify a custom coordinate reference system, the ellipsoidal
        datum shall be an oblate ellipsoid of revolution, where the major axis is uniplanar with the
        equatorial plane and the minor axis traverses the prime meridian towards the prime pole.
        North corresponds to the direction from the Equator to the prime pole. East corresponds to
        the counterclockwise direction from the prime meridian as viewed from above the North Pole.
        In this case, the semi-major and semi-minor axes must be specified (e.g. by descriptors
        0 01 152 and 0 01 153).

    Note to CRS:5
    -------------
    Earth-centred, Earth-fixed (ECEF) coordinate system or Earth-centred rotational
    (ECR) system. This is a right-handed Cartesian coordinate system (X, Y, Z)
    rotating with the Earth. The origin is defined by the centre of mass of the Earth.
    (Footnote (5) of class 27 does not apply if ECEF coordinates are specified.)
    """
    return CRS_choices[bufr_CRS]


COMPUTED_KEYS = [
    (
        ["year", "month", "day", "hour", "minute", "second"],
        "data_datetime",
        datetime_from_bufr,
    ),
    (
        [
            "typicalYear",
            "typicalMonth",
            "typicalDay",
            "typicalHour",
            "typicalMinute",
            "typicalSecond",
        ],
        "typical_datetime",
        datetime_from_bufr,
    ),
    (["blockNumber", "stationNumber"], "WMO_station_id", wmo_station_id_from_bufr),
    (
        [
            "longitude",
            "latitude",
            "heightOfStationGroundAboveMeanSeaLevel",
        ],
        "geometry",  # WMO_station_position (predefined to geometry for geopandas)
        wmo_station_position_from_bufr,
    ),
    (
        [
            "coordinateReferenceSystem",
        ],
        "CRS",
        CRS_from_bufr,
    ),
]


def extract_observations(
    message: T.Mapping[str, T.Any],
    filtered_keys: T.List[BufrKey],
    filters: T.Dict[str, bufr_filters.BufrFilter] = {},
    base_observation: T.Dict[str, T.Any] = {},
) -> T.Iterator[T.Dict[str, T.Any]]:
    value_cache = {}
    try:
        is_compressed = bool(message["compressedData"])
    except KeyError:
        is_compressed = False

    if is_compressed:
        subset_count = message["numberOfSubsets"]
    else:
        subset_count = 1

    for subset in range(subset_count):
        current_observation: T.Dict[str, T.Any]
        current_observation = collections.OrderedDict(base_observation)
        current_levels: T.List[int] = [0]
        failed_match_level: T.Optional[int] = None

        for bufr_key in filtered_keys:
            level = bufr_key.level
            name = bufr_key.name

            if failed_match_level is not None and level > failed_match_level:
                continue

            # TODO: make into a function
            if all(name in current_observation for name in filters) and (
                level < current_levels[-1]
                or (level == current_levels[-1] and name in current_observation)
            ):
                # copy the content of current_items
                yield dict(current_observation)

            while len(current_observation) and (
                level < current_levels[-1]
                or (level == current_levels[-1] and name in current_observation)
            ):
                current_observation.popitem()  # OrderedDict.popitem uses LIFO order
                current_levels.pop()

            if bufr_key.key not in value_cache:
                try:
                    value_cache[bufr_key.key] = message[bufr_key.key]
                except KeyError:
                    value_cache[bufr_key.key] = None
            value = value_cache[bufr_key.key]

            # extract compressed BUFR values. They are either numpy arrays (for numeric types)
            # or lists of strings
            if (
                is_compressed
                and name != "unexpandedDescriptors"
                and isinstance(value, (np.ndarray, list))
                and len(value) == subset_count
            ):
                value = value[subset]

            if isinstance(value, float) and value == eccodes.CODES_MISSING_DOUBLE:
                value = None
            elif isinstance(value, int) and value == eccodes.CODES_MISSING_LONG:
                value = None

            if name in filters:
                if filters[name].match(value):
                    failed_match_level = None
                else:
                    failed_match_level = level
                    continue

            current_observation[name] = value
            current_levels.append(level)

        # yield the last observation
        if all(name in current_observation for name in filters):
            yield dict(current_observation)


def extract_message(
    message: T.Mapping[str, T.Any],
    filters: T.Dict[str, bufr_filters.BufrFilter] = {},
    base_observation: T.Dict[str, T.Any] = {},
    required_columns: T.Set[str] = set(),
    header_keys: T.Set[str] = set(),
) -> T.Iterator[T.Dict[str, T.Any]]:
    value_cache = {}
    try:
        is_compressed = bool(message["compressedData"])
    except KeyError:
        is_compressed = False

    if is_compressed:
        is_uncompressed = False
        subset_count = message["numberOfSubsets"]
    else:
        is_uncompressed = int(message["numberOfSubsets"]) > 1
        subset_count = 1

    # For messages with uncompressed subsets consider this:
    # - for each data key we have a single value
    # - there is no way to identify the subset from the key
    # - we cannot directly iterate over a given subset
    # - if we iterate over the keys a new subset is indicated by the
    #   appearance of the "subsetNumber" key, which contains the same array
    #   of values each time (the subset index for all the subsets). This key is
    #   generated by ecCodes and does not contain any ranking so its name is
    #   always "subsetNumber".

    uncompressed_keys: T.Dict["str", T.Any]
    uncompressed_keys = dict()
    skip_keys = {
        "unexpandedDescriptors",
        "shortDelayedDescriptorReplicationFactor",
        "delayedDescriptorReplicationFactor",
        "extendedDelayedDescriptorReplicationFactor",
        "delayedDescriptorAndDataRepetitionFactor",
        "extendedDelayedDescriptorAndDataRepetitionFactor"
        "associatedFieldSignificance",
        "dataPresentIndicator",
        "operator",
    }

    for subset in range(subset_count):
        filters_match = {k: False for k in filters.keys()}
        required_columns_match = {k: False for k in required_columns}
        current_observation: T.Dict[str, T.Any]
        current_observation = collections.OrderedDict(base_observation)

        uncompressed_subset = 0
        for key in message:
            name = key.rpartition("#")[2]
            if name in skip_keys or "->" in key:
                continue

            if is_uncompressed and key == "subsetNumber":
                if uncompressed_subset > 0:
                    if (
                        current_observation
                        and all(filters_match.values())
                        and all(required_columns_match.values())
                    ):
                        yield dict(current_observation)

                    # header keys appear only once so we need to keep the match info for them
                    for k in filters_match:
                        if k not in header_keys:
                            filters_match[k] = False

                    for k in required_columns_match:
                        if k not in header_keys:
                            required_columns_match[k] = False

                    # only keep the header keys in the result because they are the
                    # same for all the subsets
                    while (
                        len(current_observation)
                        and "subsetNumber" in current_observation
                    ):
                        # OrderedDict.popitem uses LIFO orde
                        current_observation.popitem()

                    for v in uncompressed_keys.values():
                        v.adjust_ref_rank()

                uncompressed_subset += 1

            if is_compressed:
                if key not in value_cache:
                    try:
                        value_cache[key] = message[key]
                    except KeyError:
                        value_cache[key] = None
                value = value_cache[key]
            else:
                value = message[key]

            # extract compressed BUFR values. They are either numpy arrays (for numeric types)
            # or lists of strings
            if (
                is_compressed
                and name != "unexpandedDescriptors"
                and isinstance(value, (np.ndarray, list))
                and len(value) == subset_count
            ):
                value = value[subset]

            if isinstance(value, float) and value == eccodes.CODES_MISSING_DOUBLE:
                value = None
            elif isinstance(value, int) and value == eccodes.CODES_MISSING_LONG:
                value = None

            if is_uncompressed:
                if name not in uncompressed_keys:
                    uncompressed_keys[name] = UncompressedBufrKey.from_key(key)
                else:
                    uncompressed_keys[name].update_rank(key)
                key = uncompressed_keys[name].relative_key

                # subsetNumber is an array and we need the current value
                if key == "subsetNumber":
                    value = uncompressed_subset

            if name in filters:
                if filters[name].match(value):
                    filters_match[name] = True

            if name in required_columns:
                required_columns_match[name] = True

            current_observation[key] = value

        # yield the last observation
        if (
            current_observation
            and all(filters_match.values())
            and all(required_columns_match.values())
        ):
            yield dict(current_observation)


def add_computed_keys(
    observation: T.Dict[str, T.Any],
    included_keys: T.Container[str],
    filters: T.Dict[str, bufr_filters.BufrFilter] = {},
) -> T.Dict[str, T.Any]:
    augmented_observation = observation.copy()
    for keys, computed_key, getter in COMPUTED_KEYS:
        if computed_key not in included_keys:
            continue
        computed_value = None
        try:
            computed_value = getter(observation, "", keys)
        except Exception:
            pass
        if computed_value:
            if computed_key in filters:
                if filters[computed_key].match(computed_value):
                    augmented_observation[computed_key] = computed_value
            else:
                augmented_observation[computed_key] = computed_value
    return augmented_observation


def test_computed_keys(
    observation: T.Dict[str, T.Any],
    filters: T.Dict[str, bufr_filters.BufrFilter] = {},
    prefix: str = "",
) -> bool:
    for keys, computed_key, getter in COMPUTED_KEYS:
        if computed_key in filters:
            computed_value = None
            try:
                computed_value = getter(observation, prefix, keys)
            except Exception:
                return False
            if computed_value is not None:
                if not filters[computed_key].match(computed_value):
                    return False
            else:
                return False
    return True


def stream_bufr(
    bufr_file: T.Iterable[T.MutableMapping[str, T.Any]],
    columns: T.Union[T.Sequence[str], str],
    filters: T.Mapping[str, T.Any] = {},
    required_columns: T.Union[bool, T.Iterable[str]] = True,
    prefilter_headers: bool = False,
) -> T.Iterator[T.Dict[str, T.Any]]:
    """
    Iterate over selected observations from a eccodes.BurfFile.

    :param bufr_file: the eccodes.BurfFile object
    :param columns: a list of BUFR keys to return in the DataFrame for every observation
    :param filters: a dictionary of BUFR key / filter definition to filter the observations to return
    :param required_columns: the list of BUFR keys that are required for all observations.
        ``True`` means all ``columns`` are required (default ``True``)
    :param prefilter_headers: filter the header keys before unpacking the data section (default ``False``)
    """

    if isinstance(columns, str):
        columns = (columns,)

    if required_columns is True:
        required_columns = set(columns)
    elif required_columns is False:
        required_columns = set()
    elif isinstance(required_columns, T.Iterable):
        required_columns = set(required_columns)
    else:
        raise TypeError("required_columns must be a bool or an iterable")

    filters = dict(filters)

    value_filters = {k: bufr_filters.BufrFilter.from_user(filters[k]) for k in filters}
    included_keys = set(value_filters)
    included_keys |= set(columns)
    computed_keys = []
    for keys, computed_key, _ in COMPUTED_KEYS:
        if computed_key in included_keys:
            included_keys |= set(keys)
            computed_keys.append(computed_key)

    if "count" in value_filters:
        max_count = value_filters["count"].max()
    else:
        max_count = None

    keys_cache: T.Dict[T.Tuple[T.Hashable, ...], T.List[BufrKey]] = {}
    for count, msg in enumerate(bufr_file, 1):
        # we use a context manager to automatically delete the handle of the BufrMessage.
        # We have to use a wrapper object here because a message can also be a dict
        with MessageWrapper.wrap(msg) as message:
            if "count" in value_filters and not value_filters["count"].match(count):
                continue

            if prefilter_headers:
                # test header keys for failed matches before unpacking
                if not bufr_filters.is_match(message, value_filters, required=False):
                    continue

            message["skipExtraKeyAttributes"] = 1
            message["unpack"] = 1

            filtered_keys = filter_keys_cached(message, keys_cache, included_keys)
            if "count" in included_keys:
                observation = {"count": count}
            else:
                observation = {}

            value_filters_without_computed = {
                k: v for k, v in value_filters.items() if k not in computed_keys
            }

            for observation in extract_observations(
                message,
                filtered_keys,
                value_filters_without_computed,
                observation,
            ):
                augmented_observation = add_computed_keys(
                    observation, included_keys, value_filters
                )
                data = {k: v for k, v in augmented_observation.items() if k in columns}
                if required_columns.issubset(data):
                    yield data

            # optimisation: skip decoding messages above max_count
            if max_count is not None and count >= max_count:
                break


def stream_bufr_flat(
    bufr_file: T.Iterable[T.MutableMapping[str, T.Any]],
    columns: T.Union[T.Sequence[str], str],
    filters: T.Mapping[str, T.Any] = {},
    required_columns: T.Union[bool, T.Iterable[str]] = True,
    prefilter_headers: bool = False,
    column_info: T.Any = None,
) -> T.Iterator[T.Dict[str, T.Any]]:
    if isinstance(columns, str):
        columns = (columns,)

    if not isinstance(columns, T.Sequence):
        raise TypeError("invalid columns type")
    elif len(columns) == 0 or columns[0] == "":
        columns = ("all",)
    elif len(columns) != 1:
        raise ValueError(f"when columns is an iterable it can have maximum 1 element")

    if columns[0] not in ["all", "header", "data"]:
        raise ValueError(f"columns must be all, header or data")

    add_header = columns[0] in ["all", "header"]
    add_data = columns[0] in ["all", "data"]
    if not add_header and not add_data:
        raise ValueError("either header or data must be extracted")

    if isinstance(required_columns, bool):
        required_columns = set()
    elif isinstance(required_columns, str):
        required_columns = {required_columns}
    elif isinstance(required_columns, T.Iterable):
        required_columns = set(required_columns)
    else:
        raise TypeError("required_columns must be a bool, str or an iterable")

    # compile filters
    filters = dict(filters)
    value_filters = {k: bufr_filters.BufrFilter.from_user(filters[k]) for k in filters}

    # prepare count filter
    if "count" in value_filters:
        max_count = value_filters["count"].max()
    else:
        max_count = None

    count_filter = value_filters.pop("count", None)

    # prepare computed keys
    computed_keys = [x for _, x, _ in COMPUTED_KEYS]
    value_filters_without_computed = {
        k: v for k, v in value_filters.items() if k not in computed_keys
    }

    if column_info is not None:
        column_info.first_count = 0

    for count, msg in enumerate(bufr_file, 1):
        # we use a context manager to automatically delete the handle of the BufrMessage.
        # We have to use a wrapper object here because a message can also be a dict
        with MessageWrapper.wrap(msg) as message:
            # count filter
            if count_filter is not None and not count_filter.match(count):
                continue

            message_value_filters = value_filters_without_computed
            message_required_columns = required_columns

            header_keys = set()
            if not add_header or prefilter_headers or value_filters or required_columns:
                header_keys = set(message.keys())

                if required_columns:
                    message_required_columns = required_columns - set(header_keys)

                # test header keys for failed matches before unpacking
                if prefilter_headers:
                    if not bufr_filters.is_match(
                        message, value_filters, required=False
                    ):
                        continue
                    # remove already tested filters
                    else:
                        message_value_filters = {
                            k: v
                            for k, v in value_filters.items()
                            if k not in header_keys
                        }

            message["skipExtraKeyAttributes"] = 1

            if add_data or message_value_filters or message_required_columns:
                message["unpack"] = 1

            observation: T.Dict[str, T.Any] = {}

            for observation in extract_message(
                message,
                message_value_filters,
                observation,
                message_required_columns,
                header_keys,
            ):
                if header_keys:
                    if not add_header:
                        for key in header_keys:
                            observation.pop(key, None)
                    if not add_data:
                        data_keys = set(observation.keys()) - header_keys
                        for key in data_keys:
                            observation.pop(key, None)

                if observation and test_computed_keys(
                    observation, value_filters, "#1#"
                ):
                    if column_info is not None and column_info.first_count == 0:
                        column_info.first_count = len(observation)
                    yield observation

            # optimisation: skip decoding messages above max_count
            if max_count is not None and count >= max_count:
                break
