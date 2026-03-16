import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

naive_rectangle_data_original = [
    1281,
    465,
    1518,
    1368,
    867,
    7790,
    8855,
    4526,
    3672,
    2200,
    1120,
    7885,
    42,
    651,
    22260,
    1066,
    1155,
    288,
    6976,
    11550,
    560,
    7650,
    6786,
]
improved_polytope_data_original = [
    643,
    250,
    412,
    403,
    457,
    3994,
    4128,
    2931,
    870,
    1254,
    605,
    2116,
    23,
    285,
    3825,
    593,
    636,
    156,
    3391,
    5028,
    315,
    5204,
    2154,
]
country_list_original = [
    "Austria",
    "Belgium",
    "Croatia",
    "Denmark",
    "Estonia",
    "Finland",
    "France",
    "Germany",
    "Greece",
    "Iceland",
    "Ireland",
    "Italy",
    "Luxembourg",
    "Netherlands",
    "Norway",
    "Portugal",
    "Serbia",
    "Slovenia",
    "Spain",
    "Sweden",
    "Switzerland",
    "Turkiye",
    "UK",
]

mask = range(len(naive_rectangle_data_original))

naive_rectangle_data = [naive_rectangle_data_original[i] for i in mask]
improved_polytope_data = [improved_polytope_data_original[i] for i in mask]
country_list = [country_list_original[i] for i in mask]

normalised_improvement = [
    polytope / rectangle for polytope, rectangle in zip(improved_polytope_data, naive_rectangle_data)
]

normalised_rectangle_data = list(np.ones(len(naive_rectangle_data)))
half_improvement = [0.5 * value for value in normalised_rectangle_data]

x_range = range(len(naive_rectangle_data))

country_list = [
    "Norway",
    "Greece",
    "Croatia",
    "Italy",
    "Denmark",
    "UK",
    "Sweden",
    "Netherlands",
    "France",
    "Spain",
    "Austria",
    "Finland",
    "Estonia",
    "Slovenia",
    "Ireland",
    "Belgium",
    "Serbia",
    "Luxembourg",
    "Switzerland",
    "Portugal",
    "Iceland",
    "Germany",
    "Turkiye",
][::-1]
normalised_improvement = [
    0.17,
    0.24,
    0.27,
    0.27,
    0.29,
    0.32,
    0.44,
    0.44,
    0.47,
    0.49,
    0.50,
    0.51,
    0.53,
    0.54,
    0.54,
    0.54,
    0.55,
    0.55,
    0.56,
    0.56,
    0.57,
    0.65,
    0.68,
][::-1]
new_normalised_improvement = []
for item in normalised_improvement:
    new_normalised_improvement.append(item * 100)
freq_series = pd.Series(new_normalised_improvement)

plt.figure(figsize=(12, 8))
ax = freq_series.plot(kind="barh", color="darkorange", alpha=0.4, width=0.8)
ax.set_title("Percentage Improvement", size=24, fontweight="bold")
ax.set_xlabel("Percentage", size=12, fontweight="bold")
ax.set_yticklabels([])
plt.tick_params(left=False)
ax.set_xlim(0, 100.0)  # expand xlim to make labels easier to read

rects = ax.patches

index = 0

for rect in rects:
    x_value = rect.get_width()
    y_value = rect.get_y() + rect.get_height() / 2

    space = 8
    ha = "left"

    if x_value < 0:
        space *= -1
        ha = "right"

    label = country_list[index]
    index = index + 1

    plt.annotate(
        label,
        (x_value, y_value),
        xytext=(space, 0),
        textcoords="offset points",
        va="center",
        ha=ha,
        style="italic",
        fontweight="bold",
    )

    label2 = "{:.0f}".format(x_value) + "%"
    x_value2 = 5.85
    plt.annotate(
        label2,
        (x_value2, y_value),
        xytext=(0, 0),
        textcoords="offset points",
        va="center",
        ha=ha,
        color="black",
        fontweight="bold",
    )

plt.show()
