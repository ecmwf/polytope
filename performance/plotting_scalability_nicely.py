import matplotlib.pyplot as plt

number_points_box_2D = [289440, 519840, 807840, 1038240]
number_points_box_3D = [289842, 578880, 1039680]
number_points_box_4D = [291284, 579684, 1157760]


total_algo_time_box_2D = [2.4397358894348145, 4.640367269515991, 7.3496620655059814, 9.376123905181885]
total_algo_time_box_3D = [3.570450782775879, 5.600926876068115, 9.711699962615967]
total_algo_time_box_4D = [3.2922229766845703, 6.021270990371704, 10.309967041015625]


extract_algo_time_box_2D = [1.7958579063415527, 3.463357925415039, 5.5203869342803955, 7.058114051818848]
extract_algo_time_box_3D = [2.9079132080078125, 4.303113222122192, 7.371915102005005]
extract_algo_time_box_4D = [2.6364331245422363, 4.723308086395264, 7.707273006439209]


actual_slicing_time_box_2D = [6.7263681592118115e-06*201 + 289442 * 4.065339515348613e-07,
                              4.0471143154975205e-07 * 519842 + 361 * 6.2243767313206965e-06,
                              807842 * 4.014794972282536e-07 + 561 * 6.780748663175474e-06,
                              1038242 * 4.022617077703454e-07 + 721 * 6.608876560316729e-06]
actual_slicing_time_box_3D = [289844 * 3.991664481591157e-07 + 402 * 6.875621890589214e-06 + 2 * 0.00010550000000186799,
                              4.078741436080055e-07 * 578882 + 6.641791044775719e-06 * 402 + 0.0003075000000000161*2,
                              2 * 0.00010350000000025616 + 722 * 6.9141274238370105e-06 +
                              1039682 * 3.98596878660858e-07]
actual_slicing_time_box_4D = [291284 * 4.1572485958679014e-07 + 404 * 6.358910891215079e-06 +
                              4 * 0.0002907499999995622 + 2 * 0.00039400000000355817 ,
                              579684 * 4.0316620779740755e-07 + 804 * 6.7077114428012355e-06 +
                              4 * 6.675000000022635e-05 + 2 * 0.0002414999999995615,
                              3.9849968905388793e-07 * 1157760 + 804 * 6.14427860693583e-06 +
                              4*6.975000000064568e-05 + 2 * 0.000529999999997699]

# plt.plot(number_points_box_2D, total_algo_time_box_2D, c="blue")
# plt.plot(number_points_box_3D, total_algo_time_box_3D, c="green")
# plt.plot(number_points_box_4D, total_algo_time_box_4D, c="orange")

# PLOT 0 OF ALL EXTRACT AND SLICING TIMES IN ALL DIMENSIONS

plt.plot(number_points_box_2D, extract_algo_time_box_2D, c="blue", linestyle="--", marker="o")
plt.plot(number_points_box_3D, extract_algo_time_box_3D, c="green", linestyle="--", marker="d")
plt.plot(number_points_box_4D, extract_algo_time_box_4D, c="orange", linestyle="--", marker="v")

plt.plot(number_points_box_2D, actual_slicing_time_box_2D, c="blue", label="2D", marker="o")
plt.plot(number_points_box_3D, actual_slicing_time_box_3D, c="green", label="3D", marker="d")
plt.plot(number_points_box_4D, actual_slicing_time_box_4D, c="orange", label="4D", marker="v")


# plt.annotate('Algorithm run time', xy=(2, 1), xytext=(3, 1.5))
plt.title("Total Algorithm Run Time and Slicing Time")
plt.text((0.75)*1000000, 6.05, "Algorithm run time", rotation=30.5)
plt.text((0.8)*1000000, 0.7, "Total slicing time", rotation=3.5)
plt.xlabel("Number of extracted points (in millions)")
plt.ylabel("Time taken (in seconds)")
plt.legend(loc="lower right")
plt.show()

# PLOT 1 OF DIFFERENCE BETWEEN EXTRACT AND SLICING TIME FOR 2D

# PLOT 2 OF DIFFERENT EXTRACT TIME IN ALL DIMENSIONS

