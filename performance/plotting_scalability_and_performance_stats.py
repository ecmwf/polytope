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

plt.plot(number_points_box_2D, total_algo_time_box_2D, c="blue")
plt.plot(number_points_box_3D, total_algo_time_box_3D, c="green")
plt.plot(number_points_box_4D, total_algo_time_box_4D, c="orange")

plt.plot(number_points_box_2D, extract_algo_time_box_2D, c="blue", linestyle="--")
plt.plot(number_points_box_3D, extract_algo_time_box_3D, c="green", linestyle="--")
plt.plot(number_points_box_4D, extract_algo_time_box_4D, c="orange", linestyle="--")

plt.plot(number_points_box_2D, actual_slicing_time_box_2D, c="blue", marker="o")
plt.plot(number_points_box_3D, actual_slicing_time_box_3D, c="green", marker="o")
plt.plot(number_points_box_4D, actual_slicing_time_box_4D, c="orange", marker="o")

plt.title("Different total/extract/slicing times")
plt.show()

plt.plot(number_points_box_2D, actual_slicing_time_box_2D, c="blue", marker="o")
plt.plot(number_points_box_3D, actual_slicing_time_box_3D, c="green", marker="o")
plt.plot(number_points_box_4D, actual_slicing_time_box_4D, c="orange", marker="o")
plt.title("Actual slicing times")
plt.show()

num_1D_slices_box_2D = [289442, 519842, 807842, 1038240]
num_2D_slices_box_2D = [201, 361, 561, 721]
num_3D_slices_box_2D = [0, 0, 0, 0]
num_4D_slices_box_2D = [0, 0, 0, 0]

num_1D_slices_box_3D = [289844, 578882, 1039682]
num_2D_slices_box_3D = [402, 402, 722]
num_3D_slices_box_3D = [2, 2, 2]
num_4D_slices_box_3D = [0, 0, 0]

num_1D_slices_box_4D = [291284, 579684, 1157760]
num_2D_slices_box_4D = [404, 804, 804]
num_3D_slices_box_4D = [4, 4, 4]
num_4D_slices_box_4D = [2, 2, 2]

av_1D_slice_time_box_2D = [9.064192634218924e-08, 9.091095130734284e-08, 9.173443778164712e-08, 9.121082170132226e-08]
av_2D_slice_time_box_2D = [6.259377322979828e-06, 5.8151678365353405e-06, 6.521449369542739e-06, 6.745162519436438e-06]
av_3D_slice_time_box_2D = [0, 0, 0, 0]
av_4D_slice_time_box_2D = [0, 0, 0, 0]

av_1D_slice_time_box_3D = [9.270426113614943e-08, 9.121843222078931e-08, 9.208500888295107e-08]
av_2D_slice_time_box_3D = [6.624715245185207e-06, 5.877433131583295e-06, 6.505326881303021e-06]
av_3D_slice_time_box_3D = [0.0001900196075439453, 0.0002110004425048828, 0.0002740621566772461]
av_4D_slice_time_box_3D = [0, 0, 0]

av_1D_slice_time_box_4D = [8.992712964032136e-08, 9.150393227778518e-08, 9.180750386895496e-08]
av_2D_slice_time_box_4D = [6.554740490299641e-06, 6.232688676065474e-06, 6.275983592170981e-06]
av_3D_slice_time_box_4D = [6.562471389770508e-05, 6.526708602905273e-05, 6.54458999633789e-05]
av_4D_slice_time_box_4D = [0.00024044513702392578, 0.0002626180648803711, 0.00033032894134521484]

plt.scatter(number_points_box_2D, av_1D_slice_time_box_2D, c="blue")
plt.scatter(number_points_box_3D, av_1D_slice_time_box_3D, c="green")
plt.scatter(number_points_box_4D, av_1D_slice_time_box_4D, c="orange")
plt.title("Average 1D slicing times for different dimensions")
plt.show()

plt.scatter(number_points_box_2D, av_2D_slice_time_box_2D, c="blue")
plt.scatter(number_points_box_3D, av_2D_slice_time_box_3D, c="green")
plt.scatter(number_points_box_4D, av_2D_slice_time_box_4D, c="orange")
plt.title("Average 2D slicing times for different dimensions")
plt.show()


number_of_points_2D_box_unions = [289440, 519840, 807840, 1038240]
total_algo_time_2D_box_unions = [4.644075155258179, 8.693471193313599, 12.548772096633911, 16.745749950408936]
extract_algo_time_2D_box_unions = [3.9688520431518555, 7.517251253128052, 10.700877904891968, 14.363126993179321]
actual_slicing_time_2D_box_unions = [304490 * 4.167460343527014e-07 + 2100 * 7.164761904760321e-06,
                                     536330*4.0699755747380885e-07 + 3700 * 7.06189189189023e-06,
                                     826130 * 4.063004611852375e-07 + 5700 * 6.954561403501221e-06,
                                     1057970*4.073858427003713e-07 + 7300 * 6.799863013725274e-06]


