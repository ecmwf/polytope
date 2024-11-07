class CoverageCollection:
    def __init__(self, covjson):
        if isinstance(covjson, dict):
            self.coverage = covjson

        self.type = self.coverage["type"]

        if self.type == "Coverage":
            raise TypeError("CoverageCollection class takes CoverageCollection not Coverage")

        self.coverages = self.coverage["coverages"]
