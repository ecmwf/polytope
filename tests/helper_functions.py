import os

import requests
from eccodes import codes_grib_find_nearest, codes_grib_new_from_file


class HTTPError(Exception):
    def __init__(self, status_code, message):
        self.status_code = status_code
        self.message = message
        super().__init__(f"HTTPError {status_code}: {message}")


def download_test_data(nexus_url, filename):
    local_directory = "./tests/data"

    if not os.path.exists(local_directory):
        os.makedirs(local_directory)

    # Construct the full path for the local file
    local_file_path = os.path.join(local_directory, filename)

    if not os.path.exists(local_file_path):
        session = requests.Session()
        response = session.get(nexus_url)
        if response.status_code != 200:
            raise HTTPError(response.status_code, "Failed to download data.")
        # Save the downloaded data to the local file
        with open(local_file_path, "wb") as f:
            f.write(response.content)


def find_nearest_latlon(grib_file, target_lat, target_lon):

    # Open the GRIB file
    f = open(grib_file)

    # Load the GRIB messages from the file
    messages = []
    while True:
        message = codes_grib_new_from_file(f)
        if message is None:
            break
        messages.append(message)

    # Find the nearest grid points
    nearest_points = []
    for message in messages:
        nearest_index = codes_grib_find_nearest(message, target_lat, target_lon)
        nearest_points.append(nearest_index)

    # Close the GRIB file
    f.close()

    return nearest_points
