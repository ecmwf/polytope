import os

import requests


def download_test_data(nexus_url, filename):
    local_directory = "./tests/data"

    if not os.path.exists(local_directory):
        os.makedirs(local_directory)

    # Construct the full path for the local file
    local_file_path = os.path.join(local_directory, filename)

    if not os.path.exists(local_file_path):
        session = requests.Session()
        response = session.get(nexus_url)
        if response.status_code == 200:
            # Save the downloaded data to the local file
            with open(local_file_path, "wb") as f:
                f.write(response.content)
