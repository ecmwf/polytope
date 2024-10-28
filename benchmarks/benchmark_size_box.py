import pandas as pd

from polytope_feature.polytope import Request
from polytope_feature.shapes import Span, Select, Box

from benchmark_setup import PolytopeBenchmarkEnsembleSurface


def benchmark_boxes(box):
    benchmark = PolytopeBenchmarkEnsembleSurface()

    # request = Request(
    #     Select("step", [0]),
    #     Select("domain", ["g"]),
    #     Select("class", ["od"]),
    #     Select("levtype", ["sfc"]),
    #     Select("date", [pd.Timestamp("20240925T000000")]),
    #     Select("expver", ["0079"]),
    #     Select("param", ["164"]),
    #     Select("stream", ["enfo"]),
    #     Select("type", ["pf"]),
    #     Select("number", [1]),
    #     box
    # )
    request = Request(
            Select("step", [0]),
            Select("levtype", ["sfc"]),
            Select("date", [pd.Timestamp("20240118T000000")]),
            Select("domain", ["g"]),
            Select("expver", ["0001"]),
            Select("param", ["49", "167"]),
            Select("class", ["od"]),
            Select("stream", ["oper"]),
            Select("type", ["fc"]),
            box,
        )

    result = benchmark.API.retrieve(request)
    # result.pprint()


# NOTE that this is on real forecast data, which might not be the best for comparing boxes in different dimensions
if True:

    import logging
    
    logger = logging.getLogger('')
    logger.setLevel(logging.INFO)

    # # Look at how increasing number of latitude points affects extraction time etc
    # # BUT longitude points on different latitude lines are not evenly spaced
    # # so it's not the same whether we center the box around 0 or another latitude point
    # # -> EFFECT PF THE GRID

    # print("EXTRACTION OF BOXES WITH INCREASING SIZE IN LAT WITH LOWER CORNER [0,0] \n\n")

    # boxes = [Box(["latitude", "longitude"], [0, 0], [1, 10]),
    #          Box(["latitude", "longitude"], [0, 0], [5, 10]),
    #          Box(["latitude", "longitude"], [0, 0], [10, 10]),
    #          Box(["latitude", "longitude"], [0, 0], [45, 10]),
    #          Box(["latitude", "longitude"], [0, 0], [90, 10]),
    #          ]

    # for box in boxes:
    #     benchmark_boxes(box)

    # print("EXTRACTION OF BOXES WITH INCREASING SIZE IN LAT WITH CENTER [0,0] \n\n")

    # boxes = [Box(["latitude", "longitude"], [-0.5, 0], [0.5, 10]),
    #          Box(["latitude", "longitude"], [-2.5, 0], [2.5, 10]),
    #          Box(["latitude", "longitude"], [-5, 0], [5, 10]),
    #          Box(["latitude", "longitude"], [-22.5, 0], [22.5, 10]),
    #          Box(["latitude", "longitude"], [-45, 0], [45, 10]),
    #          ]

    # for box in boxes:
    #     benchmark_boxes(box)

    # # Look at how increasing number of longitude points affects extraction time etc
    # # BUT longitude points on different latitude lines are not evenly spaced
    # # so it's not the same whether we center the box around 0 or another latitude point
    # # -> EFFECT PF THE GRID

    # print("EXTRACTION OF BOXES WITH INCREASING SIZE IN LON WITH LOWER CORNER [0,0] \n\n")

    # boxes = [Box(["longitude", "latitude"], [0, 0], [1, 10]),
    #          Box(["longitude", "latitude"], [0, 0], [5, 10]),
    #          Box(["longitude", "latitude"], [0, 0], [10, 10]),
    #          Box(["longitude", "latitude"], [0, 0], [45, 10]),
    #          Box(["longitude", "latitude"], [0, 0], [90, 10]),
    #          ]

    # for box in boxes:
    #     benchmark_boxes(box)

    # print("EXTRACTION OF BOXES WITH INCREASING SIZE IN LON WITH CENTER [0,0] \n\n")

    # boxes = [Box(["longitude", "latitude"], [-0.5, 0], [0.5, 10]),
    #          Box(["longitude", "latitude"], [-2.5, 0], [2.5, 10]),
    #          Box(["longitude", "latitude"], [-5, 0], [5, 10]),
    #          Box(["longitude", "latitude"], [-22.5, 0], [22.5, 10]),
    #          Box(["longitude", "latitude"], [-45, 0], [45, 10]),
    #          ]

    # for box in boxes:
    #     benchmark_boxes(box)
    
    # # Look at how increasing number of longitude and latitude points affects extraction time etc
    # # BUT longitude points on different latitude lines are not evenly spaced
    # # so it's not the same whether we center the box around 0 or another latitude point
    # # -> EFFECT PF THE GRID

    # print("EXTRACTION OF BOXES WITH INCREASING SIZE IN LON AND LAT WITH LOWER CORNER [0,0] \n\n")

    # boxes = [Box(["longitude", "latitude"], [0, 0], [1, 1]),
    #          Box(["longitude", "latitude"], [0, 0], [5, 5]),
    #          Box(["longitude", "latitude"], [0, 0], [10, 10]),
    #          Box(["longitude", "latitude"], [0, 0], [45, 45]),
    #          Box(["longitude", "latitude"], [0, 0], [90, 90]),
    #          ]

    # for box in boxes:
    #     benchmark_boxes(box)

    print("EXTRACTION OF BOXES WITH INCREASING SIZE IN LON AND LAT WITH CENTER [0,0] \n\n")

    boxes = [Box(["longitude", "latitude"], [-0.5, -0.5], [0.5, 0.5]),
            #  Box(["longitude", "latitude"], [-2.5, -2.5], [2.5, 2.5]),
            #  Box(["longitude", "latitude"], [-5, -5], [5, 5]),
            #  Box(["longitude", "latitude"], [-22.5, -22.5], [22.5, 22.5]),
            #  Box(["longitude", "latitude"], [-45, -45], [45, 45]),
             ]

    for box in boxes:
        benchmark_boxes(box)
