"""Marketstack Error Response Errors."""

from typing import Self

from aiohttp.client import ClientResponse


class ResponseError(Exception):
    """A failure response was received from Marketstack."""

    response: ClientResponse

    def __init__(self: Self, response: ClientResponse) -> None:
        """Create a new response exception stemming from a client response."""
        self.response = response


class UnhandledResponseError(ResponseError):
    """An unexpected http error code was returned."""


class UnauthorizedError(ResponseError):
    """An unauthorized http response code was returned."""


class InvalidAccessKeyError(UnauthorizedError):
    """An invalid API key was supplied."""


class MissingAccessKeyError(UnauthorizedError):
    """No API Access key was supplied."""


class InactiveUserError(UnauthorizedError):
    """The given user account is inactive."""


class ForbiddenError(ResponseError):
    """The forbidden http response code was returned."""


class HttpsAccessRestrictedError(ForbiddenError):
    """Https is not supported with this plan."""


class FunctionAccessRestrictedError(ForbiddenError):
    """The given API endpoint is not supported on this access plan."""


class NotFoundError(ResponseError):
    """The http not found response was returned."""


class InvalidApiFunctionError(NotFoundError):
    """The given API endpoint does not exist."""


class ResourceNotFoundError(NotFoundError):
    """The resource is not found."""


class TooManyRequestsError(ResponseError):
    """The too many requests http response was returned."""


class UsageLimitReachedError(TooManyRequestsError):
    """The given user account has reached its monthly request volume."""


class RateLimitReachedError(TooManyRequestsError):
    """The given account has reached the rate limit."""


class InternalErrorError(ResponseError):
    """An internal marketstack error has ocurred."""
