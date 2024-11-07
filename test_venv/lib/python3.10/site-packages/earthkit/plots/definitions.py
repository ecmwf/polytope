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

from pathlib import Path

ROOT_DIR = Path(__file__).parents[3]
DATA_DIR = Path(__file__).parents[0] / "data"
TESTS_DIR = ROOT_DIR / "tests"
GEO_DIR = DATA_DIR / "geo"
STATIC_DIR = DATA_DIR / "static"
FONTS_DIR = STATIC_DIR / "fonts"
SYMBOLS_DIR = STATIC_DIR / "symbols"
