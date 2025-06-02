from typing import Optional

class GameAPIError(Exception):
    """Custom exception for Steam API related errors.
    
        Attributes:
            message (str): Error message
            status_code (int, optional): HTTP status code if available
    """
    def __init__(self, message: str, status_code: Optional[int] = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)