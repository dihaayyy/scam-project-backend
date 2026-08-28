class AuthException(Exception):
    """Base class for authentication-related exceptions."""

class EmailAlreadyRegistered(AuthException):
    pass

class InvalidCredentials(AuthException):
    pass