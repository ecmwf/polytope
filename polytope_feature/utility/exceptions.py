class PolytopeError(Exception):
    pass


class BadRequestError(PolytopeError):
    def __init__(self, pre_path):
        self.pre_path = pre_path
        self.message = f"No data for {pre_path} is available on the FDB."


class AxisOverdefinedError(PolytopeError, KeyError):
    def __init__(self, axis):
        self.axis = axis
        self.message = (
            f"Axis {axis} is overdefined. You have used it in two or more input polytopes which"
            f"cannot form a union (because they span different axes)."
        )


class AxisUnderdefinedError(PolytopeError, KeyError):
    def __init__(self, axis):
        self.axis = axis
        self.message = f"Axis {axis} is underdefined. It does not appear in any input polytope."


class AxisNotFoundError(PolytopeError, KeyError):
    def __init__(self, axis):
        self.axis = axis
        self.message = f"Axis {axis} does not exist in the datacube."


class UnsliceableShapeError(PolytopeError, KeyError):
    def __init__(self, axis):
        self.axis = axis
        self.message = f"Higher-dimensional shape does not support unsliceable axis {axis.name}."
