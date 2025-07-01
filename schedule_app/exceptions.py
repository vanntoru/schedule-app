class APIError(Exception):
    """Raised when an upstream API request fails."""

    def __init__(self, description: str) -> None:
        self.description = description
        super().__init__(description)
