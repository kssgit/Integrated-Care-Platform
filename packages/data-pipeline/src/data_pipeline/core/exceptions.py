class PipelineError(Exception):
    """Base pipeline exception."""


class ProviderRequestError(PipelineError):
    """Raised when provider request failed after retries."""


class ValidationError(PipelineError):
    """Raised when a record is invalid."""

