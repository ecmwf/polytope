class Coverage:
    def __init__(self, covjson):
        if isinstance(covjson, dict):
            self.coverage = covjson

        self.type = self.coverage.pop("type")

        if self.type == "CoverageCollection":
            raise TypeError("Coverage class takes coverage not CoverageCollection")
