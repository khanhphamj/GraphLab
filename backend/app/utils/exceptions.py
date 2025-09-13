"""Custom exceptions for the application"""

class GraphLabException(Exception):
    """Base exception class for GraphLab"""
    def __init__(self, message: str, code: str = None):
        self.message = message
        self.code = code
        super().__init__(self.message)


class AuthenticationError(GraphLabException):
    """Raised when authentication fails"""
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, "AUTHENTICATION_ERROR")


class AuthorizationError(GraphLabException):
    """Raised when authorization fails"""
    def __init__(self, message: str = "Access denied"):
        super().__init__(message, "AUTHORIZATION_ERROR")


class ValidationError(GraphLabException):
    """Raised when validation fails"""
    def __init__(self, message: str = "Validation failed"):
        super().__init__(message, "VALIDATION_ERROR")


class NotFoundError(GraphLabException):
    """Raised when a resource is not found"""
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, "NOT_FOUND_ERROR")


class ConflictError(GraphLabException):
    """Raised when there's a conflict (e.g., duplicate email)"""
    def __init__(self, message: str = "Conflict occurred"):
        super().__init__(message, "CONFLICT_ERROR")


class RateLimitError(GraphLabException):
    """Raised when rate limit is exceeded"""
    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(message, "RATE_LIMIT_ERROR")
