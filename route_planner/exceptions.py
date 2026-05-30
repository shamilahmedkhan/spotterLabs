class RoutePlanningError(Exception):
    pass


class ExternalServiceError(RoutePlanningError):
    pass


class OptimizationError(RoutePlanningError):
    pass
