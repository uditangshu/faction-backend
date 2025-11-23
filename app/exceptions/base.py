"""Base exception classes"""


class AppException(Exception):
    """Base application exception"""

    def __init__(self, message: str = "An error occurred"):
        self.message = message
        super().__init__(self.message)

