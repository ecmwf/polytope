import bisect

from ..datacube_mappers import DatacubeMapper


class ReducedLatLonMapper(DatacubeMapper):
    def __init__(self, base_axis, mapped_axes, resolution, local_area=[]):
        # TODO: if local area is not empty list, raise NotImplemented
        self._mapped_axes = mapped_axes
        self._base_axis = base_axis
        self._resolution = resolution
        self._axis_reversed = {mapped_axes[0]: False, mapped_axes[1]: False}
        self._first_axis_vals = self.first_axis_vals()

    def first_axis_vals(self):
        resolution = 180 / (self._resolution - 1)
        vals = [-90 + i * resolution for i in range(self._resolution)]
        return vals

    def map_first_axis(self, lower, upper):
        axis_lines = self._first_axis_vals
        return_vals = [val for val in axis_lines if lower <= val <= upper]
        return return_vals

    def lon_spacing(self):
        if self._resolution == 1441:
            return [
                2,
                6,
                14,
                20,
                26,
                32,
                38,
                44,
                50,
                58,
                64,
                70,
                76,
                82,
                88,
                94,
                102,
                108,
                114,
                120,
                126,
                132,
                138,
                144,
                152,
                158,
                164,
                170,
                176,
                182,
                188,
                196,
                202,
                208,
                214,
                220,
                226,
                232,
                238,
                246,
                252,
                258,
                264,
                270,
                276,
                282,
                290,
                296,
                302,
                308,
                314,
                320,
                326,
                332,
                340,
                346,
                352,
                358,
                364,
                370,
                376,
                382,
                388,
                396,
                402,
                408,
                414,
                420,
                426,
                432,
                438,
                444,
                452,
                458,
                464,
                470,
                476,
                482,
                488,
                494,
                500,
                506,
                512,
                520,
                526,
                532,
                538,
                544,
                550,
                556,
                562,
                568,
                574,
                580,
                586,
                594,
                600,
                606,
                612,
                618,
                624,
                630,
                636,
                642,
                648,
                654,
                660,
                666,
                672,
                678,
                686,
                692,
                698,
                704,
                710,
                716,
                722,
                728,
                734,
                740,
                746,
                752,
                758,
                764,
                770,
                776,
                782,
                788,
                794,
                800,
                806,
                812,
                818,
                824,
                830,
                836,
                842,
                848,
                854,
                860,
                866,
                872,
                878,
                884,
                890,
                896,
                902,
                908,
                914,
                920,
                926,
                932,
                938,
                944,
                950,
                956,
                962,
                968,
                974,
                980,
                986,
                992,
                998,
                1004,
                1010,
                1014,
                1020,
                1026,
                1032,
                1038,
                1044,
                1050,
                1056,
                1062,
                1068,
                1074,
                1080,
                1086,
                1092,
                1096,
                1102,
                1108,
                1114,
                1120,
                1126,
                1132,
                1138,
                1144,
                1148,
                1154,
                1160,
                1166,
                1172,
                1178,
                1184,
                1190,
                1194,
                1200,
                1206,
                1212,
                1218,
                1224,
                1230,
                1234,
                1240,
                1246,
                1252,
                1258,
                1264,
                1268,
                1274,
                1280,
                1286,
                1292,
                1296,
                1302,
                1308,
                1314,
                1320,
                1324,
                1330,
                1336,
                1342,
                1348,
                1352,
                1358,
                1364,
                1370,
                1374,
                1380,
                1386,
                1392,
                1396,
                1402,
                1408,
                1414,
                1418,
                1424,
                1430,
                1436,
                1440,
                1446,
                1452,
                1456,
                1462,
                1468,
                1474,
                1478,
                1484,
                1490,
                1494,
                1500,
                1506,
                1510,
                1516,
                1522,
                1526,
                1532,
                1538,
                1542,
                1548,
                1554,
                1558,
                1564,
                1570,
                1574,
                1580,
                1584,
                1590,
                1596,
                1600,
                1606,
                1610,
                1616,
                1622,
                1626,
                1632,
                1636,
                1642,
                1648,
                1652,
                1658,
                1662,
                1668,
                1672,
                1678,
                1684,
                1688,
                1694,
                1698,
                1704,
                1708,
                1714,
                1718,
                1724,
                1728,
                1734,
                1738,
                1744,
                1748,
                1754,
                1758,
                1764,
                1768,
                1774,
                1778,
                1784,
                1788,
                1794,
                1798,
                1804,
                1808,
                1812,
                1818,
                1822,
                1828,
                1832,
                1838,
                1842,
                1846,
                1852,
                1856,
                1862,
                1866,
                1870,
                1876,
                1880,
                1886,
                1890,
                1894,
                1900,
                1904,
                1908,
                1914,
                1918,
                1922,
                1928,
                1932,
                1936,
                1942,
                1946,
                1950,
                1956,
                1960,
                1964,
                1970,
                1974,
                1978,
                1982,
                1988,
                1992,
                1996,
                2002,
                2006,
                2010,
                2014,
                2020,
                2024,
                2028,
                2032,
                2036,
                2042,
                2046,
                2050,
                2054,
                2060,
                2064,
                2068,
                2072,
                2076,
                2080,
                2086,
                2090,
                2094,
                2098,
                2102,
                2106,
                2112,
                2116,
                2120,
                2124,
                2128,
                2132,
                2136,
                2140,
                2144,
                2150,
                2154,
                2158,
                2162,
                2166,
                2170,
                2174,
                2178,
                2182,
                2186,
                2190,
                2194,
                2198,
                2202,
                2206,
                2210,
                2214,
                2218,
                2222,
                2226,
                2230,
                2234,
                2238,
                2242,
                2246,
                2250,
                2254,
                2258,
                2262,
                2266,
                2270,
                2274,
                2278,
                2282,
                2286,
                2290,
                2292,
                2296,
                2300,
                2304,
                2308,
                2312,
                2316,
                2320,
                2324,
                2326,
                2330,
                2334,
                2338,
                2342,
                2346,
                2348,
                2352,
                2356,
                2360,
                2364,
                2366,
                2370,
                2374,
                2378,
                2382,
                2384,
                2388,
                2392,
                2396,
                2398,
                2402,
                2406,
                2410,
                2412,
                2416,
                2420,
                2422,
                2426,
                2430,
                2432,
                2436,
                2440,
                2442,
                2446,
                2450,
                2452,
                2456,
                2460,
                2462,
                2466,
                2470,
                2472,
                2476,
                2478,
                2482,
                2486,
                2488,
                2492,
                2494,
                2498,
                2500,
                2504,
                2508,
                2510,
                2514,
                2516,
                2520,
                2522,
                2526,
                2528,
                2532,
                2534,
                2538,
                2540,
                2544,
                2546,
                2550,
                2552,
                2556,
                2558,
                2560,
                2564,
                2566,
                2570,
                2572,
                2576,
                2578,
                2580,
                2584,
                2586,
                2590,
                2592,
                2594,
                2598,
                2600,
                2602,
                2606,
                2608,
                2610,
                2614,
                2616,
                2618,
                2622,
                2624,
                2626,
                2628,
                2632,
                2634,
                2636,
                2640,
                2642,
                2644,
                2646,
                2650,
                2652,
                2654,
                2656,
                2658,
                2662,
                2664,
                2666,
                2668,
                2670,
                2674,
                2676,
                2678,
                2680,
                2682,
                2684,
                2686,
                2690,
                2692,
                2694,
                2696,
                2698,
                2700,
                2702,
                2704,
                2706,
                2708,
                2712,
                2714,
                2716,
                2718,
                2720,
                2722,
                2724,
                2726,
                2728,
                2730,
                2732,
                2734,
                2736,
                2738,
                2740,
                2742,
                2744,
                2746,
                2748,
                2750,
                2750,
                2752,
                2754,
                2756,
                2758,
                2760,
                2762,
                2764,
                2766,
                2768,
                2768,
                2770,
                2772,
                2774,
                2776,
                2778,
                2780,
                2780,
                2782,
                2784,
                2786,
                2788,
                2788,
                2790,
                2792,
                2794,
                2794,
                2796,
                2798,
                2800,
                2800,
                2802,
                2804,
                2806,
                2806,
                2808,
                2810,
                2810,
                2812,
                2814,
                2814,
                2816,
                2818,
                2818,
                2820,
                2822,
                2822,
                2824,
                2826,
                2826,
                2828,
                2828,
                2830,
                2832,
                2832,
                2834,
                2834,
                2836,
                2836,
                2838,
                2838,
                2840,
                2842,
                2842,
                2844,
                2844,
                2846,
                2846,
                2846,
                2848,
                2848,
                2850,
                2850,
                2852,
                2852,
                2854,
                2854,
                2856,
                2856,
                2856,
                2858,
                2858,
                2860,
                2860,
                2860,
                2862,
                2862,
                2862,
                2864,
                2864,
                2864,
                2866,
                2866,
                2866,
                2868,
                2868,
                2868,
                2868,
                2870,
                2870,
                2870,
                2872,
                2872,
                2872,
                2872,
                2874,
                2874,
                2874,
                2874,
                2874,
                2876,
                2876,
                2876,
                2876,
                2876,
                2876,
                2878,
                2878,
                2878,
                2878,
                2878,
                2878,
                2878,
                2878,
                2880,
                2880,
                2880,
                2880,
                2880,
                2880,
                2880,
                2880,
                2880,
                2880,
                2880,
                2880,
                2880,
                2880,
                2880,
                2880,
                2880,
                2880,
                2880,
                2880,
                2880,
                2880,
                2880,
                2880,
                2880,
                2880,
                2880,
                2880,
                2880,
                2878,
                2878,
                2878,
                2878,
                2878,
                2878,
                2878,
                2878,
                2876,
                2876,
                2876,
                2876,
                2876,
                2876,
                2874,
                2874,
                2874,
                2874,
                2874,
                2872,
                2872,
                2872,
                2872,
                2870,
                2870,
                2870,
                2868,
                2868,
                2868,
                2868,
                2866,
                2866,
                2866,
                2864,
                2864,
                2864,
                2862,
                2862,
                2862,
                2860,
                2860,
                2860,
                2858,
                2858,
                2856,
                2856,
                2856,
                2854,
                2854,
                2852,
                2852,
                2850,
                2850,
                2848,
                2848,
                2846,
                2846,
                2846,
                2844,
                2844,
                2842,
                2842,
                2840,
                2838,
                2838,
                2836,
                2836,
                2834,
                2834,
                2832,
                2832,
                2830,
                2828,
                2828,
                2826,
                2826,
                2824,
                2822,
                2822,
                2820,
                2818,
                2818,
                2816,
                2814,
                2814,
                2812,
                2810,
                2810,
                2808,
                2806,
                2806,
                2804,
                2802,
                2800,
                2800,
                2798,
                2796,
                2794,
                2794,
                2792,
                2790,
                2788,
                2788,
                2786,
                2784,
                2782,
                2780,
                2780,
                2778,
                2776,
                2774,
                2772,
                2770,
                2768,
                2768,
                2766,
                2764,
                2762,
                2760,
                2758,
                2756,
                2754,
                2752,
                2750,
                2750,
                2748,
                2746,
                2744,
                2742,
                2740,
                2738,
                2736,
                2734,
                2732,
                2730,
                2728,
                2726,
                2724,
                2722,
                2720,
                2718,
                2716,
                2714,
                2712,
                2708,
                2706,
                2704,
                2702,
                2700,
                2698,
                2696,
                2694,
                2692,
                2690,
                2686,
                2684,
                2682,
                2680,
                2678,
                2676,
                2674,
                2670,
                2668,
                2666,
                2664,
                2662,
                2658,
                2656,
                2654,
                2652,
                2650,
                2646,
                2644,
                2642,
                2640,
                2636,
                2634,
                2632,
                2628,
                2626,
                2624,
                2622,
                2618,
                2616,
                2614,
                2610,
                2608,
                2606,
                2602,
                2600,
                2598,
                2594,
                2592,
                2590,
                2586,
                2584,
                2580,
                2578,
                2576,
                2572,
                2570,
                2566,
                2564,
                2560,
                2558,
                2556,
                2552,
                2550,
                2546,
                2544,
                2540,
                2538,
                2534,
                2532,
                2528,
                2526,
                2522,
                2520,
                2516,
                2514,
                2510,
                2508,
                2504,
                2500,
                2498,
                2494,
                2492,
                2488,
                2486,
                2482,
                2478,
                2476,
                2472,
                2470,
                2466,
                2462,
                2460,
                2456,
                2452,
                2450,
                2446,
                2442,
                2440,
                2436,
                2432,
                2430,
                2426,
                2422,
                2420,
                2416,
                2412,
                2410,
                2406,
                2402,
                2398,
                2396,
                2392,
                2388,
                2384,
                2382,
                2378,
                2374,
                2370,
                2366,
                2364,
                2360,
                2356,
                2352,
                2348,
                2346,
                2342,
                2338,
                2334,
                2330,
                2326,
                2324,
                2320,
                2316,
                2312,
                2308,
                2304,
                2300,
                2296,
                2292,
                2290,
                2286,
                2282,
                2278,
                2274,
                2270,
                2266,
                2262,
                2258,
                2254,
                2250,
                2246,
                2242,
                2238,
                2234,
                2230,
                2226,
                2222,
                2218,
                2214,
                2210,
                2206,
                2202,
                2198,
                2194,
                2190,
                2186,
                2182,
                2178,
                2174,
                2170,
                2166,
                2162,
                2158,
                2154,
                2150,
                2144,
                2140,
                2136,
                2132,
                2128,
                2124,
                2120,
                2116,
                2112,
                2106,
                2102,
                2098,
                2094,
                2090,
                2086,
                2080,
                2076,
                2072,
                2068,
                2064,
                2060,
                2054,
                2050,
                2046,
                2042,
                2036,
                2032,
                2028,
                2024,
                2020,
                2014,
                2010,
                2006,
                2002,
                1996,
                1992,
                1988,
                1982,
                1978,
                1974,
                1970,
                1964,
                1960,
                1956,
                1950,
                1946,
                1942,
                1936,
                1932,
                1928,
                1922,
                1918,
                1914,
                1908,
                1904,
                1900,
                1894,
                1890,
                1886,
                1880,
                1876,
                1870,
                1866,
                1862,
                1856,
                1852,
                1846,
                1842,
                1838,
                1832,
                1828,
                1822,
                1818,
                1812,
                1808,
                1804,
                1798,
                1794,
                1788,
                1784,
                1778,
                1774,
                1768,
                1764,
                1758,
                1754,
                1748,
                1744,
                1738,
                1734,
                1728,
                1724,
                1718,
                1714,
                1708,
                1704,
                1698,
                1694,
                1688,
                1684,
                1678,
                1672,
                1668,
                1662,
                1658,
                1652,
                1648,
                1642,
                1636,
                1632,
                1626,
                1622,
                1616,
                1610,
                1606,
                1600,
                1596,
                1590,
                1584,
                1580,
                1574,
                1570,
                1564,
                1558,
                1554,
                1548,
                1542,
                1538,
                1532,
                1526,
                1522,
                1516,
                1510,
                1506,
                1500,
                1494,
                1490,
                1484,
                1478,
                1474,
                1468,
                1462,
                1456,
                1452,
                1446,
                1440,
                1436,
                1430,
                1424,
                1418,
                1414,
                1408,
                1402,
                1396,
                1392,
                1386,
                1380,
                1374,
                1370,
                1364,
                1358,
                1352,
                1348,
                1342,
                1336,
                1330,
                1324,
                1320,
                1314,
                1308,
                1302,
                1296,
                1292,
                1286,
                1280,
                1274,
                1268,
                1264,
                1258,
                1252,
                1246,
                1240,
                1234,
                1230,
                1224,
                1218,
                1212,
                1206,
                1200,
                1194,
                1190,
                1184,
                1178,
                1172,
                1166,
                1160,
                1154,
                1148,
                1144,
                1138,
                1132,
                1126,
                1120,
                1114,
                1108,
                1102,
                1096,
                1092,
                1086,
                1080,
                1074,
                1068,
                1062,
                1056,
                1050,
                1044,
                1038,
                1032,
                1026,
                1020,
                1014,
                1010,
                1004,
                998,
                992,
                986,
                980,
                974,
                968,
                962,
                956,
                950,
                944,
                938,
                932,
                926,
                920,
                914,
                908,
                902,
                896,
                890,
                884,
                878,
                872,
                866,
                860,
                854,
                848,
                842,
                836,
                830,
                824,
                818,
                812,
                806,
                800,
                794,
                788,
                782,
                776,
                770,
                764,
                758,
                752,
                746,
                740,
                734,
                728,
                722,
                716,
                710,
                704,
                698,
                692,
                686,
                678,
                672,
                666,
                660,
                654,
                648,
                642,
                636,
                630,
                624,
                618,
                612,
                606,
                600,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
            ]

    def second_axis_vals(self, first_val):
        first_idx = self._first_axis_vals.index(first_val[0])
        Ny = self.lon_spacing()[first_idx]
        second_spacing = 360 / Ny
        return [i * second_spacing for i in range(Ny)]

    def map_second_axis(self, first_val, lower, upper):
        axis_lines = self.second_axis_vals(first_val)
        return_vals = [val for val in axis_lines if lower <= val <= upper]
        return return_vals

    def axes_idx_to_reduced_ll_idx(self, first_idx, second_idx):
        Ny_array = self.lon_spacing()
        idx = 0
        for i in range(self._resolution):
            if i != first_idx:
                idx += Ny_array[i]
            else:
                idx += second_idx
                return idx

    def find_second_idx(self, first_val, second_val):
        tol = 1e-10
        second_axis_vals = self.second_axis_vals(first_val)
        second_idx = bisect.bisect_left(second_axis_vals, second_val - tol)
        return second_idx

    def unmap(self, first_val, second_val):
        tol = 1e-8
        first_value = [i for i in self._first_axis_vals if first_val[0] - tol <= i <= first_val[0] + tol][0]
        first_idx = self._first_axis_vals.index(first_value)
        second_val = [i for i in self.second_axis_vals(first_val) if second_val[0] - tol <= i <= second_val[0] + tol][0]
        second_idx = self.second_axis_vals(first_val).index(second_val)
        reduced_ll_index = self.axes_idx_to_reduced_ll_idx(first_idx, second_idx)
        return reduced_ll_index
