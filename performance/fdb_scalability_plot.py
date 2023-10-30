import matplotlib.pyplot as plt

fdb_time = [7.6377081871032715 - 7.558288812637329, 73.57192325592041 - 72.99611115455627, 733.2706120014191 - 727.7059993743896, 4808.3157522678375 - 4770.814565420151]
num_extracted_points = [1986, 19226, 191543, 1267134]

# for the 1.3M points, we used 100 latitudes too...., maybe that's why it's not as linear...

# plt.xscale("log")
plt.plot(num_extracted_points, fdb_time, marker="o")
plt.xlabel("Number of extracted points")
plt.ylabel("Polytope extraction time (in s)")
plt.show()