plt.plot(number_points_box_2D, total_algo_time_box_2D, c="blue")
plt.plot(number_of_points_2D_box_unions, total_algo_time_2D_box_unions, c="green")
# plt.title("Total Time Single vs 100 Boxes")
# plt.show()

plt.plot(number_points_box_2D, extract_algo_time_box_2D, c="blue", linestyle="--")
plt.plot(number_of_points_2D_box_unions, extract_algo_time_2D_box_unions, c="green", linestyle="--")
plt.title("Total/Extract Time Single vs 100 Boxes")
plt.show()

plt.plot(number_points_box_2D, actual_slicing_time_box_2D, c="blue")
plt.plot(number_of_points_2D_box_unions, actual_slicing_time_2D_box_unions, c="green")
plt.title("Slicing Time Single vs 100 Boxes")
plt.show()

number_of_points_2D_disk = [277855, 555711, 831355, 1047645]
total_algo_time_2D_disk = [2.4936559200286865, 5.034766912460327, 7.747948169708252, 9.995174884796143]
extract_algo_time_2D_disk = [1.8438458442687988, 3.7317371368408203, 5.778936862945557, 7.335729122161865]
actual_slicing_time_2D_disk = [277857 * 4.0659763835307473e-07 + 249*3.0698795180722826e-05,
                               555713*4.015831913231718e-07+497*3.0350100603609864e-05,
                               831357*4.0053671286882107e-07+721*3.118723994449287e-05,
                               1047647*4.005929478158308e-07+721*3.397503467402818e-05]

plt.plot(number_points_box_2D, total_algo_time_box_2D, c="blue")
plt.plot(number_of_points_2D_box_unions, total_algo_time_2D_box_unions, c="green")
plt.plot(number_of_points_2D_disk, total_algo_time_2D_disk, c="orange")
# plt.title("Total Time Single vs 100 Boxes")
# plt.show()

plt.plot(number_points_box_2D, extract_algo_time_box_2D, c="blue", linestyle="--")
plt.plot(number_of_points_2D_box_unions, extract_algo_time_2D_box_unions, c="green", linestyle="--")
plt.plot(number_of_points_2D_disk, extract_algo_time_2D_disk, c="orange", linestyle="--")
plt.title("Total/Extract Time Single vs 100 Boxes vs Disk")
plt.show()

plt.plot(number_points_box_2D, actual_slicing_time_box_2D, c="blue")
plt.plot(number_of_points_2D_box_unions, actual_slicing_time_2D_box_unions, c="green")
plt.plot(number_of_points_2D_disk, actual_slicing_time_2D_disk, c="orange")
plt.title("Slicing Time Single vs 100 Boxes vs Disk")
plt.show()

number_of_points_2D_box_polygon = [289440, 519840, 807840, 1038240]
total_algo_time_2D_box_polygon = [3.607032060623169, 7.015941858291626, 11.149569034576416, 14.69483208656311]
extract_algo_time_2D_box_polygon = [2.959832191467285, 5.8418169021606445, 9.335574865341187, 12.315201997756958]
actual_slicing_time_2D_box_polygon = [289484*3.987992427904784e-07+402*4.487562189054795e-06,
                                      519916*3.98393201978319e-07 + 722*4.6024930747934256e-06,
                                      807956*3.9702285768050683e-07+1122*4.448306595315123e-06,
                                      1038389*3.971238139069303e-07+1442*4.691400832200721e-06]

plt.plot(number_points_box_2D, total_algo_time_box_2D, c="blue")
plt.plot(number_of_points_2D_box_unions, total_algo_time_2D_box_unions, c="green")
plt.plot(number_of_points_2D_disk, total_algo_time_2D_disk, c="orange")
plt.plot(number_of_points_2D_box_polygon, total_algo_time_2D_box_polygon, c="red")

plt.plot(number_points_box_2D, extract_algo_time_box_2D, c="blue", linestyle="--")
plt.plot(number_of_points_2D_box_unions, extract_algo_time_2D_box_unions, c="green", linestyle="--")
plt.plot(number_of_points_2D_disk, extract_algo_time_2D_disk, c="orange", linestyle="--")
plt.plot(number_of_points_2D_box_polygon, extract_algo_time_2D_box_polygon, c="red", linestyle="--")
plt.title("Total/Extract Time Single vs 100 Boxes vs Disk vs Box as Polygon")
plt.show()

plt.plot(number_points_box_2D, actual_slicing_time_box_2D, c="blue")
plt.plot(number_of_points_2D_box_unions, actual_slicing_time_2D_box_unions, c="green")
plt.plot(number_of_points_2D_disk, actual_slicing_time_2D_disk, c="orange")
plt.plot(number_of_points_2D_box_polygon, actual_slicing_time_2D_box_polygon, c="red")
plt.title("Slicing Time Single vs 100 Boxes vs Disk vs Box as Polygon")
plt.show()
