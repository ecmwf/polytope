import matplotlib.pyplot as plt

fig, ax = plt.subplots(2)

ax[0].set_title("Slicer time")
ax[1].set_title("Total time")

number_points_2d = [144921, 289440, 519840, 807840, 1038240, 1558081, 2077201]
slicer_time_2d = [
    1675067651.994663 - 1675067650.8609018,
    1674574980.320323 - 1674574978.231524,
    1674575172.515479 - 1674575165.702562,
    1674575517.231494 - 1674575505.825341,
    1674576051.644233 - 1674576035.450634,
    1675177783.896509 - 1675177772.970182,
    1675184042.885151 - 1675184028.2198532,
]
total_time_2d = [
    95.02675199508667,
    187.3025050163269,
    339.9525718688965,
    529.4503169059753,
    684.5719878673553,
    1071.1850290298462,
    1526.7298312187195,
]


ax[0].plot(number_points_2d, slicer_time_2d, marker="D", color="blue", label="2D")
ax[1].plot(number_points_2d, total_time_2d, marker="D", color="blue")


number_points_3d = [289842, 578880, 1039680, 1615680, 2424642]
slicer_time_3d = [
    1675068450.163046 - 1675068448.550547,
    1674652185.60178 - 1674652181.473449,
    1674652571.813121 - 1674652557.9835598,
    1674654736.72457 - 1674654722.4930408,
    1675184322.065717 - 1675184305.480412,
]
total_time_3d = [247.2636013031006, 376.33102011680603, 689.4626791477203, 1083.933179140091, 1889.5270569324493]

ax[0].plot(number_points_3d, slicer_time_3d, marker="X", color="red", label="3D")
ax[1].plot(number_points_3d, total_time_3d, marker="X", color="red")

# number_points_2d_circle = [115755, 231517, 463025]
# slicer_time_2d_circle = [1675068696.658858-1675068695.987088, 1674654572.5894961-1674654570.838204,
#                           1674658501.923199-1674658498.5120351]
# total_time_2d_circle = [81.81447005271912, 151.26101303100586, 302.11202573776245]

# ax[0].plot(number_points_2d_circle, slicer_time_2d_circle, marker="s", color="green", label="2D circle")
# #plt.show()
# ax[1].plot(number_points_2d_circle, total_time_2d_circle, marker="s", color="green")

number_points_4d = [291284, 579684, 1157760, 2079360]
slicer_time_4d = [
    1675184632.061617 - 1675184632.061575,
    1675184532.024422 - 1675184527.558725,
    1675177114.85664 - 1675177106.422187,
    1674659021.241025 - 1674659003.32431,
]
total_time_4d = [197.0693700313568, 436.3116102218628, 845.9738457202911, 1471.0876429080963]

ax[0].plot(number_points_4d, slicer_time_4d, marker="s", color="orange", label="4D")
ax[1].plot(number_points_4d, total_time_4d, marker="s", color="orange")

lines_labels = [ax.get_legend_handles_labels() for ax in fig.axes]
lines, labels = [sum(lol, []) for lol in zip(*lines_labels)]
fig.legend(lines, labels, loc="lower center", bbox_to_anchor=(0.5, 0), bbox_transform=plt.gcf().transFigure)

plt.show()