# PLOT 3 OF DIFFERENT SLICING TIME IN ALL DIMENSIONS

plt.plot(number_points_box_2D, actual_slicing_time_box_2D, c="blue", label="2D", marker="o")
plt.plot(number_points_box_3D, actual_slicing_time_box_3D, c="green", label="3D", marker="d")
plt.plot(number_points_box_4D, actual_slicing_time_box_4D, c="orange", label="4D", marker="v")

plt.title("Slicing Times")
plt.xlabel("Number of extracted points (in millions)")
plt.ylabel("Time taken (in seconds)")
plt.legend(loc="lower right")
plt.show()

number_of_points_2D_box_unions = [289440, 519840, 807840, 1038240]
total_algo_time_2D_box_unions = [4.644075155258179, 8.693471193313599, 12.548772096633911, 16.745749950408936]
extract_algo_time_2D_box_unions = [3.9688520431518555, 7.517251253128052, 10.700877904891968, 14.363126993179321]
actual_slicing_time_2D_box_unions = [304490 * 4.167460343527014e-07 + 2100 * 7.164761904760321e-06,
                                     536330*4.0699755747380885e-07 + 3700 * 7.06189189189023e-06,
                                     826130 * 4.063004611852375e-07 + 5700 * 6.954561403501221e-06,
                                     1057970*4.073858427003713e-07 + 7300 * 6.799863013725274e-06]

# PLOT 4 OF ONE BOX VS 100 2D BOXES, THE SLICING TIME

plt.plot(number_points_box_2D, actual_slicing_time_box_2D, c="blue", label="Single Box", marker="o")
plt.plot(number_of_points_2D_box_unions, actual_slicing_time_2D_box_unions, c="green", label="Union of 100 Boxes",
         marker="d")

plt.title("Slicing Times for Different Shapes")
plt.xlabel("Number of extracted points (in millions)")
plt.ylabel("Time taken (in seconds)")
plt.legend(loc="lower right")
plt.show()

number_of_points_2D_disk = [277855, 555711, 831355, 1047645]
total_algo_time_2D_disk = [2.4936559200286865, 5.034766912460327, 7.747948169708252, 9.995174884796143]
extract_algo_time_2D_disk = [1.8438458442687988, 3.7317371368408203, 5.778936862945557, 7.335729122161865]
actual_slicing_time_2D_disk = [277857 * 4.0659763835307473e-07 + 249*3.0698795180722826e-05,
                               555713*4.015831913231718e-07+497*3.0350100603609864e-05,
                               831357*4.0053671286882107e-07+721*3.118723994449287e-05,
                               1047647*4.005929478158308e-07+721*3.397503467402818e-05]

number_of_points_2D_box_polygon = [289440, 519840, 807840, 1038240]
total_algo_time_2D_box_polygon = [3.607032060623169, 7.015941858291626, 11.149569034576416, 14.69483208656311]
extract_algo_time_2D_box_polygon = [2.959832191467285, 5.8418169021606445, 9.335574865341187, 12.315201997756958]
actual_slicing_time_2D_box_polygon = [289484*3.987992427904784e-07+402*4.487562189054795e-06,
                                      519916*3.98393201978319e-07 + 722*4.6024930747934256e-06,
                                      807956*3.9702285768050683e-07+1122*4.448306595315123e-06,
                                      1038389*3.971238139069303e-07+1442*4.691400832200721e-06]

# PLOT 5 OF BOX VS DISK VS POLYGON, THE SLICING TIME

plt.plot(number_points_box_2D, actual_slicing_time_box_2D, c="blue", label="Box", marker="o")
# plt.plot(number_of_points_2D_box_unions, actual_slicing_time_2D_box_unions, c="green")
plt.plot(number_of_points_2D_disk, actual_slicing_time_2D_disk, c="green", label="Disk", marker="d")
plt.plot(number_of_points_2D_box_polygon, actual_slicing_time_2D_box_polygon, c="orange", label="Polygon", marker="v")
plt.title("Slicing Times for Different Shapes")
plt.xlabel("Number of extracted points (in millions)")
plt.ylabel("Time taken (in seconds)")
plt.legend(loc="lower right")
plt.show()
