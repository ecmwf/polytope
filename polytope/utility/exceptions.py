class AxisOverdefinedError(KeyError):
    def __init__(self, axis):
        self.axis = axis
        self.message = (
            f"Axis {axis} is overdefined. You have used it in two or more input polytopes which"
            f"cannot form a union (because they span different axes)."
        )


class AxisUnderdefinedError(KeyError):
    def __init__(self, axis):
        self.axis = axis
        self.message = f"Axis {axis} is underdefined. It does not appear in any input polytope."


class AxisNotFoundError(KeyError):
    def __init__(self, axis):
        self.axis = axis
        self.message = f"Axis {axis} does not exist in the datacube."


class UnsliceableShapeError(KeyError):
    def __init__(self, axis):
        self.axis = axis
        self.message = f"Higher-dimensional shape does not support unsliceable axis {axis.name}."
