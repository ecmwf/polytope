import os

import requests


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
