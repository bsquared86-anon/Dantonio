from fastapi import HTTPException
from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_404_NOT_FOUND,
    HTTP_500_INTERNAL_SERVER_ERROR,
)

class BaseCustomException(Exception):
    def __init__(self, message: str, status_code: int = HTTP_500_INTERNAL_SERVER_ERROR):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

class ValidationError(BaseCustomException):
    def __init__(self, message: str):
        super().__init__(message, HTTP_400_BAD_REQUEST)

class AuthenticationError(BaseCustomException):
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, HTTP_401_UNAUTHORIZED)

