class AuthException(Exception):
    """Base class for authentication-related exceptions."""

class EmailAlreadyRegistered(AuthException):
    pass

class InvalidCredentials(AuthException):
    pass

class InvalidOTP(AuthException):
    pass

class OTPExpired(AuthException):
    pass

class UserNotVerified(AuthException):
    pass

class UserNotFound(AuthException):
    pass

class UserAlreadyVerified(AuthException):
    pass
