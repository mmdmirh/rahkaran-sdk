class RahkaranError(Exception):
    """Base exception for Rahkaran Client."""
    pass

class RahkaranAuthError(RahkaranError):
    """Raised when authentication fails (401/403)."""
    pass

class RahkaranServerError(RahkaranError):
    """Raised when the server returns a 5xx error."""
    pass

class RahkaranClientError(RahkaranError):
    """Raised when the client sends a bad request (400)."""
    pass
