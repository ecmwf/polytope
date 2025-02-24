# from typing import List

# from ..datacube.tensor_index_tree import TensorIndexTree
# from ..shapes import ConvexPolytope
# from ..utility.combinatorics import group, tensor_product
# from .engine import Engine
# from ..utility.list_tools import unique
# from qubed import Qube


# class QubedSlicing(Engine):
#     def __init__(self):
#         self.datacube = ??

#     def create_fake_datacube_mappers(self):
#         # TODO
#         self.datacube_mappers = ??
#         pass

#     def create_request_polys(self, polytopes):
#         for p in polytopes:
#             self._unique_continuous_points(p)

#         groups, input_axes = group(polytopes)
#         combinations = tensor_product(groups)
#         return combinations

#     def _unique_continuous_points(self, p: ConvexPolytope):
#         for i, ax in enumerate(p._axes):
#             mapper = self.datacube_mappers.get(ax, None)
#             for j, val in enumerate(p.points):
#                 p.points[j][i] = mapper.to_float(mapper.parse(p.points[j][i]))
#         # Remove duplicate points
#         unique(p.points)

#     def extract(self, datacube, polytopes: List[ConvexPolytope]):
#         combinations = self.create_request_polys(polytopes)

#         request = Qube.empty()

#         for c in combinations:
#             r = Qube.empty()
#             new_c = []
#             for combi in c:
#                 if isinstance(combi, list):
#                     new_c.extend(combi)
#                 else:
#                     new_c.append(combi)
#             r.set

#         # TODO: replace all the TensorIndexTrees with Qube trees

#         # request = TensorIndexTree()

#         # for c in combinations:
#         #     r = TensorIndexTree()
#         #     new_c = []
#         #     for combi in c:
#         #         if isinstance(combi, list):
#         #             new_c.extend(combi)
#         #         else:
#         #             new_c.append(combi)
#         #     r["unsliced_polytopes"] = set(new_c)
#         #     current_nodes = [r]
#         #     for ax in datacube.axes.values():
#         #         next_nodes = []
#         #         interm_next_nodes = []
#         #         for node in current_nodes:
#         #             self._build_branch(ax, node, datacube, interm_next_nodes)
#         #             next_nodes.extend(interm_next_nodes)
#         #             interm_next_nodes = []
#         #         current_nodes = next_nodes

#         #     request.merge(r)
#         # return request
