class DetectionException(Exception):
    """Base class for detection exceptions."""

class DetectionNotFound(DetectionException):
    pass

class GuestLimitReached(DetectionException):
    pass

