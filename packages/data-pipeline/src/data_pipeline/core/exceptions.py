class PipelineError(Exception):
    """Base pipeline exception."""


class ProviderRequestError(PipelineError):
    """Raised when provider request failed after retries."""


class ProviderTemporaryError(ProviderRequestError):
    """Raised when provider request can be retried."""


class ValidationError(PipelineError):
    """Raised when a record is invalid."""


class ProviderNormalizationError(ValidationError):
    """Raised when provider payload schema cannot be normalized."""
