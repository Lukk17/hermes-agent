"""
src/exceptions.py - Standardized exception classes.

All custom exceptions should be defined here.
"""


class CryptoMonitorError(Exception):
    """Base exception for all crypto-monitor errors."""
    pass


class APIKeyMissingError(CryptoMonitorError):
    """
    Raised when a required API key is not configured.
    
    Attributes:
        service: Name of the service requiring the key
        env_var: Environment variable name that should contain the key
    """
    
    def __init__(self, service: str, env_var: str, docs_url: str = ""):
        self.service = service
        self.env_var = env_var
        self.docs_url = docs_url or f"https://{service.lower()}.com/api"
        super().__init__(
            f"❌ {service} requires API key. "
            f"Set {env_var} environment variable. "
            f"Get key at {self.docs_url}"
        )


class RateLimitedError(CryptoMonitorError):
    """
    Raised when an API refuses a request with HTTP 429.

    Attributes:
        service: Name of the service that rate-limited the caller
    """

    def __init__(self, service: str):
        self.service = service
        super().__init__(f"{service} rate-limited the request (HTTP 429)")


class DataCollectionError(CryptoMonitorError):
    """
    Raised when a collector fails to fetch data.
    
    Attributes:
        collector: Name of the collector that failed
        error: Description of the error
    """
    
    def __init__(self, collector: str, error: str):
        self.collector = collector
        self.error = error
        super().__init__(f"{collector} failed: {error}")


class SchemaValidationError(CryptoMonitorError):
    """
    Raised when data does not match expected schema.
    
    Attributes:
        schema: Name of the schema that failed validation
        field: Field that failed validation
    """
    
    def __init__(self, schema: str, field: str, expected: str, actual: str):
        self.schema = schema
        self.field = field
        self.expected = expected
        self.actual = actual
        super().__init__(
            f"Schema validation failed for {schema}.{field}: "
            f"expected {expected}, got {actual}"
        )
