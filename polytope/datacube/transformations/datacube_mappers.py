import math
from copy import deepcopy
from importlib import import_module
from ...utility.list_tools import bisect_left_cmp, bisect_right_cmp
import bisect

from .datacube_transformations import DatacubeAxisTransformation


class DatacubeMapper(DatacubeAxisTransformation):
    # Needs to implements DatacubeAxisTransformation methods

    def __init__(self, name, mapper_options):
        self.transformation_options = mapper_options
        self.grid_type = mapper_options["type"]
        self.grid_resolution = mapper_options["resolution"]
        self.grid_axes = mapper_options["axes"]
        self.old_axis = name
        self._final_transformation = self.generate_final_transformation()
        self._final_mapped_axes = self._final_transformation._mapped_axes
        self._axis_reversed = self._final_transformation._axis_reversed

    def generate_final_transformation(self):
        map_type = _type_to_datacube_mapper_lookup[self.grid_type]
        module = import_module("polytope.datacube.transformations.datacube_mappers")
        constructor = getattr(module, map_type)
        transformation = deepcopy(constructor(self.old_axis, self.grid_axes, self.grid_resolution))
        return transformation

    def blocked_axes(self):
        return []

    def unwanted_axes(self):
        return [self._final_mapped_axes[0]]

    def transformation_axes_final(self):
        # final_transformation = self.generate_final_transformation()
        # final_axes = self._final_transformation._mapped_axes
        final_axes = self._final_mapped_axes
        return final_axes

    # Needs to also implement its own methods

    def change_val_type(self, axis_name, values):
        # the new axis_vals created will be floats
        return [0.0]

    def _mapped_axes(self):
        # NOTE: Each of the mapper method needs to call it's sub mapper method
        # final_transformation = self.generate_final_transformation()
        # final_axes = self._final_transformation._mapped_axes
        final_axes = self._final_mapped_axes
        return final_axes

    def _base_axis(self):
        pass

    def _resolution(self):
        pass

    def first_axis_vals(self):
        # final_transformation = self.generate_final_transformation()
        return self._final_transformation.first_axis_vals()

    def second_axis_vals(self, first_val):
        # final_transformation = self.generate_final_transformation()
        return self._final_transformation.second_axis_vals(first_val)

    def map_first_axis(self, lower, upper):
        # final_transformation = self.generate_final_transformation()
        return self._final_transformation.map_first_axis(lower, upper)

    def map_second_axis(self, first_val, lower, upper):
        # final_transformation = self.generate_final_transformation()
        return self._final_transformation.map_second_axis(first_val, lower, upper)

    def find_second_idx(self, first_val, second_val):
        return self._final_transformation.find_second_idx(first_val, second_val)

    def unmap_first_val_to_start_line_idx(self, first_val):
        return self._final_transformation.unmap_first_val_to_start_line_idx(first_val)

    def unmap(self, first_val, second_val):
        # final_transformation = self.generate_final_transformation()
        return self._final_transformation.unmap(first_val, second_val)


class RegularGridMapper(DatacubeMapper):
    def __init__(self, base_axis, mapped_axes, resolution):
        self._mapped_axes = mapped_axes
        self._base_axis = base_axis
        self._resolution = resolution
        self.deg_increment = 90 / self._resolution
        self._axis_reversed = {mapped_axes[0]: True, mapped_axes[1]: False}

    def first_axis_vals(self):
        first_ax_vals = [-90 + i * self.deg_increment for i in range(2 * self._resolution)]
        return first_ax_vals

    def map_first_axis(self, lower, upper):
        axis_lines = self.first_axis_vals()
        return_vals = [val for val in axis_lines if lower <= val <= upper]
        return return_vals

    def second_axis_vals(self, first_val):
        second_ax_vals = [i * self.deg_increment for i in range(4 * self._resolution)]
        return second_ax_vals

    def map_second_axis(self, first_val, lower, upper):
        axis_lines = self.second_axis_vals(first_val)
        return_vals = [val for val in axis_lines if lower <= val <= upper]
        return return_vals

    def axes_idx_to_regular_idx(self, first_idx, second_idx):
        final_idx = first_idx * 4 * self._resolution + second_idx
        return final_idx

    def find_second_idx(self, first_val, second_val):
        tol = 1e-10
        second_axis_vals = self.second_axis_vals(first_val)
        second_idx = bisect.bisect_left(second_axis_vals, second_val - tol)
        return second_idx

    def unmap_first_val_to_start_line_idx(self, first_val):
        tol = 1e-8
        first_val = [i for i in self.first_axis_vals() if first_val - tol <= i <= first_val + tol][0]
        first_idx = self.first_axis_vals().index(first_val)
        return first_idx * 4 * self._resolution

    def unmap(self, first_val, second_val):
        tol = 1e-8
        first_val = [i for i in self.first_axis_vals() if first_val - tol <= i <= first_val + tol][0]
        first_idx = self.first_axis_vals().index(first_val)
        second_val = [i for i in self.second_axis_vals(first_val) if second_val - tol <= i <= second_val + tol][0]
        second_idx = self.second_axis_vals(first_val).index(second_val)
        final_index = self.axes_idx_to_regular_idx(first_idx, second_idx)
        return final_index


class HealpixGridMapper(DatacubeMapper):
    def __init__(self, base_axis, mapped_axes, resolution):
        self._mapped_axes = mapped_axes
        self._base_axis = base_axis
        self._resolution = resolution
        self._axis_reversed = {mapped_axes[0]: True, mapped_axes[1]: False}

    def first_axis_vals(self):
        rad2deg = 180 / math.pi
        vals = [0] * (4 * self._resolution - 1)

        # Polar caps
        for i in range(1, self._resolution):
            val = 90 - (rad2deg * math.acos(1 - (i * i / (3 * self._resolution * self._resolution))))
            vals[i - 1] = val
            vals[4 * self._resolution - 1 - i] = -val
        # Equatorial belts
        for i in range(self._resolution, 2 * self._resolution):
            val = 90 - (rad2deg * math.acos((4 * self._resolution - 2 * i) / (3 * self._resolution)))
            vals[i - 1] = val
            vals[4 * self._resolution - 1 - i] = -val
        # Equator
        vals[2 * self._resolution - 1] = 0

        return vals

    def map_first_axis(self, lower, upper):
        axis_lines = self.first_axis_vals()
        return_vals = [val for val in axis_lines if lower <= val <= upper]
        return return_vals

    def second_axis_vals(self, first_val):
        tol = 1e-8
        first_val = [i for i in self.first_axis_vals() if first_val - tol <= i <= first_val + tol][0]
        idx = self.first_axis_vals().index(first_val)

        # Polar caps
        if idx < self._resolution - 1 or 3 * self._resolution - 1 < idx <= 4 * self._resolution - 2:
            start = 45 / (idx + 1)
            vals = [start + i * (360 / (4 * (idx + 1))) for i in range(4 * (idx + 1))]
            return vals
        # Equatorial belts
        start = 45 / self._resolution
        if self._resolution - 1 <= idx < 2 * self._resolution - 1 or 2 * self._resolution <= idx < 3 * self._resolution:
            r_start = start * (2 - (((idx + 1) - self._resolution + 1) % 2))
            vals = [r_start + i * (360 / (4 * self._resolution)) for i in range(4 * self._resolution)]
            return vals
        # Equator
        temp_val = 1 if self._resolution % 2 else 0
        r_start = start * (1 - temp_val)
        if idx == 2 * self._resolution - 1:
            vals = [r_start + i * (360 / (4 * self._resolution)) for i in range(4 * self._resolution)]
            return vals

    def map_second_axis(self, first_val, lower, upper):
        axis_lines = self.second_axis_vals(first_val)
        return_vals = [val for val in axis_lines if lower <= val <= upper]
        return return_vals

    def axes_idx_to_healpix_idx(self, first_idx, second_idx):
        idx = 0
        for i in range(self._resolution - 1):
            if i != first_idx:
                idx += 4 * (i + 1)
            else:
                idx += second_idx
        for i in range(self._resolution - 1, 3 * self._resolution):
            if i != first_idx:
                idx += 4 * self._resolution
            else:
                idx += second_idx
        for i in range(3 * self._resolution, 4 * self._resolution - 1):
            if i != first_idx:
                idx += 4 * (4 * self._resolution - 1 - i + 1)
            else:
                idx += second_idx
        return idx

    def find_second_idx(self, first_val, second_val):
        tol = 1e-10
        second_axis_vals = self.second_axis_vals(first_val)
        second_idx = bisect.bisect_left(second_axis_vals, second_val - tol)
        return second_idx

    def unmap_first_val_to_start_line_idx(self, first_val):
        tol = 1e-8
        first_val = [i for i in self.first_axis_vals() if first_val - tol <= i <= first_val + tol][0]
        first_idx = self.first_axis_vals().index(first_val)
        idx = 0
        for i in range(self._resolution - 1):
            if i != first_idx:
                idx += 4 * (i + 1)
            else:
                return idx
        for i in range(self._resolution - 1, 3 * self._resolution):
            if i != first_idx:
                idx += 4 * self._resolution
            else:
                return idx
        for i in range(3 * self._resolution, 4 * self._resolution - 1):
            if i != first_idx:
                idx += 4 * (4 * self._resolution - 1 - i + 1)
            else:
                return idx

    def unmap(self, first_val, second_val):
        tol = 1e-8
        first_val = [i for i in self.first_axis_vals() if first_val - tol <= i <= first_val + tol][0]
        first_idx = self.first_axis_vals().index(first_val)
        second_val = [i for i in self.second_axis_vals(first_val) if second_val - tol <= i <= second_val + tol][0]
        second_idx = self.second_axis_vals(first_val).index(second_val)
        healpix_index = self.axes_idx_to_healpix_idx(first_idx, second_idx)
        return healpix_index


