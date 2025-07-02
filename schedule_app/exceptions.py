class APIError(Exception):
    """Raised when an upstream API request fails.

    This is used for token errors or other issues communicating
    with external services.
    """

    def __init__(self, description: str) -> None:
        self.description = description
        super().__init__(description)
