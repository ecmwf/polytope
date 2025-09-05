import matplotlib.pyplot as plt

box_size = [10, 20, 40, 80]

quadtree_build_time = [10.954054832458496, 10.95795202255249, 10.915708065032959, 11.012521028518677]

num_vals_found = [19226, 72485, 253205, 724400]

gj_retrieve_structured_time = [0.0176, 0.021518, 0.022053, 0.051661]

gj_retrieve_unstructured_time = [0.097058, 1, 13, 128]

tot_retrieve_time_structured = [0.2735710144042969, 0.5628271102905273, 1.5192251205444336, 4.548176288604736]

tot_retrieve_time_unstructured = [0.9918620586395264, 5.218957185745239, 33.4666748046875, 210.05072903633118]


pure_poly_time_structured = [tot_retrieve_time_structured[i] - gj_retrieve_structured_time[i] for i in range(4)]
pure_poly_time_unstructured = [tot_retrieve_time_unstructured[i] - gj_retrieve_unstructured_time[i] for i in range(4)]

fig, ax = plt.subplots(1, 1)

# ax.plot(box_size, tot_retrieve_time_structured, color="b")
# ax.plot(box_size, tot_retrieve_time_unstructured, color="r")
# ax.plot(box_size, gj_retrieve_structured_time, color="b", linestyle="--")
# ax.plot(box_size, gj_retrieve_unstructured_time, color="r", linestyle="--")
# ax.set_yscale("log")

ax.plot(box_size, pure_poly_time_structured, color="b")
ax.plot(box_size, pure_poly_time_unstructured, color="r")

plt.show()