class OctahedralGridMapper(DatacubeMapper):
    def __init__(self, base_axis, mapped_axes, resolution):
        self._mapped_axes = mapped_axes
        self._base_axis = base_axis
        self._resolution = resolution
        self._first_axis_vals = self.first_axis_vals()
        # self._inv_first_axis_vals = self._first_axis_vals[::-1]
        # self._inv_first_axis_vals = {v:k for k,v in self._first_axis_vals.items()}
        self._first_idx_map = self.create_first_idx_map()
        # self._second_axis_spacing = dict()
        self._second_axis_spacing = {}
        # self.treated_first_vals = dict()
        self._axis_reversed = {mapped_axes[0]: True, mapped_axes[1]: False}

    def gauss_first_guess(self):
        i = 0
        gvals = [
            2.4048255577e0,
            5.5200781103e0,
            8.6537279129e0,
            11.7915344391e0,
            14.9309177086e0,
            18.0710639679e0,
            21.2116366299e0,
            24.3524715308e0,
            27.4934791320e0,
            30.6346064684e0,
            33.7758202136e0,
            36.9170983537e0,
            40.0584257646e0,
            43.1997917132e0,
            46.3411883717e0,
            49.4826098974e0,
            52.6240518411e0,
            55.7655107550e0,
            58.9069839261e0,
            62.0484691902e0,
            65.1899648002e0,
            68.3314693299e0,
            71.4729816036e0,
            74.6145006437e0,
            77.7560256304e0,
            80.8975558711e0,
            84.0390907769e0,
            87.1806298436e0,
            90.3221726372e0,
            93.4637187819e0,
            96.6052679510e0,
            99.7468198587e0,
            102.8883742542e0,
            106.0299309165e0,
            109.1714896498e0,
            112.3130502805e0,
            115.4546126537e0,
            118.5961766309e0,
            121.7377420880e0,
            124.8793089132e0,
            128.0208770059e0,
            131.1624462752e0,
            134.3040166383e0,
            137.4455880203e0,
            140.5871603528e0,
            143.7287335737e0,
            146.8703076258e0,
            150.0118824570e0,
            153.1534580192e0,
            156.2950342685e0,
        ]

        numVals = len(gvals)
        vals = []
        for i in range(self._resolution):
            if i < numVals:
                vals.append(gvals[i])
            else:
                vals.append(vals[i - 1] + math.pi)
        return vals

    def get_precomputed_values_N1280(self):
        lats = [0] * 2560
        # lats = SortedList()
        # lats = {}
        lats[0] = 89.946187715665616
        lats[1] = 89.876478353332288
        lats[2] = 89.806357319542244
        lats[3] = 89.736143271609578
        lats[4] = 89.6658939412157
        lats[5] = 89.595627537554492
        lats[6] = 89.525351592371393
        lats[7] = 89.45506977912261
        lats[8] = 89.3847841013921
        lats[9] = 89.314495744374256
        lats[10] = 89.24420545380525
        lats[11] = 89.173913722284126
        lats[12] = 89.103620888238879
        lats[13] = 89.033327191845927
        lats[14] = 88.96303280826325
        lats[15] = 88.892737868230952
        lats[16] = 88.822442471310097
        lats[17] = 88.752146694650691
        lats[18] = 88.681850598961759
        lats[19] = 88.611554232668382
        lats[20] = 88.541257634868515
        lats[21] = 88.470960837474877
        lats[22] = 88.40066386679355
        lats[23] = 88.330366744702559
        lats[24] = 88.26006948954614
        lats[25] = 88.189772116820762
        lats[26] = 88.119474639706425
        lats[27] = 88.049177069484486
        lats[28] = 87.978879415867283
        lats[29] = 87.908581687261687
        lats[30] = 87.838283890981543
        lats[31] = 87.767986033419561
        lats[32] = 87.697688120188062
        lats[33] = 87.627390156234085
        lats[34] = 87.557092145935584
        lats[35] = 87.486794093180748
        lats[36] = 87.416496001434894
        lats[37] = 87.346197873795816
        lats[38] = 87.275899713041966
        lats[39] = 87.205601521672108
        lats[40] = 87.135303301939786
        lats[41] = 87.065005055882821
        lats[42] = 86.994706785348129
        lats[43] = 86.924408492014166
        lats[44] = 86.854110177408927
        lats[45] = 86.783811842927179
        lats[46] = 86.713513489844246
        lats[47] = 86.643215119328573
        lats[48] = 86.572916732453024
        lats[49] = 86.502618330203831
        lats[50] = 86.432319913489792
        lats[51] = 86.362021483149363
        lats[52] = 86.291723039957418
        lats[53] = 86.221424584631109
        lats[54] = 86.151126117835304
        lats[55] = 86.080827640187209
        lats[56] = 86.010529152260403
        lats[57] = 85.940230654588888
        lats[58] = 85.869932147670127
        lats[59] = 85.799633631968391
        lats[60] = 85.729335107917464
        lats[61] = 85.659036575922883
        lats[62] = 85.588738036364362
        lats[63] = 85.518439489597966
        lats[64] = 85.448140935957483
        lats[65] = 85.377842375756586
        lats[66] = 85.307543809290152
        lats[67] = 85.237245236835548
        lats[68] = 85.16694665865414
        lats[69] = 85.09664807499216
        lats[70] = 85.026349486081983
        lats[71] = 84.95605089214304
        lats[72] = 84.885752293382765
        lats[73] = 84.81545368999717
        lats[74] = 84.745155082171991
        lats[75] = 84.674856470082915
        lats[76] = 84.604557853896708
        lats[77] = 84.534259233771479
        lats[78] = 84.463960609857125
        lats[79] = 84.393661982296322
        lats[80] = 84.323363351224444
        lats[81] = 84.253064716770425
        lats[82] = 84.18276607905679
        lats[83] = 84.112467438200326
        lats[84] = 84.042168794312317
        lats[85] = 83.971870147498763
        lats[86] = 83.901571497860914
        lats[87] = 83.831272845495249
        lats[88] = 83.760974190494011
        lats[89] = 83.690675532945292
        lats[90] = 83.620376872933264
        lats[91] = 83.550078210538487
        lats[92] = 83.479779545838113
        lats[93] = 83.409480878905782
        lats[94] = 83.339182209812321
        lats[95] = 83.268883538625232
        lats[96] = 83.198584865409657
        lats[97] = 83.128286190227698
        lats[98] = 83.057987513139125
        lats[99] = 82.987688834201322
        lats[100] = 82.917390153469313
        lats[101] = 82.84709147099602
        lats[102] = 82.77679278683226
        lats[103] = 82.706494101026948
        lats[104] = 82.63619541362705
        lats[105] = 82.56589672467787
        lats[106] = 82.495598034222837
        lats[107] = 82.425299342304029
        lats[108] = 82.355000648961692
        lats[109] = 82.284701954234833
        lats[110] = 82.214403258160871
        lats[111] = 82.144104560776
        lats[112] = 82.073805862115165
        lats[113] = 82.003507162211946
        lats[114] = 81.933208461098829
        lats[115] = 81.862909758807191
        lats[116] = 81.792611055367345
        lats[117] = 81.722312350808508
        lats[118] = 81.652013645158945
        lats[119] = 81.581714938445955
        lats[120] = 81.511416230696042
        lats[121] = 81.441117521934686
        lats[122] = 81.370818812186627
        lats[123] = 81.300520101475826
        lats[124] = 81.230221389825374
        lats[125] = 81.159922677257711
        lats[126] = 81.089623963794551
        lats[127] = 81.019325249456955
        lats[128] = 80.949026534265244
        lats[129] = 80.878727818239184
        lats[130] = 80.808429101397948
        lats[131] = 80.73813038376008
        lats[132] = 80.667831665343556
        lats[133] = 80.59753294616587
        lats[134] = 80.527234226243991
        lats[135] = 80.456935505594302
        lats[136] = 80.386636784232863
        lats[137] = 80.316338062175078
        lats[138] = 80.246039339436052
        lats[139] = 80.175740616030438
        lats[140] = 80.105441891972376
        lats[141] = 80.035143167275749
        lats[142] = 79.9648444419539
        lats[143] = 79.894545716019948
        lats[144] = 79.824246989486554
        lats[145] = 79.753948262366038
        lats[146] = 79.683649534670437
        lats[147] = 79.61335080641139
        lats[148] = 79.543052077600308
        lats[149] = 79.472753348248219
        lats[150] = 79.402454618365894
        lats[151] = 79.332155887963822
        lats[152] = 79.261857157052191
        lats[153] = 79.191558425640977
        lats[154] = 79.121259693739859
        lats[155] = 79.050960961358285
        lats[156] = 78.980662228505423
        lats[157] = 78.910363495190211
        lats[158] = 78.840064761421445
        lats[159] = 78.769766027207638
        lats[160] = 78.699467292557102
        lats[161] = 78.629168557477882
        lats[162] = 78.558869821977908
        lats[163] = 78.488571086064923
        lats[164] = 78.418272349746417
        lats[165] = 78.347973613029708
        lats[166] = 78.277674875922045
        lats[167] = 78.207376138430348
        lats[168] = 78.137077400561424
        lats[169] = 78.066778662322022
        lats[170] = 77.996479923718596
        lats[171] = 77.926181184757539
        lats[172] = 77.855882445445019
        lats[173] = 77.785583705787161
        lats[174] = 77.71528496578982
        lats[175] = 77.644986225458879
        lats[176] = 77.574687484799924
        lats[177] = 77.504388743818524
        lats[178] = 77.434090002520122
        lats[179] = 77.363791260909963
        lats[180] = 77.293492518993247
        lats[181] = 77.22319377677502
        lats[182] = 77.15289503426024
        lats[183] = 77.082596291453768
        lats[184] = 77.012297548360323
        lats[185] = 76.941998804984564
        lats[186] = 76.871700061330955
        lats[187] = 76.801401317404
        lats[188] = 76.731102573208048
        lats[189] = 76.660803828747362
        lats[190] = 76.59050508402602
        lats[191] = 76.520206339048215
        lats[192] = 76.449907593817869
        lats[193] = 76.379608848338933
        lats[194] = 76.3093101026152
        lats[195] = 76.239011356650423
        lats[196] = 76.16871261044831
        lats[197] = 76.098413864012443
        lats[198] = 76.028115117346374
        lats[199] = 75.957816370453543
        lats[200] = 75.887517623337317
        lats[201] = 75.81721887600105
        lats[202] = 75.746920128447996
        lats[203] = 75.67662138068134
        lats[204] = 75.60632263270422
        lats[205] = 75.536023884519707
        lats[206] = 75.465725136130786
        lats[207] = 75.395426387540439
        lats[208] = 75.325127638751567
        lats[209] = 75.254828889766983
        lats[210] = 75.184530140589501
        lats[211] = 75.114231391221821
        lats[212] = 75.043932641666672
        lats[213] = 74.973633891926625
        lats[214] = 74.903335142004323
        lats[215] = 74.833036391902269
        lats[216] = 74.762737641622991
        lats[217] = 74.692438891168877
        lats[218] = 74.622140140542356
        lats[219] = 74.551841389745761
        lats[220] = 74.481542638781434
        lats[221] = 74.411243887651622
        lats[222] = 74.340945136358584
        lats[223] = 74.270646384904481
        lats[224] = 74.200347633291472
        lats[225] = 74.13004888152166
        lats[226] = 74.059750129597163
        lats[227] = 73.98945137751997
        lats[228] = 73.919152625292114
        lats[229] = 73.848853872915541
        lats[230] = 73.778555120392184
        lats[231] = 73.70825636772399
        lats[232] = 73.637957614912779
        lats[233] = 73.567658861960396
        lats[234] = 73.497360108868662
        lats[235] = 73.427061355639339
        lats[236] = 73.356762602274188
        lats[237] = 73.2864638487749
        lats[238] = 73.216165095143182
        lats[239] = 73.145866341380668
        lats[240] = 73.075567587489019
        lats[241] = 73.005268833469799
        lats[242] = 72.934970079324657
        lats[243] = 72.864671325055056
        lats[244] = 72.794372570662574
        lats[245] = 72.724073816148703
        lats[246] = 72.653775061514935
        lats[247] = 72.583476306762691
        lats[248] = 72.513177551893421
        lats[249] = 72.442878796908545
        lats[250] = 72.3725800418094
        lats[251] = 72.302281286597392
        lats[252] = 72.231982531273843
        lats[253] = 72.161683775840089
        lats[254] = 72.091385020297409
        lats[255] = 72.02108626464711
        lats[256] = 71.950787508890414
        lats[257] = 71.880488753028587
        lats[258] = 71.810189997062835
        lats[259] = 71.739891240994368
        lats[260] = 71.669592484824364
        lats[261] = 71.599293728553988
        lats[262] = 71.528994972184378
        lats[263] = 71.458696215716685
        lats[264] = 71.388397459152031
        lats[265] = 71.318098702491469
        lats[266] = 71.247799945736105
        lats[267] = 71.177501188887007
        lats[268] = 71.107202431945211
        lats[269] = 71.036903674911756
        lats[270] = 70.966604917787635
        lats[271] = 70.896306160573886
        lats[272] = 70.826007403271475
        lats[273] = 70.755708645881384
        lats[274] = 70.685409888404578
        lats[275] = 70.615111130841967
        lats[276] = 70.544812373194532
        lats[277] = 70.474513615463138
        lats[278] = 70.404214857648739
        lats[279] = 70.333916099752187
        lats[280] = 70.263617341774406
        lats[281] = 70.193318583716191
        lats[282] = 70.123019825578467
        lats[283] = 70.052721067362043
        lats[284] = 69.982422309067744
        lats[285] = 69.912123550696421
        lats[286] = 69.841824792248843
        lats[287] = 69.771526033725834
        lats[288] = 69.701227275128161
        lats[289] = 69.630928516456592
        lats[290] = 69.560629757711908
        lats[291] = 69.490330998894862
        lats[292] = 69.420032240006194
        lats[293] = 69.349733481046613
        lats[294] = 69.279434722016902
        lats[295] = 69.209135962917699
        lats[296] = 69.138837203749759
        lats[297] = 69.068538444513763
        lats[298] = 68.998239685210365
        lats[299] = 68.927940925840304
        lats[300] = 68.85764216640419
        lats[301] = 68.787343406902693
        lats[302] = 68.717044647336493
        lats[303] = 68.646745887706189
        lats[304] = 68.576447128012447
        lats[305] = 68.506148368255865
        lats[306] = 68.435849608437067
        lats[307] = 68.365550848556666
        lats[308] = 68.295252088615257
        lats[309] = 68.224953328613438
        lats[310] = 68.154654568551791
        lats[311] = 68.084355808430871
        lats[312] = 68.014057048251274
        lats[313] = 67.943758288013555
        lats[314] = 67.873459527718282
        lats[315] = 67.803160767365966
        lats[316] = 67.732862006957205
        lats[317] = 67.662563246492482
        lats[318] = 67.592264485972336
        lats[319] = 67.521965725397308
        lats[320] = 67.451666964767895
        lats[321] = 67.381368204084609
        lats[322] = 67.311069443347961
        lats[323] = 67.240770682558434
        lats[324] = 67.170471921716526
        lats[325] = 67.100173160822706
        lats[326] = 67.029874399877471
        lats[327] = 66.95957563888129
        lats[328] = 66.889276877834618
        lats[329] = 66.818978116737924
        lats[330] = 66.748679355591662
        lats[331] = 66.678380594396273
        lats[332] = 66.608081833152212
        lats[333] = 66.537783071859891
        lats[334] = 66.467484310519808
        lats[335] = 66.397185549132331
        lats[336] = 66.326886787697887
        lats[337] = 66.256588026216932
        lats[338] = 66.186289264689833
        lats[339] = 66.115990503117033
        lats[340] = 66.045691741498899
        lats[341] = 65.975392979835888
        lats[342] = 65.905094218128355
        lats[343] = 65.834795456376696
        lats[344] = 65.764496694581283
        lats[345] = 65.694197932742526
        lats[346] = 65.623899170860767
        lats[347] = 65.553600408936404
        lats[348] = 65.483301646969792
        lats[349] = 65.413002884961315
        lats[350] = 65.342704122911286
        lats[351] = 65.272405360820116
        lats[352] = 65.202106598688133
        lats[353] = 65.131807836515677
        lats[354] = 65.061509074303089
        lats[355] = 64.991210312050711
        lats[356] = 64.920911549758912
        lats[357] = 64.850612787427963
        lats[358] = 64.780314025058246
        lats[359] = 64.710015262650074
        lats[360] = 64.639716500203733
        lats[361] = 64.569417737719576
        lats[362] = 64.499118975197902
        lats[363] = 64.428820212639039
        lats[364] = 64.358521450043284
        lats[365] = 64.288222687410922
        lats[366] = 64.21792392474228
        lats[367] = 64.147625162037642
        lats[368] = 64.07732639929732
        lats[369] = 64.00702763652157
        lats[370] = 63.93672887371072
        lats[371] = 63.866430110865004
        lats[372] = 63.796131347984762
        lats[373] = 63.725832585070251
        lats[374] = 63.655533822121711
        lats[375] = 63.585235059139464
        lats[376] = 63.514936296123757
        lats[377] = 63.444637533074854
        lats[378] = 63.374338769993031
        lats[379] = 63.304040006878537
        lats[380] = 63.23374124373165
        lats[381] = 63.163442480552604
        lats[382] = 63.093143717341647
        lats[383] = 63.022844954099064
        lats[384] = 62.952546190825068
        lats[385] = 62.882247427519928
        lats[386] = 62.811948664183866
        lats[387] = 62.741649900817137
        lats[388] = 62.67135113741999
        lats[389] = 62.60105237399263
        lats[390] = 62.530753610535321
        lats[391] = 62.460454847048261
        lats[392] = 62.3901560835317
        lats[393] = 62.319857319985871
        lats[394] = 62.249558556410982
        lats[395] = 62.179259792807258
        lats[396] = 62.108961029174914
        lats[397] = 62.038662265514176
        lats[398] = 61.968363501825259
        lats[399] = 61.898064738108381
        lats[400] = 61.827765974363729
        lats[401] = 61.757467210591535
        lats[402] = 61.687168446791986
        lats[403] = 61.616869682965287
        lats[404] = 61.546570919111666
        lats[405] = 61.476272155231321
        lats[406] = 61.405973391324409
        lats[407] = 61.335674627391185
        lats[408] = 61.265375863431785
        lats[409] = 61.195077099446451
        lats[410] = 61.124778335435344
        lats[411] = 61.054479571398652
        lats[412] = 60.984180807336578
        lats[413] = 60.913882043249295
        lats[414] = 60.843583279137007
        lats[415] = 60.773284514999872
        lats[416] = 60.702985750838074
        lats[417] = 60.632686986651805
        lats[418] = 60.562388222441243
        lats[419] = 60.492089458206543
        lats[420] = 60.421790693947884
        lats[421] = 60.35149192966545
        lats[422] = 60.28119316535939
        lats[423] = 60.21089440102989
        lats[424] = 60.140595636677112
        lats[425] = 60.070296872301235
        lats[426] = 59.999998107902378
        lats[427] = 59.929699343480763
        lats[428] = 59.859400579036503
        lats[429] = 59.78910181456979
        lats[430] = 59.718803050080759
        lats[431] = 59.64850428556958
        lats[432] = 59.578205521036402
        lats[433] = 59.507906756481383
        lats[434] = 59.43760799190467
        lats[435] = 59.3673092273064
        lats[436] = 59.29701046268675
        lats[437] = 59.226711698045854
        lats[438] = 59.156412933383855
        lats[439] = 59.086114168700909
        lats[440] = 59.015815403997145
        lats[441] = 58.945516639272725
        lats[442] = 58.875217874527763
        lats[443] = 58.804919109762423
        lats[444] = 58.73462034497684
        lats[445] = 58.664321580171141
        lats[446] = 58.594022815345468
        lats[447] = 58.523724050499972
        lats[448] = 58.453425285634758
        lats[449] = 58.383126520749968
        lats[450] = 58.312827755845746
        lats[451] = 58.242528990922203
        lats[452] = 58.172230225979497
        lats[453] = 58.101931461017728
        lats[454] = 58.031632696037022
        lats[455] = 57.961333931037537
        lats[456] = 57.891035166019364
        lats[457] = 57.820736400982646
        lats[458] = 57.75043763592749
        lats[459] = 57.680138870854037
        lats[460] = 57.60984010576238
        lats[461] = 57.539541340652676
        lats[462] = 57.469242575525016
        lats[463] = 57.398943810379521
        lats[464] = 57.328645045216312
        lats[465] = 57.258346280035504
        lats[466] = 57.188047514837208
        lats[467] = 57.117748749621541
        lats[468] = 57.047449984388614
        lats[469] = 56.977151219138541
        lats[470] = 56.90685245387143
        lats[471] = 56.836553688587379
        lats[472] = 56.766254923286517
        lats[473] = 56.695956157968951
        lats[474] = 56.625657392634771
        lats[475] = 56.555358627284086
        lats[476] = 56.485059861917016
        lats[477] = 56.41476109653366
        lats[478] = 56.34446233113411
        lats[479] = 56.274163565718467
        lats[480] = 56.203864800286865
        lats[481] = 56.133566034839362
        lats[482] = 56.063267269376091
        lats[483] = 55.992968503897131
        lats[484] = 55.922669738402583
        lats[485] = 55.852370972892551
        lats[486] = 55.782072207367136
        lats[487] = 55.711773441826416
        lats[488] = 55.641474676270505
        lats[489] = 55.571175910699488
        lats[490] = 55.500877145113449
        lats[491] = 55.430578379512511
        lats[492] = 55.360279613896743
        lats[493] = 55.289980848266232
        lats[494] = 55.219682082621084
        lats[495] = 55.149383316961377
        lats[496] = 55.07908455128721
        lats[497] = 55.008785785598668
        lats[498] = 54.938487019895831
        lats[499] = 54.868188254178797
        lats[500] = 54.797889488447652
        lats[501] = 54.727590722702473
        lats[502] = 54.657291956943347
        lats[503] = 54.586993191170357
        lats[504] = 54.516694425383605
        lats[505] = 54.446395659583146
        lats[506] = 54.376096893769081
        lats[507] = 54.305798127941479
        lats[508] = 54.235499362100448
        lats[509] = 54.165200596246031
        lats[510] = 54.094901830378333
        lats[511] = 54.024603064497434
        lats[512] = 53.954304298603383
        lats[513] = 53.884005532696307
        lats[514] = 53.813706766776235
        lats[515] = 53.743408000843282
        lats[516] = 53.673109234897495
        lats[517] = 53.602810468938962
        lats[518] = 53.53251170296776
        lats[519] = 53.462212936983953
        lats[520] = 53.391914170987633
        lats[521] = 53.321615404978871
        lats[522] = 53.251316638957725
        lats[523] = 53.181017872924265
        lats[524] = 53.110719106878584
        lats[525] = 53.040420340820731
        lats[526] = 52.970121574750792
        lats[527] = 52.899822808668837
        lats[528] = 52.829524042574917
        lats[529] = 52.759225276469131
        lats[530] = 52.688926510351514
        lats[531] = 52.618627744222159
        lats[532] = 52.548328978081123
        lats[533] = 52.478030211928477
        lats[534] = 52.407731445764284
        lats[535] = 52.337432679588609
        lats[536] = 52.26713391340153
        lats[537] = 52.196835147203096
        lats[538] = 52.126536380993372
        lats[539] = 52.056237614772435
        lats[540] = 51.985938848540336
        lats[541] = 51.915640082297152
        lats[542] = 51.845341316042933
        lats[543] = 51.775042549777737
        lats[544] = 51.704743783501634
        lats[545] = 51.634445017214695
        lats[546] = 51.56414625091697
        lats[547] = 51.493847484608516
        lats[548] = 51.423548718289396
        lats[549] = 51.353249951959683
        lats[550] = 51.282951185619417
        lats[551] = 51.21265241926865
        lats[552] = 51.14235365290746
        lats[553] = 51.072054886535909
        lats[554] = 51.001756120154049
        lats[555] = 50.931457353761914
        lats[556] = 50.86115858735959
        lats[557] = 50.790859820947119
        lats[558] = 50.720561054524559
        lats[559] = 50.650262288091959
        lats[560] = 50.579963521649397
        lats[561] = 50.509664755196901
        lats[562] = 50.439365988734544
        lats[563] = 50.369067222262359
        lats[564] = 50.298768455780426
        lats[565] = 50.228469689288779
        lats[566] = 50.158170922787484
        lats[567] = 50.087872156276575
        lats[568] = 50.017573389756123
        lats[569] = 49.947274623226157
        lats[570] = 49.876975856686762
        lats[571] = 49.80667709013796
        lats[572] = 49.736378323579807
        lats[573] = 49.66607955701236
        lats[574] = 49.595780790435676
        lats[575] = 49.525482023849783
        lats[576] = 49.455183257254745
        lats[577] = 49.384884490650613
        lats[578] = 49.314585724037435
        lats[579] = 49.244286957415234
        lats[580] = 49.173988190784094
        lats[581] = 49.103689424144044
        lats[582] = 49.03339065749514
        lats[583] = 48.963091890837418
        lats[584] = 48.892793124170929
        lats[585] = 48.822494357495721
        lats[586] = 48.752195590811837
        lats[587] = 48.681896824119335
        lats[588] = 48.611598057418242
        lats[589] = 48.541299290708608
        lats[590] = 48.47100052399049
        lats[591] = 48.400701757263917
        lats[592] = 48.330402990528938
        lats[593] = 48.260104223785596
        lats[594] = 48.189805457033941
        lats[595] = 48.119506690274015
        lats[596] = 48.049207923505868
        lats[597] = 47.978909156729507
        lats[598] = 47.908610389945018
        lats[599] = 47.838311623152421
        lats[600] = 47.76801285635176
        lats[601] = 47.697714089543084
        lats[602] = 47.627415322726435
        lats[603] = 47.557116555901828
        lats[604] = 47.486817789069342
        lats[605] = 47.416519022228997
        lats[606] = 47.346220255380835
        lats[607] = 47.275921488524894
        lats[608] = 47.205622721661214
        lats[609] = 47.13532395478984
        lats[610] = 47.065025187910805
        lats[611] = 46.994726421024154
        lats[612] = 46.924427654129929
        lats[613] = 46.85412888722815
        lats[614] = 46.783830120318882
        lats[615] = 46.713531353402139
        lats[616] = 46.643232586477971
        lats[617] = 46.572933819546414
        lats[618] = 46.502635052607502
        lats[619] = 46.432336285661272
        lats[620] = 46.362037518707766
        lats[621] = 46.291738751747012
        lats[622] = 46.221439984779053
        lats[623] = 46.151141217803925
        lats[624] = 46.080842450821663
        lats[625] = 46.01054368383231
        lats[626] = 45.94024491683588
        lats[627] = 45.869946149832437
        lats[628] = 45.799647382821995
        lats[629] = 45.729348615804589
        lats[630] = 45.659049848780263
        lats[631] = 45.588751081749038
        lats[632] = 45.51845231471097
        lats[633] = 45.448153547666081
        lats[634] = 45.377854780614399
        lats[635] = 45.30755601355596
        lats[636] = 45.237257246490813
        lats[637] = 45.166958479418959
        lats[638] = 45.096659712340461
        lats[639] = 45.026360945255341
        lats[640] = 44.956062178163634
        lats[641] = 44.885763411065362
        lats[642] = 44.81546464396056
        lats[643] = 44.745165876849271
        lats[644] = 44.674867109731515
        lats[645] = 44.604568342607337
        lats[646] = 44.534269575476756
        lats[647] = 44.463970808339802
        lats[648] = 44.39367204119651
        lats[649] = 44.323373274046915
        lats[650] = 44.253074506891046
        lats[651] = 44.182775739728925
        lats[652] = 44.112476972560586
        lats[653] = 44.042178205386072
        lats[654] = 43.971879438205391
        lats[655] = 43.9015806710186
        lats[656] = 43.831281903825705
        lats[657] = 43.760983136626741
        lats[658] = 43.690684369421732
        lats[659] = 43.620385602210717
        lats[660] = 43.550086834993728
        lats[661] = 43.479788067770777
        lats[662] = 43.409489300541907
        lats[663] = 43.339190533307139
        lats[664] = 43.26889176606651
        lats[665] = 43.19859299882004
        lats[666] = 43.128294231567757
        lats[667] = 43.057995464309691
        lats[668] = 42.987696697045862
        lats[669] = 42.917397929776307
        lats[670] = 42.847099162501053
        lats[671] = 42.776800395220121
        lats[672] = 42.706501627933541
        lats[673] = 42.63620286064134
        lats[674] = 42.565904093343548
        lats[675] = 42.495605326040177
        lats[676] = 42.425306558731272
        lats[677] = 42.355007791416853
        lats[678] = 42.284709024096927
        lats[679] = 42.214410256771551
        lats[680] = 42.144111489440725
        lats[681] = 42.073812722104492
        lats[682] = 42.003513954762873
        lats[683] = 41.933215187415882
        lats[684] = 41.862916420063563
        lats[685] = 41.792617652705921
        lats[686] = 41.722318885343
        lats[687] = 41.6520201179748
        lats[688] = 41.581721350601363
        lats[689] = 41.511422583222718
        lats[690] = 41.441123815838885
        lats[691] = 41.370825048449873
        lats[692] = 41.300526281055724
        lats[693] = 41.230227513656445
        lats[694] = 41.159928746252085
        lats[695] = 41.089629978842645
        lats[696] = 41.01933121142816
        lats[697] = 40.949032444008644
        lats[698] = 40.878733676584126
        lats[699] = 40.808434909154634
        lats[700] = 40.738136141720176
        lats[701] = 40.667837374280786
        lats[702] = 40.597538606836487
        lats[703] = 40.527239839387299
        lats[704] = 40.456941071933244
        lats[705] = 40.386642304474343
        lats[706] = 40.316343537010617
        lats[707] = 40.246044769542102
        lats[708] = 40.175746002068806
        lats[709] = 40.105447234590748
        lats[710] = 40.035148467107952
        lats[711] = 39.964849699620437
        lats[712] = 39.894550932128247
        lats[713] = 39.824252164631375
        lats[714] = 39.753953397129855
        lats[715] = 39.683654629623703
        lats[716] = 39.613355862112947
        lats[717] = 39.543057094597607
        lats[718] = 39.472758327077692
        lats[719] = 39.402459559553229
        lats[720] = 39.332160792024254
        lats[721] = 39.261862024490775
        lats[722] = 39.191563256952804
        lats[723] = 39.121264489410365
        lats[724] = 39.050965721863491
        lats[725] = 38.980666954312184
        lats[726] = 38.910368186756479
        lats[727] = 38.840069419196389
        lats[728] = 38.769770651631937
        lats[729] = 38.699471884063136
        lats[730] = 38.629173116490001
        lats[731] = 38.558874348912568
        lats[732] = 38.488575581330842
        lats[733] = 38.418276813744846
        lats[734] = 38.347978046154608
        lats[735] = 38.277679278560143
        lats[736] = 38.20738051096145
        lats[737] = 38.137081743358586
        lats[738] = 38.066782975751536
        lats[739] = 37.99648420814033
        lats[740] = 37.926185440524989
        lats[741] = 37.855886672905527
        lats[742] = 37.785587905281965
        lats[743] = 37.715289137654317
        lats[744] = 37.644990370022605
        lats[745] = 37.574691602386856
        lats[746] = 37.504392834747065
        lats[747] = 37.434094067103274
        lats[748] = 37.363795299455489
        lats[749] = 37.293496531803719
        lats[750] = 37.223197764147997
        lats[751] = 37.152898996488332
        lats[752] = 37.082600228824752
        lats[753] = 37.012301461157264
        lats[754] = 36.942002693485883
        lats[755] = 36.871703925810628
        lats[756] = 36.801405158131523
        lats[757] = 36.731106390448581
        lats[758] = 36.660807622761808
        lats[759] = 36.590508855071242
        lats[760] = 36.520210087376888
        lats[761] = 36.449911319678755
        lats[762] = 36.379612551976876
        lats[763] = 36.309313784271254
        lats[764] = 36.239015016561908
        lats[765] = 36.16871624884886
        lats[766] = 36.098417481132117
        lats[767] = 36.028118713411708
        lats[768] = 35.957819945687639
        lats[769] = 35.887521177959933
        lats[770] = 35.817222410228595
        lats[771] = 35.746923642493655
        lats[772] = 35.676624874755113
        lats[773] = 35.606326107012997
        lats[774] = 35.536027339267314
        lats[775] = 35.465728571518085
        lats[776] = 35.395429803765317
        lats[777] = 35.325131036009047
        lats[778] = 35.254832268249267
        lats[779] = 35.184533500486005
        lats[780] = 35.114234732719261
        lats[781] = 35.043935964949064
        lats[782] = 34.973637197175435
        lats[783] = 34.903338429398374
        lats[784] = 34.833039661617903
        lats[785] = 34.762740893834028
        lats[786] = 34.692442126046771
        lats[787] = 34.622143358256153
        lats[788] = 34.551844590462188
        lats[789] = 34.481545822664863
        lats[790] = 34.411247054864234
        lats[791] = 34.340948287060286
        lats[792] = 34.270649519253041
        lats[793] = 34.200350751442521
        lats[794] = 34.130051983628725
        lats[795] = 34.059753215811682
        lats[796] = 33.989454447991392
        lats[797] = 33.919155680167876
        lats[798] = 33.848856912341155
        lats[799] = 33.778558144511237
        lats[800] = 33.708259376678136
        lats[801] = 33.637960608841851
        lats[802] = 33.567661841002426
        lats[803] = 33.497363073159853
        lats[804] = 33.42706430531414
        lats[805] = 33.356765537465314
        lats[806] = 33.286466769613391
        lats[807] = 33.216168001758369
        lats[808] = 33.145869233900278
        lats[809] = 33.075570466039117
        lats[810] = 33.005271698174909
        lats[811] = 32.934972930307666
        lats[812] = 32.864674162437396
        lats[813] = 32.794375394564113
        lats[814] = 32.724076626687825
        lats[815] = 32.653777858808567
        lats[816] = 32.583479090926325
        lats[817] = 32.513180323041112
        lats[818] = 32.442881555152965
        lats[819] = 32.372582787261891
        lats[820] = 32.302284019367875
        lats[821] = 32.231985251470959
        lats[822] = 32.161686483571145
        lats[823] = 32.091387715668439
        lats[824] = 32.021088947762863
        lats[825] = 31.950790179854422
        lats[826] = 31.880491411943137
        lats[827] = 31.810192644029012
        lats[828] = 31.739893876112063
        lats[829] = 31.669595108192297
        lats[830] = 31.599296340269738
        lats[831] = 31.528997572344384
        lats[832] = 31.458698804416255
        lats[833] = 31.388400036485361
        lats[834] = 31.318101268551715
        lats[835] = 31.247802500615318
        lats[836] = 31.177503732676204
        lats[837] = 31.107204964734358
        lats[838] = 31.036906196789811
        lats[839] = 30.966607428842572
        lats[840] = 30.896308660892647
        lats[841] = 30.826009892940046
        lats[842] = 30.755711124984781
        lats[843] = 30.685412357026873
        lats[844] = 30.615113589066322
        lats[845] = 30.544814821103138
        lats[846] = 30.47451605313735
        lats[847] = 30.404217285168947
        lats[848] = 30.333918517197947
        lats[849] = 30.263619749224372
        lats[850] = 30.19332098124822
        lats[851] = 30.123022213269511
        lats[852] = 30.052723445288244
        lats[853] = 29.98242467730444
        lats[854] = 29.91212590931811
        lats[855] = 29.841827141329258
        lats[856] = 29.771528373337894
        lats[857] = 29.701229605344039
        lats[858] = 29.630930837347698
        lats[859] = 29.560632069348884
        lats[860] = 29.490333301347597
        lats[861] = 29.420034533343859
        lats[862] = 29.349735765337677
        lats[863] = 29.279436997329057
        lats[864] = 29.209138229318015
        lats[865] = 29.138839461304556
        lats[866] = 29.068540693288696
        lats[867] = 28.998241925270449
        lats[868] = 28.927943157249814
        lats[869] = 28.857644389226806
        lats[870] = 28.787345621201432
        lats[871] = 28.717046853173709
        lats[872] = 28.646748085143642
        lats[873] = 28.576449317111244
        lats[874] = 28.506150549076519
        lats[875] = 28.435851781039485
        lats[876] = 28.365553013000145
        lats[877] = 28.29525424495851
        lats[878] = 28.224955476914594
        lats[879] = 28.154656708868405
        lats[880] = 28.084357940819952
        lats[881] = 28.014059172769244
        lats[882] = 27.94376040471629
        lats[883] = 27.873461636661098
        lats[884] = 27.803162868603682
        lats[885] = 27.732864100544052
        lats[886] = 27.662565332482213
        lats[887] = 27.592266564418171
        lats[888] = 27.521967796351948
        lats[889] = 27.451669028283543
        lats[890] = 27.381370260212968
        lats[891] = 27.311071492140236
        lats[892] = 27.240772724065348
        lats[893] = 27.170473955988321
        lats[894] = 27.100175187909159
        lats[895] = 27.029876419827872
        lats[896] = 26.959577651744471
        lats[897] = 26.889278883658971
        lats[898] = 26.818980115571364
        lats[899] = 26.748681347481678
        lats[900] = 26.678382579389908
        lats[901] = 26.608083811296069
        lats[902] = 26.53778504320017
        lats[903] = 26.467486275102218
        lats[904] = 26.397187507002222
        lats[905] = 26.326888738900195
        lats[906] = 26.256589970796135
        lats[907] = 26.186291202690064
        lats[908] = 26.115992434581983
        lats[909] = 26.045693666471902
        lats[910] = 25.975394898359827
        lats[911] = 25.90509613024577
        lats[912] = 25.834797362129745
        lats[913] = 25.764498594011751
        lats[914] = 25.694199825891793
        lats[915] = 25.623901057769892
        lats[916] = 25.553602289646051
        lats[917] = 25.483303521520277
        lats[918] = 25.413004753392578
        lats[919] = 25.342705985262967
        lats[920] = 25.272407217131445
        lats[921] = 25.202108448998025
        lats[922] = 25.13180968086272
        lats[923] = 25.061510912725527
        lats[924] = 24.991212144586456
        lats[925] = 24.920913376445526
        lats[926] = 24.850614608302738
        lats[927] = 24.780315840158096
        lats[928] = 24.710017072011613
        lats[929] = 24.639718303863294
        lats[930] = 24.569419535713152
        lats[931] = 24.499120767561195
        lats[932] = 24.428821999407425
        lats[933] = 24.358523231251851
        lats[934] = 24.288224463094483
        lats[935] = 24.217925694935328
        lats[936] = 24.1476269267744
        lats[937] = 24.077328158611696
        lats[938] = 24.007029390447226
        lats[939] = 23.936730622281004
        lats[940] = 23.866431854113038
        lats[941] = 23.796133085943328
        lats[942] = 23.725834317771888
        lats[943] = 23.655535549598721
        lats[944] = 23.585236781423838
        lats[945] = 23.514938013247242
        lats[946] = 23.444639245068949
        lats[947] = 23.374340476888957
        lats[948] = 23.304041708707278
        lats[949] = 23.233742940523921
        lats[950] = 23.163444172338895
        lats[951] = 23.0931454041522
        lats[952] = 23.022846635963852
        lats[953] = 22.952547867773848
        lats[954] = 22.882249099582204
        lats[955] = 22.811950331388925
        lats[956] = 22.741651563194019
        lats[957] = 22.671352794997489
        lats[958] = 22.60105402679935
        lats[959] = 22.530755258599601
        lats[960] = 22.460456490398254
        lats[961] = 22.390157722195315
        lats[962] = 22.319858953990789
        lats[963] = 22.249560185784691
        lats[964] = 22.179261417577013
        lats[965] = 22.108962649367779
        lats[966] = 22.038663881156989
        lats[967] = 21.968365112944642
        lats[968] = 21.898066344730758
        lats[969] = 21.827767576515338
        lats[970] = 21.757468808298391
        lats[971] = 21.687170040079913
        lats[972] = 21.616871271859928
        lats[973] = 21.546572503638437
        lats[974] = 21.47627373541544
        lats[975] = 21.40597496719095
        lats[976] = 21.335676198964972
        lats[977] = 21.265377430737512
        lats[978] = 21.195078662508585
        lats[979] = 21.124779894278181
        lats[980] = 21.054481126046323
        lats[981] = 20.984182357813012
        lats[982] = 20.913883589578251
        lats[983] = 20.843584821342048
        lats[984] = 20.773286053104417
        lats[985] = 20.702987284865355
        lats[986] = 20.632688516624874
        lats[987] = 20.562389748382977
        lats[988] = 20.492090980139672
        lats[989] = 20.421792211894967
        lats[990] = 20.35149344364887
        lats[991] = 20.28119467540138
        lats[992] = 20.210895907152516
        lats[993] = 20.140597138902272
        lats[994] = 20.070298370650661
        lats[995] = 19.999999602397686
        lats[996] = 19.929700834143357
        lats[997] = 19.859402065887682
        lats[998] = 19.789103297630657
        lats[999] = 19.718804529372303
        lats[1000] = 19.648505761112613
        lats[1001] = 19.578206992851602
        lats[1002] = 19.507908224589269
        lats[1003] = 19.437609456325632
        lats[1004] = 19.367310688060684
        lats[1005] = 19.297011919794439
        lats[1006] = 19.226713151526898
        lats[1007] = 19.15641438325807
        lats[1008] = 19.086115614987968
        lats[1009] = 19.015816846716586
        lats[1010] = 18.945518078443939
        lats[1011] = 18.875219310170031
        lats[1012] = 18.804920541894862
        lats[1013] = 18.734621773618446
        lats[1014] = 18.664323005340787
        lats[1015] = 18.594024237061891
        lats[1016] = 18.523725468781763
        lats[1017] = 18.453426700500408
        lats[1018] = 18.383127932217832
        lats[1019] = 18.312829163934047
        lats[1020] = 18.242530395649048
        lats[1021] = 18.172231627362851
        lats[1022] = 18.101932859075458
        lats[1023] = 18.031634090786874
        lats[1024] = 17.96133532249711
        lats[1025] = 17.89103655420616
        lats[1026] = 17.820737785914044
        lats[1027] = 17.75043901762076
        lats[1028] = 17.680140249326314
        lats[1029] = 17.60984148103071
        lats[1030] = 17.539542712733962
        lats[1031] = 17.469243944436066
        lats[1032] = 17.39894517613704
        lats[1033] = 17.328646407836878
        lats[1034] = 17.258347639535586
        lats[1035] = 17.188048871233182
        lats[1036] = 17.117750102929655
        lats[1037] = 17.04745133462502
        lats[1038] = 16.977152566319283
        lats[1039] = 16.906853798012452
        lats[1040] = 16.836555029704527
        lats[1041] = 16.766256261395515
        lats[1042] = 16.69595749308542
        lats[1043] = 16.625658724774254
        lats[1044] = 16.555359956462013
        lats[1045] = 16.485061188148713
        lats[1046] = 16.41476241983435
        lats[1047] = 16.344463651518936
        lats[1048] = 16.274164883202477
        lats[1049] = 16.203866114884974
        lats[1050] = 16.133567346566434
        lats[1051] = 16.063268578246863
        lats[1052] = 15.992969809926265
        lats[1053] = 15.922671041604652
        lats[1054] = 15.852372273282016
        lats[1055] = 15.78207350495838
        lats[1056] = 15.711774736633735
        lats[1057] = 15.641475968308091
        lats[1058] = 15.571177199981456
        lats[1059] = 15.500878431653829
        lats[1060] = 15.430579663325226
        lats[1061] = 15.360280894995643
        lats[1062] = 15.289982126665089
        lats[1063] = 15.219683358333569
        lats[1064] = 15.149384590001089
        lats[1065] = 15.07908582166765
        lats[1066] = 15.008787053333259
        lats[1067] = 14.938488284997929
        lats[1068] = 14.868189516661655
        lats[1069] = 14.797890748324447
        lats[1070] = 14.727591979986309
        lats[1071] = 14.657293211647247
        lats[1072] = 14.586994443307265
        lats[1073] = 14.516695674966371
        lats[1074] = 14.446396906624567
        lats[1075] = 14.376098138281863
        lats[1076] = 14.305799369938256
        lats[1077] = 14.23550060159376
        lats[1078] = 14.165201833248371
        lats[1079] = 14.0949030649021
        lats[1080] = 14.024604296554955
        lats[1081] = 13.954305528206934
        lats[1082] = 13.884006759858046
        lats[1083] = 13.813707991508297
        lats[1084] = 13.743409223157688
        lats[1085] = 13.673110454806226
        lats[1086] = 13.602811686453919
        lats[1087] = 13.532512918100766
        lats[1088] = 13.46221414974678
        lats[1089] = 13.391915381391959
        lats[1090] = 13.32161661303631
        lats[1091] = 13.251317844679837
        lats[1092] = 13.181019076322551
        lats[1093] = 13.110720307964451
        lats[1094] = 13.040421539605545
        lats[1095] = 12.970122771245832
        lats[1096] = 12.899824002885323
        lats[1097] = 12.829525234524022
        lats[1098] = 12.759226466161934
        lats[1099] = 12.688927697799061
        lats[1100] = 12.618628929435411
        lats[1101] = 12.548330161070988
        lats[1102] = 12.478031392705796
        lats[1103] = 12.407732624339841
        lats[1104] = 12.337433855973126
        lats[1105] = 12.267135087605659
        lats[1106] = 12.196836319237443
        lats[1107] = 12.126537550868482
        lats[1108] = 12.056238782498781
        lats[1109] = 11.985940014128348
        lats[1110] = 11.915641245757183
        lats[1111] = 11.845342477385294
        lats[1112] = 11.775043709012685
        lats[1113] = 11.704744940639358
        lats[1114] = 11.634446172265324
        lats[1115] = 11.564147403890583
        lats[1116] = 11.493848635515141
        lats[1117] = 11.423549867139002
        lats[1118] = 11.35325109876217
        lats[1119] = 11.282952330384653
        lats[1120] = 11.212653562006453
        lats[1121] = 11.142354793627575
        lats[1122] = 11.072056025248026
        lats[1123] = 11.001757256867807
        lats[1124] = 10.931458488486923
        lats[1125] = 10.861159720105382
        lats[1126] = 10.790860951723188
        lats[1127] = 10.720562183340341
        lats[1128] = 10.65026341495685
        lats[1129] = 10.579964646572719
        lats[1130] = 10.509665878187954
        lats[1131] = 10.439367109802557
        lats[1132] = 10.369068341416533
        lats[1133] = 10.298769573029887
        lats[1134] = 10.228470804642624
        lats[1135] = 10.158172036254747
        lats[1136] = 10.087873267866264
        lats[1137] = 10.017574499477174
        lats[1138] = 9.9472757310874869
        lats[1139] = 9.8769769626972046
        lats[1140] = 9.8066781943063344
        lats[1141] = 9.7363794259148779
        lats[1142] = 9.6660806575228388
        lats[1143] = 9.5957818891302242
        lats[1144] = 9.5254831207370376
        lats[1145] = 9.4551843523432826
        lats[1146] = 9.3848855839489662
        lats[1147] = 9.3145868155540921
        lats[1148] = 9.2442880471586619
        lats[1149] = 9.1739892787626829
        lats[1150] = 9.1036905103661585
        lats[1151] = 9.0333917419690941
        lats[1152] = 8.963092973571495
        lats[1153] = 8.8927942051733631
        lats[1154] = 8.8224954367747017
        lats[1155] = 8.7521966683755217
        lats[1156] = 8.6818978999758194
        lats[1157] = 8.6115991315756055
        lats[1158] = 8.5413003631748801
        lats[1159] = 8.4710015947736537
        lats[1160] = 8.4007028263719228
        lats[1161] = 8.3304040579696963
        lats[1162] = 8.2601052895669778
        lats[1163] = 8.1898065211637725
        lats[1164] = 8.1195077527600841
        lats[1165] = 8.049208984355916
        lats[1166] = 7.9789102159512737
        lats[1167] = 7.9086114475461606
        lats[1168] = 7.8383126791405831
        lats[1169] = 7.7680139107345463
        lats[1170] = 7.6977151423280494
        lats[1171] = 7.6274163739210996
        lats[1172] = 7.557117605513703
        lats[1173] = 7.4868188371058624
        lats[1174] = 7.4165200686975803
        lats[1175] = 7.3462213002888648
        lats[1176] = 7.2759225318797176
        lats[1177] = 7.2056237634701441
        lats[1178] = 7.1353249950601469
        lats[1179] = 7.0650262266497315
        lats[1180] = 6.994727458238903
        lats[1181] = 6.924428689827665
        lats[1182] = 6.8541299214160212
        lats[1183] = 6.7838311530039768
        lats[1184] = 6.7135323845915353
        lats[1185] = 6.6432336161787013
        lats[1186] = 6.5729348477654792
        lats[1187] = 6.5026360793518734
        lats[1188] = 6.4323373109378874
        lats[1189] = 6.3620385425235257
        lats[1190] = 6.2917397741087928
        lats[1191] = 6.2214410056936931
        lats[1192] = 6.151142237278231
        lats[1193] = 6.0808434688624091
        lats[1194] = 6.0105447004462347
        lats[1195] = 5.9402459320297085
        lats[1196] = 5.869947163612836
        lats[1197] = 5.7996483951956233
        lats[1198] = 5.729349626778073
        lats[1199] = 5.6590508583601888
        lats[1200] = 5.5887520899419751
        lats[1201] = 5.5184533215234373
        lats[1202] = 5.4481545531045787
        lats[1203] = 5.3778557846854023
        lats[1204] = 5.3075570162659149
        lats[1205] = 5.2372582478461194
        lats[1206] = 5.1669594794260192
        lats[1207] = 5.0966607110056197
        lats[1208] = 5.0263619425849244
        lats[1209] = 4.9560631741639369
        lats[1210] = 4.8857644057426626
        lats[1211] = 4.8154656373211049
        lats[1212] = 4.7451668688992683
        lats[1213] = 4.6748681004771564
        lats[1214] = 4.6045693320547736
        lats[1215] = 4.5342705636321252
        lats[1216] = 4.4639717952092139
        lats[1217] = 4.3936730267860451
        lats[1218] = 4.3233742583626205
        lats[1219] = 4.2530754899389471
        lats[1220] = 4.1827767215150269
        lats[1221] = 4.1124779530908659
        lats[1222] = 4.0421791846664661
        lats[1223] = 3.9718804162418326
        lats[1224] = 3.90158164781697
        lats[1225] = 3.8312828793918823
        lats[1226] = 3.7609841109665734
        lats[1227] = 3.6906853425410477
        lats[1228] = 3.6203865741153085
        lats[1229] = 3.5500878056893601
        lats[1230] = 3.4797890372632065
        lats[1231] = 3.4094902688368531
        lats[1232] = 3.339191500410303
        lats[1233] = 3.2688927319835597
        lats[1234] = 3.1985939635566285
        lats[1235] = 3.1282951951295126
        lats[1236] = 3.0579964267022164
        lats[1237] = 2.9876976582747439
        lats[1238] = 2.9173988898470999
        lats[1239] = 2.8471001214192873
        lats[1240] = 2.7768013529913107
        lats[1241] = 2.7065025845631743
        lats[1242] = 2.6362038161348824
        lats[1243] = 2.5659050477064382
        lats[1244] = 2.4956062792778466
        lats[1245] = 2.4253075108491116
        lats[1246] = 2.3550087424202366
        lats[1247] = 2.2847099739912267
        lats[1248] = 2.2144112055620848
        lats[1249] = 2.1441124371328155
        lats[1250] = 2.0738136687034232
        lats[1251] = 2.0035149002739114
        lats[1252] = 1.9332161318442849
        lats[1253] = 1.8629173634145471
        lats[1254] = 1.792618594984702
        lats[1255] = 1.7223198265547539
        lats[1256] = 1.6520210581247066
        lats[1257] = 1.5817222896945646
        lats[1258] = 1.5114235212643317
        lats[1259] = 1.4411247528340119
        lats[1260] = 1.3708259844036093
        lats[1261] = 1.300527215973128
        lats[1262] = 1.2302284475425722
        lats[1263] = 1.1599296791119456
        lats[1264] = 1.0896309106812523
        lats[1265] = 1.0193321422504964
        lats[1266] = 0.949033373819682
        lats[1267] = 0.87873460538881287
        lats[1268] = 0.80843583695789356
        lats[1269] = 0.73813706852692773
        lats[1270] = 0.66783830009591949
        lats[1271] = 0.59753953166487306
        lats[1272] = 0.52724076323379232
        lats[1273] = 0.45694199480268116
        lats[1274] = 0.3866432263715438
        lats[1275] = 0.31634445794038429
        lats[1276] = 0.24604568950920663
        lats[1277] = 0.17574692107801482
        lats[1278] = 0.10544815264681295
        lats[1279] = 0.035149384215604956
        lats[1280] = -0.035149384215604956
        lats[1281] = -0.10544815264681295
        lats[1282] = -0.17574692107801482
        lats[1283] = -0.24604568950920663
        lats[1284] = -0.31634445794038429
        lats[1285] = -0.3866432263715438
        lats[1286] = -0.45694199480268116
        lats[1287] = -0.52724076323379232
        lats[1288] = -0.59753953166487306
        lats[1289] = -0.66783830009591949
        lats[1290] = -0.73813706852692773
        lats[1291] = -0.80843583695789356
        lats[1292] = -0.87873460538881287
        lats[1293] = -0.949033373819682
        lats[1294] = -1.0193321422504964
        lats[1295] = -1.0896309106812523
        lats[1296] = -1.1599296791119456
        lats[1297] = -1.2302284475425722
        lats[1298] = -1.300527215973128
        lats[1299] = -1.3708259844036093
        lats[1300] = -1.4411247528340119
        lats[1301] = -1.5114235212643317
        lats[1302] = -1.5817222896945646
        lats[1303] = -1.6520210581247066
        lats[1304] = -1.7223198265547539
        lats[1305] = -1.792618594984702
        lats[1306] = -1.8629173634145471
        lats[1307] = -1.9332161318442849
        lats[1308] = -2.0035149002739114
        lats[1309] = -2.0738136687034232
        lats[1310] = -2.1441124371328155
        lats[1311] = -2.2144112055620848
        lats[1312] = -2.2847099739912267
        lats[1313] = -2.3550087424202366
        lats[1314] = -2.4253075108491116
        lats[1315] = -2.4956062792778466
        lats[1316] = -2.5659050477064382
        lats[1317] = -2.6362038161348824
        lats[1318] = -2.7065025845631743
        lats[1319] = -2.7768013529913107
        lats[1320] = -2.8471001214192873
        lats[1321] = -2.9173988898470999
        lats[1322] = -2.9876976582747439
        lats[1323] = -3.0579964267022164
        lats[1324] = -3.1282951951295126
        lats[1325] = -3.1985939635566285
        lats[1326] = -3.2688927319835597
        lats[1327] = -3.339191500410303
        lats[1328] = -3.4094902688368531
        lats[1329] = -3.4797890372632065
        lats[1330] = -3.5500878056893601
        lats[1331] = -3.6203865741153085
        lats[1332] = -3.6906853425410477
        lats[1333] = -3.7609841109665734
        lats[1334] = -3.8312828793918823
        lats[1335] = -3.90158164781697
        lats[1336] = -3.9718804162418326
        lats[1337] = -4.0421791846664661
        lats[1338] = -4.1124779530908659
        lats[1339] = -4.1827767215150269
        lats[1340] = -4.2530754899389471
        lats[1341] = -4.3233742583626205
        lats[1342] = -4.3936730267860451
        lats[1343] = -4.4639717952092139
        lats[1344] = -4.5342705636321252
        lats[1345] = -4.6045693320547736
        lats[1346] = -4.6748681004771564
        lats[1347] = -4.7451668688992683
        lats[1348] = -4.8154656373211049
        lats[1349] = -4.8857644057426626
        lats[1350] = -4.9560631741639369
        lats[1351] = -5.0263619425849244
        lats[1352] = -5.0966607110056197
        lats[1353] = -5.1669594794260192
        lats[1354] = -5.2372582478461194
        lats[1355] = -5.3075570162659149
        lats[1356] = -5.3778557846854023
        lats[1357] = -5.4481545531045787
        lats[1358] = -5.5184533215234373
        lats[1359] = -5.5887520899419751
        lats[1360] = -5.6590508583601888
        lats[1361] = -5.729349626778073
        lats[1362] = -5.7996483951956233
        lats[1363] = -5.869947163612836
        lats[1364] = -5.9402459320297085
        lats[1365] = -6.0105447004462347
        lats[1366] = -6.0808434688624091
        lats[1367] = -6.151142237278231
        lats[1368] = -6.2214410056936931
        lats[1369] = -6.2917397741087928
        lats[1370] = -6.3620385425235257
        lats[1371] = -6.4323373109378874
        lats[1372] = -6.5026360793518734
        lats[1373] = -6.5729348477654792
        lats[1374] = -6.6432336161787013
        lats[1375] = -6.7135323845915353
        lats[1376] = -6.7838311530039768
        lats[1377] = -6.8541299214160212
        lats[1378] = -6.924428689827665
        lats[1379] = -6.994727458238903
        lats[1380] = -7.0650262266497315
        lats[1381] = -7.1353249950601469
        lats[1382] = -7.2056237634701441
        lats[1383] = -7.2759225318797176
        lats[1384] = -7.3462213002888648
        lats[1385] = -7.4165200686975803
        lats[1386] = -7.4868188371058624
        lats[1387] = -7.557117605513703
        lats[1388] = -7.6274163739210996
        lats[1389] = -7.6977151423280494
        lats[1390] = -7.7680139107345463
        lats[1391] = -7.8383126791405831
        lats[1392] = -7.9086114475461606
        lats[1393] = -7.9789102159512737
        lats[1394] = -8.049208984355916
        lats[1395] = -8.1195077527600841
        lats[1396] = -8.1898065211637725
        lats[1397] = -8.2601052895669778
        lats[1398] = -8.3304040579696963
        lats[1399] = -8.4007028263719228
        lats[1400] = -8.4710015947736537
        lats[1401] = -8.5413003631748801
        lats[1402] = -8.6115991315756055
        lats[1403] = -8.6818978999758194
        lats[1404] = -8.7521966683755217
        lats[1405] = -8.8224954367747017
        lats[1406] = -8.8927942051733631
        lats[1407] = -8.963092973571495
        lats[1408] = -9.0333917419690941
        lats[1409] = -9.1036905103661585
        lats[1410] = -9.1739892787626829
        lats[1411] = -9.2442880471586619
        lats[1412] = -9.3145868155540921
        lats[1413] = -9.3848855839489662
        lats[1414] = -9.4551843523432826
        lats[1415] = -9.5254831207370376
        lats[1416] = -9.5957818891302242
        lats[1417] = -9.6660806575228388
        lats[1418] = -9.7363794259148779
        lats[1419] = -9.8066781943063344
        lats[1420] = -9.8769769626972046
        lats[1421] = -9.9472757310874869
        lats[1422] = -10.017574499477174
        lats[1423] = -10.087873267866264
        lats[1424] = -10.158172036254747
        lats[1425] = -10.228470804642624
        lats[1426] = -10.298769573029887
        lats[1427] = -10.369068341416533
        lats[1428] = -10.439367109802557
        lats[1429] = -10.509665878187954
        lats[1430] = -10.579964646572719
        lats[1431] = -10.65026341495685
        lats[1432] = -10.720562183340341
        lats[1433] = -10.790860951723188
        lats[1434] = -10.861159720105382
        lats[1435] = -10.931458488486923
        lats[1436] = -11.001757256867807
        lats[1437] = -11.072056025248026
        lats[1438] = -11.142354793627575
        lats[1439] = -11.212653562006453
        lats[1440] = -11.282952330384653
        lats[1441] = -11.35325109876217
        lats[1442] = -11.423549867139002
        lats[1443] = -11.493848635515141
        lats[1444] = -11.564147403890583
        lats[1445] = -11.634446172265324
        lats[1446] = -11.704744940639358
        lats[1447] = -11.775043709012685
        lats[1448] = -11.845342477385294
        lats[1449] = -11.915641245757183
        lats[1450] = -11.985940014128348
        lats[1451] = -12.056238782498781
        lats[1452] = -12.126537550868482
        lats[1453] = -12.196836319237443
        lats[1454] = -12.267135087605659
        lats[1455] = -12.337433855973126
        lats[1456] = -12.407732624339841
        lats[1457] = -12.478031392705796
        lats[1458] = -12.548330161070988
        lats[1459] = -12.618628929435411
        lats[1460] = -12.688927697799061
        lats[1461] = -12.759226466161934
        lats[1462] = -12.829525234524022
        lats[1463] = -12.899824002885323
        lats[1464] = -12.970122771245832
        lats[1465] = -13.040421539605545
        lats[1466] = -13.110720307964451
        lats[1467] = -13.181019076322551
        lats[1468] = -13.251317844679837
        lats[1469] = -13.32161661303631
        lats[1470] = -13.391915381391959
        lats[1471] = -13.46221414974678
        lats[1472] = -13.532512918100766
        lats[1473] = -13.602811686453919
        lats[1474] = -13.673110454806226
        lats[1475] = -13.743409223157688
        lats[1476] = -13.813707991508297
        lats[1477] = -13.884006759858046
        lats[1478] = -13.954305528206934
        lats[1479] = -14.024604296554955
        lats[1480] = -14.0949030649021
        lats[1481] = -14.165201833248371
        lats[1482] = -14.23550060159376
        lats[1483] = -14.305799369938256
        lats[1484] = -14.376098138281863
        lats[1485] = -14.446396906624567
        lats[1486] = -14.516695674966371
        lats[1487] = -14.586994443307265
        lats[1488] = -14.657293211647247
        lats[1489] = -14.727591979986309
        lats[1490] = -14.797890748324447
        lats[1491] = -14.868189516661655
        lats[1492] = -14.938488284997929
        lats[1493] = -15.008787053333259
        lats[1494] = -15.07908582166765
        lats[1495] = -15.149384590001089
        lats[1496] = -15.219683358333569
        lats[1497] = -15.289982126665089
        lats[1498] = -15.360280894995643
        lats[1499] = -15.430579663325226
        lats[1500] = -15.500878431653829
        lats[1501] = -15.571177199981456
        lats[1502] = -15.641475968308091
        lats[1503] = -15.711774736633735
        lats[1504] = -15.78207350495838
        lats[1505] = -15.852372273282016
        lats[1506] = -15.922671041604652
        lats[1507] = -15.992969809926265
        lats[1508] = -16.063268578246863
        lats[1509] = -16.133567346566434
        lats[1510] = -16.203866114884974
        lats[1511] = -16.274164883202477
        lats[1512] = -16.344463651518936
        lats[1513] = -16.41476241983435
        lats[1514] = -16.485061188148713
        lats[1515] = -16.555359956462013
        lats[1516] = -16.625658724774254
        lats[1517] = -16.69595749308542
        lats[1518] = -16.766256261395515
        lats[1519] = -16.836555029704527
        lats[1520] = -16.906853798012452
        lats[1521] = -16.977152566319283
        lats[1522] = -17.04745133462502
        lats[1523] = -17.117750102929655
        lats[1524] = -17.188048871233182
        lats[1525] = -17.258347639535586
        lats[1526] = -17.328646407836878
        lats[1527] = -17.39894517613704
        lats[1528] = -17.469243944436066
        lats[1529] = -17.539542712733962
        lats[1530] = -17.60984148103071
        lats[1531] = -17.680140249326314
        lats[1532] = -17.75043901762076
        lats[1533] = -17.820737785914044
        lats[1534] = -17.89103655420616
        lats[1535] = -17.96133532249711
        lats[1536] = -18.031634090786874
        lats[1537] = -18.101932859075458
        lats[1538] = -18.172231627362851
        lats[1539] = -18.242530395649048
        lats[1540] = -18.312829163934047
        lats[1541] = -18.383127932217832
        lats[1542] = -18.453426700500408
        lats[1543] = -18.523725468781763
        lats[1544] = -18.594024237061891
        lats[1545] = -18.664323005340787
        lats[1546] = -18.734621773618446
        lats[1547] = -18.804920541894862
        lats[1548] = -18.875219310170031
        lats[1549] = -18.945518078443939
        lats[1550] = -19.015816846716586
        lats[1551] = -19.086115614987968
        lats[1552] = -19.15641438325807
        lats[1553] = -19.226713151526898
        lats[1554] = -19.297011919794439
        lats[1555] = -19.367310688060684
        lats[1556] = -19.437609456325632
        lats[1557] = -19.507908224589269
        lats[1558] = -19.578206992851602
        lats[1559] = -19.648505761112613
        lats[1560] = -19.718804529372303
        lats[1561] = -19.789103297630657
        lats[1562] = -19.859402065887682
        lats[1563] = -19.929700834143357
        lats[1564] = -19.999999602397686
        lats[1565] = -20.070298370650661
        lats[1566] = -20.140597138902272
        lats[1567] = -20.210895907152516
        lats[1568] = -20.28119467540138
        lats[1569] = -20.35149344364887
        lats[1570] = -20.421792211894967
        lats[1571] = -20.492090980139672
        lats[1572] = -20.562389748382977
        lats[1573] = -20.632688516624874
        lats[1574] = -20.702987284865355
        lats[1575] = -20.773286053104417
        lats[1576] = -20.843584821342048
        lats[1577] = -20.913883589578251
        lats[1578] = -20.984182357813012
        lats[1579] = -21.054481126046323
        lats[1580] = -21.124779894278181
        lats[1581] = -21.195078662508585
        lats[1582] = -21.265377430737512
        lats[1583] = -21.335676198964972
        lats[1584] = -21.40597496719095
        lats[1585] = -21.47627373541544
        lats[1586] = -21.546572503638437
        lats[1587] = -21.616871271859928
        lats[1588] = -21.687170040079913
        lats[1589] = -21.757468808298391
        lats[1590] = -21.827767576515338
        lats[1591] = -21.898066344730758
        lats[1592] = -21.968365112944642
        lats[1593] = -22.038663881156989
        lats[1594] = -22.108962649367779
        lats[1595] = -22.179261417577013
        lats[1596] = -22.249560185784691
        lats[1597] = -22.319858953990789
        lats[1598] = -22.390157722195315
        lats[1599] = -22.460456490398254
        lats[1600] = -22.530755258599601
        lats[1601] = -22.60105402679935
        lats[1602] = -22.671352794997489
        lats[1603] = -22.741651563194019
        lats[1604] = -22.811950331388925
        lats[1605] = -22.882249099582204
        lats[1606] = -22.952547867773848
        lats[1607] = -23.022846635963852
        lats[1608] = -23.0931454041522
        lats[1609] = -23.163444172338895
        lats[1610] = -23.233742940523921
        lats[1611] = -23.304041708707278
        lats[1612] = -23.374340476888957
        lats[1613] = -23.444639245068949
        lats[1614] = -23.514938013247242
        lats[1615] = -23.585236781423838
        lats[1616] = -23.655535549598721
        lats[1617] = -23.725834317771888
        lats[1618] = -23.796133085943328
        lats[1619] = -23.866431854113038
        lats[1620] = -23.936730622281004
        lats[1621] = -24.007029390447226
        lats[1622] = -24.077328158611696
        lats[1623] = -24.1476269267744
        lats[1624] = -24.217925694935328
        lats[1625] = -24.288224463094483
        lats[1626] = -24.358523231251851
        lats[1627] = -24.428821999407425
        lats[1628] = -24.499120767561195
        lats[1629] = -24.569419535713152
        lats[1630] = -24.639718303863294
        lats[1631] = -24.710017072011613
        lats[1632] = -24.780315840158096
        lats[1633] = -24.850614608302738
        lats[1634] = -24.920913376445526
        lats[1635] = -24.991212144586456
        lats[1636] = -25.061510912725527
        lats[1637] = -25.13180968086272
        lats[1638] = -25.202108448998025
        lats[1639] = -25.272407217131445
        lats[1640] = -25.342705985262967
        lats[1641] = -25.413004753392578
        lats[1642] = -25.483303521520277
        lats[1643] = -25.553602289646051
        lats[1644] = -25.623901057769892
        lats[1645] = -25.694199825891793
        lats[1646] = -25.764498594011751
        lats[1647] = -25.834797362129745
        lats[1648] = -25.90509613024577
        lats[1649] = -25.975394898359827
        lats[1650] = -26.045693666471902
        lats[1651] = -26.115992434581983
        lats[1652] = -26.186291202690064
        lats[1653] = -26.256589970796135
        lats[1654] = -26.326888738900195
        lats[1655] = -26.397187507002222
        lats[1656] = -26.467486275102218
        lats[1657] = -26.53778504320017
        lats[1658] = -26.608083811296069
        lats[1659] = -26.678382579389908
        lats[1660] = -26.748681347481678
        lats[1661] = -26.818980115571364
        lats[1662] = -26.889278883658971
        lats[1663] = -26.959577651744471
        lats[1664] = -27.029876419827872
        lats[1665] = -27.100175187909159
        lats[1666] = -27.170473955988321
        lats[1667] = -27.240772724065348
        lats[1668] = -27.311071492140236
        lats[1669] = -27.381370260212968
        lats[1670] = -27.451669028283543
        lats[1671] = -27.521967796351948
        lats[1672] = -27.592266564418171
        lats[1673] = -27.662565332482213
        lats[1674] = -27.732864100544052
        lats[1675] = -27.803162868603682
        lats[1676] = -27.873461636661098
        lats[1677] = -27.94376040471629
        lats[1678] = -28.014059172769244
        lats[1679] = -28.084357940819952
        lats[1680] = -28.154656708868405
        lats[1681] = -28.224955476914594
        lats[1682] = -28.29525424495851
        lats[1683] = -28.365553013000145
        lats[1684] = -28.435851781039485
        lats[1685] = -28.506150549076519
        lats[1686] = -28.576449317111244
        lats[1687] = -28.646748085143642
        lats[1688] = -28.717046853173709
        lats[1689] = -28.787345621201432
        lats[1690] = -28.857644389226806
        lats[1691] = -28.927943157249814
        lats[1692] = -28.998241925270449
        lats[1693] = -29.068540693288696
        lats[1694] = -29.138839461304556
        lats[1695] = -29.209138229318015
        lats[1696] = -29.279436997329057
        lats[1697] = -29.349735765337677
        lats[1698] = -29.420034533343859
        lats[1699] = -29.490333301347597
        lats[1700] = -29.560632069348884
        lats[1701] = -29.630930837347698
        lats[1702] = -29.701229605344039
        lats[1703] = -29.771528373337894
        lats[1704] = -29.841827141329258
        lats[1705] = -29.91212590931811
        lats[1706] = -29.98242467730444
        lats[1707] = -30.052723445288244
        lats[1708] = -30.123022213269511
        lats[1709] = -30.19332098124822
        lats[1710] = -30.263619749224372
        lats[1711] = -30.333918517197947
        lats[1712] = -30.404217285168947
        lats[1713] = -30.47451605313735
        lats[1714] = -30.544814821103138
        lats[1715] = -30.615113589066322
        lats[1716] = -30.685412357026873
        lats[1717] = -30.755711124984781
        lats[1718] = -30.826009892940046
        lats[1719] = -30.896308660892647
        lats[1720] = -30.966607428842572
        lats[1721] = -31.036906196789811
        lats[1722] = -31.107204964734358
        lats[1723] = -31.177503732676204
        lats[1724] = -31.247802500615318
        lats[1725] = -31.318101268551715
        lats[1726] = -31.388400036485361
        lats[1727] = -31.458698804416255
        lats[1728] = -31.528997572344384
        lats[1729] = -31.599296340269738
        lats[1730] = -31.669595108192297
        lats[1731] = -31.739893876112063
        lats[1732] = -31.810192644029012
        lats[1733] = -31.880491411943137
        lats[1734] = -31.950790179854422
        lats[1735] = -32.021088947762863
        lats[1736] = -32.091387715668439
        lats[1737] = -32.161686483571145
        lats[1738] = -32.231985251470959
        lats[1739] = -32.302284019367875
        lats[1740] = -32.372582787261891
        lats[1741] = -32.442881555152965
        lats[1742] = -32.513180323041112
        lats[1743] = -32.583479090926325
        lats[1744] = -32.653777858808567
        lats[1745] = -32.724076626687825
        lats[1746] = -32.794375394564113
        lats[1747] = -32.864674162437396
        lats[1748] = -32.934972930307666
        lats[1749] = -33.005271698174909
        lats[1750] = -33.075570466039117
        lats[1751] = -33.145869233900278
        lats[1752] = -33.216168001758369
        lats[1753] = -33.286466769613391
        lats[1754] = -33.356765537465314
        lats[1755] = -33.42706430531414
        lats[1756] = -33.497363073159853
        lats[1757] = -33.567661841002426
        lats[1758] = -33.637960608841851
        lats[1759] = -33.708259376678136
        lats[1760] = -33.778558144511237
        lats[1761] = -33.848856912341155
        lats[1762] = -33.919155680167876
        lats[1763] = -33.989454447991392
        lats[1764] = -34.059753215811682
        lats[1765] = -34.130051983628725
        lats[1766] = -34.200350751442521
        lats[1767] = -34.270649519253041
        lats[1768] = -34.340948287060286
        lats[1769] = -34.411247054864234
        lats[1770] = -34.481545822664863
        lats[1771] = -34.551844590462188
        lats[1772] = -34.622143358256153
        lats[1773] = -34.692442126046771
        lats[1774] = -34.762740893834028
        lats[1775] = -34.833039661617903
        lats[1776] = -34.903338429398374
        lats[1777] = -34.973637197175435
        lats[1778] = -35.043935964949064
        lats[1779] = -35.114234732719261
        lats[1780] = -35.184533500486005
        lats[1781] = -35.254832268249267
        lats[1782] = -35.325131036009047
        lats[1783] = -35.395429803765317
        lats[1784] = -35.465728571518085
        lats[1785] = -35.536027339267314
        lats[1786] = -35.606326107012997
        lats[1787] = -35.676624874755113
        lats[1788] = -35.746923642493655
        lats[1789] = -35.817222410228595
        lats[1790] = -35.887521177959933
        lats[1791] = -35.957819945687639
        lats[1792] = -36.028118713411708
        lats[1793] = -36.098417481132117
        lats[1794] = -36.16871624884886
        lats[1795] = -36.239015016561908
        lats[1796] = -36.309313784271254
        lats[1797] = -36.379612551976876
        lats[1798] = -36.449911319678755
        lats[1799] = -36.520210087376888
        lats[1800] = -36.590508855071242
        lats[1801] = -36.660807622761808
        lats[1802] = -36.731106390448581
        lats[1803] = -36.801405158131523
        lats[1804] = -36.871703925810628
        lats[1805] = -36.942002693485883
        lats[1806] = -37.012301461157264
        lats[1807] = -37.082600228824752
        lats[1808] = -37.152898996488332
        lats[1809] = -37.223197764147997
        lats[1810] = -37.293496531803719
        lats[1811] = -37.363795299455489
        lats[1812] = -37.434094067103274
        lats[1813] = -37.504392834747065
        lats[1814] = -37.574691602386856
        lats[1815] = -37.644990370022605
        lats[1816] = -37.715289137654317
        lats[1817] = -37.785587905281965
        lats[1818] = -37.855886672905527
        lats[1819] = -37.926185440524989
        lats[1820] = -37.99648420814033
        lats[1821] = -38.066782975751536
        lats[1822] = -38.137081743358586
        lats[1823] = -38.20738051096145
        lats[1824] = -38.277679278560143
        lats[1825] = -38.347978046154608
        lats[1826] = -38.418276813744846
        lats[1827] = -38.488575581330842
        lats[1828] = -38.558874348912568
        lats[1829] = -38.629173116490001
        lats[1830] = -38.699471884063136
        lats[1831] = -38.769770651631937
        lats[1832] = -38.840069419196389
        lats[1833] = -38.910368186756479
        lats[1834] = -38.980666954312184
        lats[1835] = -39.050965721863491
        lats[1836] = -39.121264489410365
        lats[1837] = -39.191563256952804
        lats[1838] = -39.261862024490775
        lats[1839] = -39.332160792024254
        lats[1840] = -39.402459559553229
        lats[1841] = -39.472758327077692
        lats[1842] = -39.543057094597607
        lats[1843] = -39.613355862112947
        lats[1844] = -39.683654629623703
        lats[1845] = -39.753953397129855
        lats[1846] = -39.824252164631375
        lats[1847] = -39.894550932128247
        lats[1848] = -39.964849699620437
        lats[1849] = -40.035148467107952
        lats[1850] = -40.105447234590748
        lats[1851] = -40.175746002068806
        lats[1852] = -40.246044769542102
        lats[1853] = -40.316343537010617
        lats[1854] = -40.386642304474343
        lats[1855] = -40.456941071933244
        lats[1856] = -40.527239839387299
        lats[1857] = -40.597538606836487
        lats[1858] = -40.667837374280786
        lats[1859] = -40.738136141720176
        lats[1860] = -40.808434909154634
        lats[1861] = -40.878733676584126
        lats[1862] = -40.949032444008644
        lats[1863] = -41.01933121142816
        lats[1864] = -41.089629978842645
        lats[1865] = -41.159928746252085
        lats[1866] = -41.230227513656445
        lats[1867] = -41.300526281055724
        lats[1868] = -41.370825048449873
        lats[1869] = -41.441123815838885
        lats[1870] = -41.511422583222718
        lats[1871] = -41.581721350601363
        lats[1872] = -41.6520201179748
        lats[1873] = -41.722318885343
        lats[1874] = -41.792617652705921
        lats[1875] = -41.862916420063563
        lats[1876] = -41.933215187415882
        lats[1877] = -42.003513954762873
        lats[1878] = -42.073812722104492
        lats[1879] = -42.144111489440725
        lats[1880] = -42.214410256771551
        lats[1881] = -42.284709024096927
        lats[1882] = -42.355007791416853
        lats[1883] = -42.425306558731272
        lats[1884] = -42.495605326040177
        lats[1885] = -42.565904093343548
        lats[1886] = -42.63620286064134
        lats[1887] = -42.706501627933541
        lats[1888] = -42.776800395220121
        lats[1889] = -42.847099162501053
        lats[1890] = -42.917397929776307
        lats[1891] = -42.987696697045862
        lats[1892] = -43.057995464309691
        lats[1893] = -43.128294231567757
        lats[1894] = -43.19859299882004
        lats[1895] = -43.26889176606651
        lats[1896] = -43.339190533307139
        lats[1897] = -43.409489300541907
        lats[1898] = -43.479788067770777
        lats[1899] = -43.550086834993728
        lats[1900] = -43.620385602210717
        lats[1901] = -43.690684369421732
        lats[1902] = -43.760983136626741
        lats[1903] = -43.831281903825705
        lats[1904] = -43.9015806710186
        lats[1905] = -43.971879438205391
        lats[1906] = -44.042178205386072
        lats[1907] = -44.112476972560586
        lats[1908] = -44.182775739728925
        lats[1909] = -44.253074506891046
        lats[1910] = -44.323373274046915
        lats[1911] = -44.39367204119651
        lats[1912] = -44.463970808339802
        lats[1913] = -44.534269575476756
        lats[1914] = -44.604568342607337
        lats[1915] = -44.674867109731515
        lats[1916] = -44.745165876849271
        lats[1917] = -44.81546464396056
        lats[1918] = -44.885763411065362
        lats[1919] = -44.956062178163634
        lats[1920] = -45.026360945255341
        lats[1921] = -45.096659712340461
        lats[1922] = -45.166958479418959
        lats[1923] = -45.237257246490813
        lats[1924] = -45.30755601355596
        lats[1925] = -45.377854780614399
        lats[1926] = -45.448153547666081
        lats[1927] = -45.51845231471097
        lats[1928] = -45.588751081749038
        lats[1929] = -45.659049848780263
        lats[1930] = -45.729348615804589
        lats[1931] = -45.799647382821995
        lats[1932] = -45.869946149832437
        lats[1933] = -45.94024491683588
        lats[1934] = -46.01054368383231
        lats[1935] = -46.080842450821663
        lats[1936] = -46.151141217803925
        lats[1937] = -46.221439984779053
        lats[1938] = -46.291738751747012
        lats[1939] = -46.362037518707766
        lats[1940] = -46.432336285661272
        lats[1941] = -46.502635052607502
        lats[1942] = -46.572933819546414
        lats[1943] = -46.643232586477971
        lats[1944] = -46.713531353402139
        lats[1945] = -46.783830120318882
        lats[1946] = -46.85412888722815
        lats[1947] = -46.924427654129929
        lats[1948] = -46.994726421024154
        lats[1949] = -47.065025187910805
        lats[1950] = -47.13532395478984
        lats[1951] = -47.205622721661214
        lats[1952] = -47.275921488524894
        lats[1953] = -47.346220255380835
        lats[1954] = -47.416519022228997
        lats[1955] = -47.486817789069342
        lats[1956] = -47.557116555901828
        lats[1957] = -47.627415322726435
        lats[1958] = -47.697714089543084
        lats[1959] = -47.76801285635176
        lats[1960] = -47.838311623152421
        lats[1961] = -47.908610389945018
        lats[1962] = -47.978909156729507
        lats[1963] = -48.049207923505868
        lats[1964] = -48.119506690274015
        lats[1965] = -48.189805457033941
        lats[1966] = -48.260104223785596
        lats[1967] = -48.330402990528938
        lats[1968] = -48.400701757263917
        lats[1969] = -48.47100052399049
        lats[1970] = -48.541299290708608
        lats[1971] = -48.611598057418242
        lats[1972] = -48.681896824119335
        lats[1973] = -48.752195590811837
        lats[1974] = -48.822494357495721
        lats[1975] = -48.892793124170929
        lats[1976] = -48.963091890837418
        lats[1977] = -49.03339065749514
        lats[1978] = -49.103689424144044
        lats[1979] = -49.173988190784094
        lats[1980] = -49.244286957415234
        lats[1981] = -49.314585724037435
        lats[1982] = -49.384884490650613
        lats[1983] = -49.455183257254745
        lats[1984] = -49.525482023849783
        lats[1985] = -49.595780790435676
        lats[1986] = -49.66607955701236
        lats[1987] = -49.736378323579807
        lats[1988] = -49.80667709013796
        lats[1989] = -49.876975856686762
        lats[1990] = -49.947274623226157
        lats[1991] = -50.017573389756123
        lats[1992] = -50.087872156276575
        lats[1993] = -50.158170922787484
        lats[1994] = -50.228469689288779
        lats[1995] = -50.298768455780426
        lats[1996] = -50.369067222262359
        lats[1997] = -50.439365988734544
        lats[1998] = -50.509664755196901
        lats[1999] = -50.579963521649397
        lats[2000] = -50.650262288091959
        lats[2001] = -50.720561054524559
        lats[2002] = -50.790859820947119
        lats[2003] = -50.86115858735959
        lats[2004] = -50.931457353761914
        lats[2005] = -51.001756120154049
        lats[2006] = -51.072054886535909
        lats[2007] = -51.14235365290746
        lats[2008] = -51.21265241926865
        lats[2009] = -51.282951185619417
        lats[2010] = -51.353249951959683
        lats[2011] = -51.423548718289396
        lats[2012] = -51.493847484608516
        lats[2013] = -51.56414625091697
        lats[2014] = -51.634445017214695
        lats[2015] = -51.704743783501634
        lats[2016] = -51.775042549777737
        lats[2017] = -51.845341316042933
        lats[2018] = -51.915640082297152
        lats[2019] = -51.985938848540336
        lats[2020] = -52.056237614772435
        lats[2021] = -52.126536380993372
        lats[2022] = -52.196835147203096
        lats[2023] = -52.26713391340153
        lats[2024] = -52.337432679588609
        lats[2025] = -52.407731445764284
        lats[2026] = -52.478030211928477
        lats[2027] = -52.548328978081123
        lats[2028] = -52.618627744222159
        lats[2029] = -52.688926510351514
        lats[2030] = -52.759225276469131
        lats[2031] = -52.829524042574917
        lats[2032] = -52.899822808668837
        lats[2033] = -52.970121574750792
        lats[2034] = -53.040420340820731
        lats[2035] = -53.110719106878584
        lats[2036] = -53.181017872924265
        lats[2037] = -53.251316638957725
        lats[2038] = -53.321615404978871
        lats[2039] = -53.391914170987633
        lats[2040] = -53.462212936983953
        lats[2041] = -53.53251170296776
        lats[2042] = -53.602810468938962
        lats[2043] = -53.673109234897495
        lats[2044] = -53.743408000843282
        lats[2045] = -53.813706766776235
        lats[2046] = -53.884005532696307
        lats[2047] = -53.954304298603383
        lats[2048] = -54.024603064497434
        lats[2049] = -54.094901830378333
        lats[2050] = -54.165200596246031
        lats[2051] = -54.235499362100448
        lats[2052] = -54.305798127941479
        lats[2053] = -54.376096893769081
        lats[2054] = -54.446395659583146
        lats[2055] = -54.516694425383605
        lats[2056] = -54.586993191170357
        lats[2057] = -54.657291956943347
        lats[2058] = -54.727590722702473
        lats[2059] = -54.797889488447652
        lats[2060] = -54.868188254178797
        lats[2061] = -54.938487019895831
        lats[2062] = -55.008785785598668
        lats[2063] = -55.07908455128721
        lats[2064] = -55.149383316961377
        lats[2065] = -55.219682082621084
        lats[2066] = -55.289980848266232
        lats[2067] = -55.360279613896743
        lats[2068] = -55.430578379512511
        lats[2069] = -55.500877145113449
        lats[2070] = -55.571175910699488
        lats[2071] = -55.641474676270505
        lats[2072] = -55.711773441826416
        lats[2073] = -55.782072207367136
        lats[2074] = -55.852370972892551
        lats[2075] = -55.922669738402583
        lats[2076] = -55.992968503897131
        lats[2077] = -56.063267269376091
        lats[2078] = -56.133566034839362
        lats[2079] = -56.203864800286865
        lats[2080] = -56.274163565718467
        lats[2081] = -56.34446233113411
        lats[2082] = -56.41476109653366
        lats[2083] = -56.485059861917016
        lats[2084] = -56.555358627284086
        lats[2085] = -56.625657392634771
        lats[2086] = -56.695956157968951
        lats[2087] = -56.766254923286517
        lats[2088] = -56.836553688587379
        lats[2089] = -56.90685245387143
        lats[2090] = -56.977151219138541
        lats[2091] = -57.047449984388614
        lats[2092] = -57.117748749621541
        lats[2093] = -57.188047514837208
        lats[2094] = -57.258346280035504
        lats[2095] = -57.328645045216312
        lats[2096] = -57.398943810379521
        lats[2097] = -57.469242575525016
        lats[2098] = -57.539541340652676
        lats[2099] = -57.60984010576238
        lats[2100] = -57.680138870854037
        lats[2101] = -57.75043763592749
        lats[2102] = -57.820736400982646
        lats[2103] = -57.891035166019364
        lats[2104] = -57.961333931037537
        lats[2105] = -58.031632696037022
        lats[2106] = -58.101931461017728
        lats[2107] = -58.172230225979497
        lats[2108] = -58.242528990922203
        lats[2109] = -58.312827755845746
        lats[2110] = -58.383126520749968
        lats[2111] = -58.453425285634758
        lats[2112] = -58.523724050499972
        lats[2113] = -58.594022815345468
        lats[2114] = -58.664321580171141
        lats[2115] = -58.73462034497684
        lats[2116] = -58.804919109762423
        lats[2117] = -58.875217874527763
        lats[2118] = -58.945516639272725
        lats[2119] = -59.015815403997145
        lats[2120] = -59.086114168700909
        lats[2121] = -59.156412933383855
        lats[2122] = -59.226711698045854
        lats[2123] = -59.29701046268675
        lats[2124] = -59.3673092273064
        lats[2125] = -59.43760799190467
        lats[2126] = -59.507906756481383
        lats[2127] = -59.578205521036402
        lats[2128] = -59.64850428556958
        lats[2129] = -59.718803050080759
        lats[2130] = -59.78910181456979
        lats[2131] = -59.859400579036503
        lats[2132] = -59.929699343480763
        lats[2133] = -59.999998107902378
        lats[2134] = -60.070296872301235
        lats[2135] = -60.140595636677112
        lats[2136] = -60.21089440102989
        lats[2137] = -60.28119316535939
        lats[2138] = -60.35149192966545
        lats[2139] = -60.421790693947884
        lats[2140] = -60.492089458206543
        lats[2141] = -60.562388222441243
        lats[2142] = -60.632686986651805
        lats[2143] = -60.702985750838074
        lats[2144] = -60.773284514999872
        lats[2145] = -60.843583279137007
        lats[2146] = -60.913882043249295
        lats[2147] = -60.984180807336578
        lats[2148] = -61.054479571398652
        lats[2149] = -61.124778335435344
        lats[2150] = -61.195077099446451
        lats[2151] = -61.265375863431785
        lats[2152] = -61.335674627391185
        lats[2153] = -61.405973391324409
        lats[2154] = -61.476272155231321
        lats[2155] = -61.546570919111666
        lats[2156] = -61.616869682965287
        lats[2157] = -61.687168446791986
        lats[2158] = -61.757467210591535
        lats[2159] = -61.827765974363729
        lats[2160] = -61.898064738108381
        lats[2161] = -61.968363501825259
        lats[2162] = -62.038662265514176
        lats[2163] = -62.108961029174914
        lats[2164] = -62.179259792807258
        lats[2165] = -62.249558556410982
        lats[2166] = -62.319857319985871
        lats[2167] = -62.3901560835317
        lats[2168] = -62.460454847048261
        lats[2169] = -62.530753610535321
        lats[2170] = -62.60105237399263
        lats[2171] = -62.67135113741999
        lats[2172] = -62.741649900817137
        lats[2173] = -62.811948664183866
        lats[2174] = -62.882247427519928
        lats[2175] = -62.952546190825068
        lats[2176] = -63.022844954099064
        lats[2177] = -63.093143717341647
        lats[2178] = -63.163442480552604
        lats[2179] = -63.23374124373165
        lats[2180] = -63.304040006878537
        lats[2181] = -63.374338769993031
        lats[2182] = -63.444637533074854
        lats[2183] = -63.514936296123757
        lats[2184] = -63.585235059139464
        lats[2185] = -63.655533822121711
        lats[2186] = -63.725832585070251
        lats[2187] = -63.796131347984762
        lats[2188] = -63.866430110865004
        lats[2189] = -63.93672887371072
        lats[2190] = -64.00702763652157
        lats[2191] = -64.07732639929732
        lats[2192] = -64.147625162037642
        lats[2193] = -64.21792392474228
        lats[2194] = -64.288222687410922
        lats[2195] = -64.358521450043284
        lats[2196] = -64.428820212639039
        lats[2197] = -64.499118975197902
        lats[2198] = -64.569417737719576
        lats[2199] = -64.639716500203733
        lats[2200] = -64.710015262650074
        lats[2201] = -64.780314025058246
        lats[2202] = -64.850612787427963
        lats[2203] = -64.920911549758912
        lats[2204] = -64.991210312050711
        lats[2205] = -65.061509074303089
        lats[2206] = -65.131807836515677
        lats[2207] = -65.202106598688133
        lats[2208] = -65.272405360820116
        lats[2209] = -65.342704122911286
        lats[2210] = -65.413002884961315
        lats[2211] = -65.483301646969792
        lats[2212] = -65.553600408936404
        lats[2213] = -65.623899170860767
        lats[2214] = -65.694197932742526
        lats[2215] = -65.764496694581283
        lats[2216] = -65.834795456376696
        lats[2217] = -65.905094218128355
        lats[2218] = -65.975392979835888
        lats[2219] = -66.045691741498899
        lats[2220] = -66.115990503117033
        lats[2221] = -66.186289264689833
        lats[2222] = -66.256588026216932
        lats[2223] = -66.326886787697887
        lats[2224] = -66.397185549132331
        lats[2225] = -66.467484310519808
        lats[2226] = -66.537783071859891
        lats[2227] = -66.608081833152212
        lats[2228] = -66.678380594396273
        lats[2229] = -66.748679355591662
        lats[2230] = -66.818978116737924
        lats[2231] = -66.889276877834618
        lats[2232] = -66.95957563888129
        lats[2233] = -67.029874399877471
        lats[2234] = -67.100173160822706
        lats[2235] = -67.170471921716526
        lats[2236] = -67.240770682558434
        lats[2237] = -67.311069443347961
        lats[2238] = -67.381368204084609
        lats[2239] = -67.451666964767895
        lats[2240] = -67.521965725397308
        lats[2241] = -67.592264485972336
        lats[2242] = -67.662563246492482
        lats[2243] = -67.732862006957205
        lats[2244] = -67.803160767365966
        lats[2245] = -67.873459527718282
        lats[2246] = -67.943758288013555
        lats[2247] = -68.014057048251274
        lats[2248] = -68.084355808430871
        lats[2249] = -68.154654568551791
        lats[2250] = -68.224953328613438
        lats[2251] = -68.295252088615257
        lats[2252] = -68.365550848556666
        lats[2253] = -68.435849608437067
        lats[2254] = -68.506148368255865
        lats[2255] = -68.576447128012447
        lats[2256] = -68.646745887706189
        lats[2257] = -68.717044647336493
        lats[2258] = -68.787343406902693
        lats[2259] = -68.85764216640419
        lats[2260] = -68.927940925840304
        lats[2261] = -68.998239685210365
        lats[2262] = -69.068538444513763
        lats[2263] = -69.138837203749759
        lats[2264] = -69.209135962917699
        lats[2265] = -69.279434722016902
        lats[2266] = -69.349733481046613
        lats[2267] = -69.420032240006194
        lats[2268] = -69.490330998894862
        lats[2269] = -69.560629757711908
        lats[2270] = -69.630928516456592
        lats[2271] = -69.701227275128161
        lats[2272] = -69.771526033725834
        lats[2273] = -69.841824792248843
        lats[2274] = -69.912123550696421
        lats[2275] = -69.982422309067744
        lats[2276] = -70.052721067362043
        lats[2277] = -70.123019825578467
        lats[2278] = -70.193318583716191
        lats[2279] = -70.263617341774406
        lats[2280] = -70.333916099752187
        lats[2281] = -70.404214857648739
        lats[2282] = -70.474513615463138
        lats[2283] = -70.544812373194532
        lats[2284] = -70.615111130841967
        lats[2285] = -70.685409888404578
        lats[2286] = -70.755708645881384
        lats[2287] = -70.826007403271475
        lats[2288] = -70.896306160573886
        lats[2289] = -70.966604917787635
        lats[2290] = -71.036903674911756
        lats[2291] = -71.107202431945211
        lats[2292] = -71.177501188887007
        lats[2293] = -71.247799945736105
        lats[2294] = -71.318098702491469
        lats[2295] = -71.388397459152031
        lats[2296] = -71.458696215716685
        lats[2297] = -71.528994972184378
        lats[2298] = -71.599293728553988
        lats[2299] = -71.669592484824364
        lats[2300] = -71.739891240994368
        lats[2301] = -71.810189997062835
        lats[2302] = -71.880488753028587
        lats[2303] = -71.950787508890414
        lats[2304] = -72.02108626464711
        lats[2305] = -72.091385020297409
        lats[2306] = -72.161683775840089
        lats[2307] = -72.231982531273843
        lats[2308] = -72.302281286597392
        lats[2309] = -72.3725800418094
        lats[2310] = -72.442878796908545
        lats[2311] = -72.513177551893421
        lats[2312] = -72.583476306762691
        lats[2313] = -72.653775061514935
        lats[2314] = -72.724073816148703
        lats[2315] = -72.794372570662574
        lats[2316] = -72.864671325055056
        lats[2317] = -72.934970079324657
        lats[2318] = -73.005268833469799
        lats[2319] = -73.075567587489019
        lats[2320] = -73.145866341380668
        lats[2321] = -73.216165095143182
        lats[2322] = -73.2864638487749
        lats[2323] = -73.356762602274188
        lats[2324] = -73.427061355639339
        lats[2325] = -73.497360108868662
        lats[2326] = -73.567658861960396
        lats[2327] = -73.637957614912779
        lats[2328] = -73.70825636772399
        lats[2329] = -73.778555120392184
        lats[2330] = -73.848853872915541
        lats[2331] = -73.919152625292114
        lats[2332] = -73.98945137751997
        lats[2333] = -74.059750129597163
        lats[2334] = -74.13004888152166
        lats[2335] = -74.200347633291472
        lats[2336] = -74.270646384904481
        lats[2337] = -74.340945136358584
        lats[2338] = -74.411243887651622
        lats[2339] = -74.481542638781434
        lats[2340] = -74.551841389745761
        lats[2341] = -74.622140140542356
        lats[2342] = -74.692438891168877
        lats[2343] = -74.762737641622991
        lats[2344] = -74.833036391902269
        lats[2345] = -74.903335142004323
        lats[2346] = -74.973633891926625
        lats[2347] = -75.043932641666672
        lats[2348] = -75.114231391221821
        lats[2349] = -75.184530140589501
        lats[2350] = -75.254828889766983
        lats[2351] = -75.325127638751567
        lats[2352] = -75.395426387540439
        lats[2353] = -75.465725136130786
        lats[2354] = -75.536023884519707
        lats[2355] = -75.60632263270422
        lats[2356] = -75.67662138068134
        lats[2357] = -75.746920128447996
        lats[2358] = -75.81721887600105
        lats[2359] = -75.887517623337317
        lats[2360] = -75.957816370453543
        lats[2361] = -76.028115117346374
        lats[2362] = -76.098413864012443
        lats[2363] = -76.16871261044831
        lats[2364] = -76.239011356650423
        lats[2365] = -76.3093101026152
        lats[2366] = -76.379608848338933
        lats[2367] = -76.449907593817869
        lats[2368] = -76.520206339048215
        lats[2369] = -76.59050508402602
        lats[2370] = -76.660803828747362
        lats[2371] = -76.731102573208048
        lats[2372] = -76.801401317404
        lats[2373] = -76.871700061330955
        lats[2374] = -76.941998804984564
        lats[2375] = -77.012297548360323
        lats[2376] = -77.082596291453768
        lats[2377] = -77.15289503426024
        lats[2378] = -77.22319377677502
        lats[2379] = -77.293492518993247
        lats[2380] = -77.363791260909963
        lats[2381] = -77.434090002520122
        lats[2382] = -77.504388743818524
        lats[2383] = -77.574687484799924
        lats[2384] = -77.644986225458879
        lats[2385] = -77.71528496578982
        lats[2386] = -77.785583705787161
        lats[2387] = -77.855882445445019
        lats[2388] = -77.926181184757539
        lats[2389] = -77.996479923718596
        lats[2390] = -78.066778662322022
        lats[2391] = -78.137077400561424
        lats[2392] = -78.207376138430348
        lats[2393] = -78.277674875922045
        lats[2394] = -78.347973613029708
        lats[2395] = -78.418272349746417
        lats[2396] = -78.488571086064923
        lats[2397] = -78.558869821977908
        lats[2398] = -78.629168557477882
        lats[2399] = -78.699467292557102
        lats[2400] = -78.769766027207638
        lats[2401] = -78.840064761421445
        lats[2402] = -78.910363495190211
        lats[2403] = -78.980662228505423
        lats[2404] = -79.050960961358285
        lats[2405] = -79.121259693739859
        lats[2406] = -79.191558425640977
        lats[2407] = -79.261857157052191
        lats[2408] = -79.332155887963822
        lats[2409] = -79.402454618365894
        lats[2410] = -79.472753348248219
        lats[2411] = -79.543052077600308
        lats[2412] = -79.61335080641139
        lats[2413] = -79.683649534670437
        lats[2414] = -79.753948262366038
        lats[2415] = -79.824246989486554
        lats[2416] = -79.894545716019948
        lats[2417] = -79.9648444419539
        lats[2418] = -80.035143167275749
        lats[2419] = -80.105441891972376
        lats[2420] = -80.175740616030438
        lats[2421] = -80.246039339436052
        lats[2422] = -80.316338062175078
        lats[2423] = -80.386636784232863
        lats[2424] = -80.456935505594302
        lats[2425] = -80.527234226243991
        lats[2426] = -80.59753294616587
        lats[2427] = -80.667831665343556
        lats[2428] = -80.73813038376008
        lats[2429] = -80.808429101397948
        lats[2430] = -80.878727818239184
        lats[2431] = -80.949026534265244
        lats[2432] = -81.019325249456955
        lats[2433] = -81.089623963794551
        lats[2434] = -81.159922677257711
        lats[2435] = -81.230221389825374
        lats[2436] = -81.300520101475826
        lats[2437] = -81.370818812186627
        lats[2438] = -81.441117521934686
        lats[2439] = -81.511416230696042
        lats[2440] = -81.581714938445955
        lats[2441] = -81.652013645158945
        lats[2442] = -81.722312350808508
        lats[2443] = -81.792611055367345
        lats[2444] = -81.862909758807191
        lats[2445] = -81.933208461098829
        lats[2446] = -82.003507162211946
        lats[2447] = -82.073805862115165
        lats[2448] = -82.144104560776
        lats[2449] = -82.214403258160871
        lats[2450] = -82.284701954234833
        lats[2451] = -82.355000648961692
        lats[2452] = -82.425299342304029
        lats[2453] = -82.495598034222837
        lats[2454] = -82.56589672467787
        lats[2455] = -82.63619541362705
        lats[2456] = -82.706494101026948
        lats[2457] = -82.77679278683226
        lats[2458] = -82.84709147099602
        lats[2459] = -82.917390153469313
        lats[2460] = -82.987688834201322
        lats[2461] = -83.057987513139125
        lats[2462] = -83.128286190227698
        lats[2463] = -83.198584865409657
        lats[2464] = -83.268883538625232
        lats[2465] = -83.339182209812321
        lats[2466] = -83.409480878905782
        lats[2467] = -83.479779545838113
        lats[2468] = -83.550078210538487
        lats[2469] = -83.620376872933264
        lats[2470] = -83.690675532945292
        lats[2471] = -83.760974190494011
        lats[2472] = -83.831272845495249
        lats[2473] = -83.901571497860914
        lats[2474] = -83.971870147498763
        lats[2475] = -84.042168794312317
        lats[2476] = -84.112467438200326
        lats[2477] = -84.18276607905679
        lats[2478] = -84.253064716770425
        lats[2479] = -84.323363351224444
        lats[2480] = -84.393661982296322
        lats[2481] = -84.463960609857125
        lats[2482] = -84.534259233771479
        lats[2483] = -84.604557853896708
        lats[2484] = -84.674856470082915
        lats[2485] = -84.745155082171991
        lats[2486] = -84.81545368999717
        lats[2487] = -84.885752293382765
        lats[2488] = -84.95605089214304
        lats[2489] = -85.026349486081983
        lats[2490] = -85.09664807499216
        lats[2491] = -85.16694665865414
        lats[2492] = -85.237245236835548
        lats[2493] = -85.307543809290152
        lats[2494] = -85.377842375756586
        lats[2495] = -85.448140935957483
        lats[2496] = -85.518439489597966
        lats[2497] = -85.588738036364362
        lats[2498] = -85.659036575922883
        lats[2499] = -85.729335107917464
        lats[2500] = -85.799633631968391
        lats[2501] = -85.869932147670127
        lats[2502] = -85.940230654588888
        lats[2503] = -86.010529152260403
        lats[2504] = -86.080827640187209
        lats[2505] = -86.151126117835304
        lats[2506] = -86.221424584631109
        lats[2507] = -86.291723039957418
        lats[2508] = -86.362021483149363
        lats[2509] = -86.432319913489792
        lats[2510] = -86.502618330203831
        lats[2511] = -86.572916732453024
        lats[2512] = -86.643215119328573
        lats[2513] = -86.713513489844246
        lats[2514] = -86.783811842927179
        lats[2515] = -86.854110177408927
        lats[2516] = -86.924408492014166
        lats[2517] = -86.994706785348129
        lats[2518] = -87.065005055882821
        lats[2519] = -87.135303301939786
        lats[2520] = -87.205601521672108
        lats[2521] = -87.275899713041966
        lats[2522] = -87.346197873795816
        lats[2523] = -87.416496001434894
        lats[2524] = -87.486794093180748
        lats[2525] = -87.557092145935584
        lats[2526] = -87.627390156234085
        lats[2527] = -87.697688120188062
        lats[2528] = -87.767986033419561
        lats[2529] = -87.838283890981543
        lats[2530] = -87.908581687261687
        lats[2531] = -87.978879415867283
        lats[2532] = -88.049177069484486
        lats[2533] = -88.119474639706425
        lats[2534] = -88.189772116820762
        lats[2535] = -88.26006948954614
        lats[2536] = -88.330366744702559
        lats[2537] = -88.40066386679355
        lats[2538] = -88.470960837474877
        lats[2539] = -88.541257634868515
        lats[2540] = -88.611554232668382
        lats[2541] = -88.681850598961759
        lats[2542] = -88.752146694650691
        lats[2543] = -88.822442471310097
        lats[2544] = -88.892737868230952
        lats[2545] = -88.96303280826325
        lats[2546] = -89.033327191845927
        lats[2547] = -89.103620888238879
        lats[2548] = -89.173913722284126
        lats[2549] = -89.24420545380525
        lats[2550] = -89.314495744374256
        lats[2551] = -89.3847841013921
        lats[2552] = -89.45506977912261
        lats[2553] = -89.525351592371393
        lats[2554] = -89.595627537554492
        lats[2555] = -89.6658939412157
        lats[2556] = -89.736143271609578
        lats[2557] = -89.806357319542244
        lats[2558] = -89.876478353332288
        lats[2559] = -89.946187715665616
        return lats

    def first_axis_vals(self):
        if self._resolution == 1280:
            return self.get_precomputed_values_N1280()
        else:
            precision = 1.0e-14
            nval = self._resolution * 2
            rad2deg = 180 / math.pi
            convval = 1 - ((2 / math.pi) * (2 / math.pi)) * 0.25
            vals = self.gauss_first_guess()
            new_vals = [0] * nval
            denom = math.sqrt(((nval + 0.5) * (nval + 0.5)) + convval)
            for jval in range(self._resolution):
                root = math.cos(vals[jval] / denom)
                conv = 1
                while abs(conv) >= precision:
                    mem2 = 1
                    mem1 = root
                    for legi in range(nval):
                        legfonc = ((2.0 * (legi + 1) - 1.0) * root * mem1 - legi * mem2) / (legi + 1)
                        mem2 = mem1
                        mem1 = legfonc
                    conv = legfonc / ((nval * (mem2 - root * legfonc)) / (1.0 - (root * root)))
                    root = root - conv
                    # add maybe a max iter here to make sure we converge at some point
                new_vals[jval] = math.asin(root) * rad2deg
                new_vals[nval - 1 - jval] = -new_vals[jval]
            return new_vals

    def map_first_axis(self, lower, upper):
        axis_lines = self._first_axis_vals
        # return_vals = [val for val in axis_lines if lower <= val <= upper]
        end_idx = bisect_left_cmp(axis_lines, lower, cmp=lambda x, y: x > y) + 1
        start_idx = bisect_right_cmp(axis_lines, upper, cmp=lambda x, y: x > y)
        return_vals = axis_lines[start_idx:end_idx]
        return return_vals

    def second_axis_vals(self, first_val):
        first_axis_vals = self._first_axis_vals
        tol = 1e-10
        # first_val = [val for val in first_axis_vals if first_val - tol < val < first_val + tol][0]
        # first_idx = first_axis_vals.index(first_val)
        first_idx = bisect_left_cmp(first_axis_vals, first_val - tol, cmp=lambda x, y: x > y)
        if first_idx >= self._resolution:
            first_idx = (2 * self._resolution) - 1 - first_idx
        first_idx = first_idx + 1
        npoints = 4 * first_idx + 16
        second_axis_spacing = 360 / npoints
        second_axis_vals = [i * second_axis_spacing for i in range(npoints)]
        return second_axis_vals

    def second_axis_spacing(self, first_val):
        first_axis_vals = self._first_axis_vals
        tol = 1e-10
        # first_val = [val for val in first_axis_vals if first_val - tol < val < first_val + tol][0]
        # first_idx = first_axis_vals.index(first_val)
        _first_idx = bisect_left_cmp(first_axis_vals, first_val - tol, cmp=lambda x, y: x > y)
        first_idx = _first_idx
        if first_idx >= self._resolution:
            first_idx = (2 * self._resolution) - 1 - first_idx
        first_idx = first_idx + 1
        npoints = 4 * first_idx + 16
        second_axis_spacing = 360 / npoints
        return (second_axis_spacing, _first_idx + 1)

    def map_second_axis(self, first_val, lower, upper):
        second_axis_spacing, first_idx = self.second_axis_spacing(first_val)
        # if first_val not in self._second_axis_spacing:
        #     (second_axis_spacing, first_idx) = self.second_axis_spacing(first_val)
        #     self._second_axis_spacing[first_val] = (second_axis_spacing, first_idx)
        # else:
        #     (second_axis_spacing, first_idx) = self._second_axis_spacing[first_val]
        start_idx = int(lower/second_axis_spacing)
        end_idx = int(upper/second_axis_spacing) + 1
        return_vals = [i * second_axis_spacing for i in range(start_idx, end_idx)]

        # second_axis_vals = self.second_axis_vals(first_val)
        # # NOTE: here this seems faster than the bisect.bisect?
        # # return_vals = [val for val in second_axis_vals if lower <= val <= upper]
        # start_idx = bisect_left_cmp(second_axis_vals, lower, cmp=lambda x, y: x < y) + 1
        # end_idx = bisect_right_cmp(second_axis_vals, upper, cmp=lambda x, y: x < y) + 1
        # return_vals = second_axis_vals[start_idx:end_idx]
        # # start_idx = bisect.bisect_left(second_axis_vals, lower)
        # # end_idx = bisect.bisect_right(second_axis_vals, upper)
        # # return_vals = second_axis_vals[start_idx:end_idx]
        return return_vals

    def axes_idx_to_octahedral_idx(self, first_idx, second_idx):
        # NOTE: for now this takes ~2e-4s per point, so taking significant time -> for 20k points, takes 4s
        # Would it be better to store a dictionary of first_idx with cumulative number of points on that idx?
        # Because this is what we are doing here, but we are calculating for each point...
        # But then this would only work for special grid resolutions, so need to do like a O1280 version of this

        # NOTE: OR somehow cache this for a given first_idx and then only modify the axis idx for second_idx when the
        # first_idx changes
        # time1 = time.time()
        # octa_idx = self._first_idx_map[first_idx-1] + second_idx
        octa_idx = self._first_idx_map[first_idx-1] + second_idx
        # octa_idx = 0
        # if first_idx == 1:
        #     octa_idx = second_idx
        # else:
        #     for i in range(first_idx - 1):
        #         if i <= self._resolution - 1:
        #             octa_idx += 20 + 4 * i
        #         else:
        #             i = i - self._resolution + 1
        #             if i == 1:
        #                 octa_idx += 16 + 4 * self._resolution
        #             else:
        #                 i = i - 1
        #                 octa_idx += 16 + 4 * (self._resolution - i)
        #     octa_idx += second_idx
        # print("TIME UNMAPPING TO OCT IDX")
        # print(time.time() - time1)
        return octa_idx

    # def find_second_idx(self, first_val, second_val):
    #     tol = 1e-10
    #     second_axis_vals = self.second_axis_vals(first_val)
    #     second_idx = bisect.bisect_left(second_axis_vals, second_val - tol)
    #     return second_idx

    def create_first_idx_map(self):
        # first_idx_list = [0] * (2*self._resolution)
        first_idx_list = {}
        idx = 0
        for i in range(2*self._resolution):
            # first_idx_list[i] = idx
            first_idx_list[i] = idx
            if i <= self._resolution - 1:
                idx += 20 + 4 * i
            else:
                i = i - self._resolution + 1
                if i == 1:
                    idx += 16 + 4 * self._resolution
                else:
                    i = i - 1
                    idx += 16 + 4 * (self._resolution - i)
        return first_idx_list

    # def unmap_first_val_to_start_line_idx(self, first_val):
    #     first_axis_vals = self._first_axis_vals
    #     tol = 1e-10
    #     # first_val = [val for val in first_axis_vals if first_val - tol < val < first_val + tol][0]
    #     # first_idx = first_axis_vals.index(first_val) + 1
    #     # first_idx = len(first_axis_vals) - bisect.bisect_left(first_axis_vals[::-1], first_val - tol)
    #     first_idx = bisect_left_cmp(first_axis_vals, first_val - tol, cmp=lambda x, y: x > y) + 1
    #     octa_idx = 0
    #     if first_idx == 1:
    #         return octa_idx
    #     else:
    #         for i in range(first_idx - 1):
    #             if i <= self._resolution - 1:
    #                 octa_idx += 20 + 4 * i
    #             else:
    #                 i = i - self._resolution + 1
    #                 if i == 1:
    #                     octa_idx += 16 + 4 * self._resolution
    #                 else:
    #                     i = i - 1
    #                     octa_idx += 16 + 4 * (self._resolution - i)
    #         return octa_idx

    def find_second_axis_idx(self, first_val, second_val):
        (second_axis_spacing, first_idx) = self.second_axis_spacing(first_val)
        # if first_val not in self._second_axis_spacing:
        #     (second_axis_spacing, first_idx) = self.second_axis_spacing(first_val)
        #     self._second_axis_spacing[first_val] = (second_axis_spacing, first_idx)
        # else:
        #     (second_axis_spacing, first_idx) = self._second_axis_spacing[first_val]
        second_idx = int(second_val/second_axis_spacing)
        return (first_idx, second_idx)

    def unmap(self, first_val, second_val):
        # time1 = time.time()
        # first_axis_vals = self._first_axis_vals
        # inv_first_axis_vals = self._inv_first_axis_vals
        # tol = 1e-10
        # # first_val = [val for val in first_axis_vals if first_val - tol < val < first_val + tol][0]
        # # first_idx = first_axis_vals.index(first_val) + 1
        # # first_idx = len(first_axis_vals) - bisect.bisect_left(first_axis_vals[::-1], first_val - tol)
        # # first_idx = bisect_left_cmp(first_axis_vals, first_val - tol, cmp=lambda x, y: x > y) + 1
        # first_idx = bisect.bisect_left(self._inv_first_axis_vals, - (first_val - tol))
        # # print(inv_first_axis_vals)
        # # print(first_val)
        # # first_idx = inv_first_axis_vals[first_val]
        # # first_idx = np.searchsorted(-first_axis_vals, - (first_val - tol), side="right")
        # if first_val not in self.treated_first_vals:
        #     second_axis_vals = self.second_axis_vals(first_val)
        #     self.treated_first_vals[first_val] = second_axis_vals
        # else:
        #     second_axis_vals = self.treated_first_vals[first_val]
        # # second_val = [val for val in second_axis_vals if second_val - tol < val < second_val + tol][0]
        # # second_idx = second_axis_vals.index(second_val)
        # second_idx = bisect.bisect_left(second_axis_vals, second_val - tol)
        (first_idx, second_idx) = self.find_second_axis_idx(first_val, second_val)
        # second_idx = np.searchsorted(second_axis_vals, second_val - tol)
        # print("TIME SPENT DOING VAL TO IDX")
        # print(time.time() - time1)
        octahedral_index = self.axes_idx_to_octahedral_idx(first_idx, second_idx)
        # octahedral_index = int(octahedral_index)
        # print("OCTAHEDRAL UNMAP TIME ")
        # print(time.time() - time1)
        return octahedral_index


_type_to_datacube_mapper_lookup = {
    "octahedral": "OctahedralGridMapper",
    "healpix": "HealpixGridMapper",
    "regular": "RegularGridMapper",
}
