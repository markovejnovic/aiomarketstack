"""Contains the type definitions used by Markestack."""

from __future__ import annotations

from typing import TYPE_CHECKING, NotRequired, Required, Sequence, TypedDict

if TYPE_CHECKING:
    from datetime import date


class Eod(TypedDict):
    """Represents an end-of-day marketstack return type."""

    open: Required[float]
    high: Required[float]
    low: Required[float]
    close: Required[float]
    volume: Required[float]
    split_factor: Required[float]
    dividend: Required[float]
    symbol: Required[str]
    exchange: Required[str]
    date: Required[date]


class RawEod(TypedDict):
    """The eod response, as returned from marketstack."""

    open: Required[float]
    high: Required[float]
    low: Required[float]
    close: Required[float]
    volume: Required[float]
    split_factor: Required[float]
    dividend: Required[float]
    symbol: Required[str]
    exchange: Required[str]
    date: Required[str]


class Pagination(TypedDict):
    """The marketstack pagination."""

    limit: Required[int]
    offset: Required[int]
    count: Required[int]
    total: Required[int]


class ErrorContextSymbol(TypedDict):
    """The marketstack API error symbol.

    Whenever a validation error is given, additional information will be encoded within
    this object.
    """

    key: str
    message: str


class ErrorResponse(TypedDict):
    """Markestack error object.

    If an error occurs, marketstack returns the error code, and the error message.
    """

    code: Required[str]
    message: Required[str]
    context: NotRequired[Sequence[ErrorContextSymbol]]

class EodResponse(TypedDict):
    """Response for the /eod endpoint."""

    pagination: Required[Pagination]
    data: Required[list[RawEod]]
    error: NotRequired[ErrorResponse]


Response = EodResponse
