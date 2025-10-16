import requests
from qubed import Qube

url = "https://catalogue.lumi.apps.dte.destination-earth.eu/api/v2/select/"


def change_datetime_to_str(date):
    return date.strftime("%Y%m%d")


def find_axes_from_qube(pre_path):
    response = requests.get(url, params=pre_path)
    if response.ok:
        qube_json = response.json()
    else:
        print("Error querying catalogue:", response.status_code, response.text)

    qube = Qube.from_json(qube_json)

    qube_axes = qube.axes()

    for key in qube_axes.keys():
        if key == "date":
            new_vals = []
            for val in qube_axes[key]:
                val = change_datetime_to_str(val)
                new_vals.append(val)
            qube_axes[key] = new_vals
        qube_axes[key] = list(qube_axes[key])
    return qube_axes


print(
    find_axes_from_qube(
        {"class": "d1", "dataset": "on-demand-extremes-dt", "type": "fc", "levtype": "sfc", "param": "167"}
    )
)
