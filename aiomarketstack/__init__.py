"""Async client for the marketstack API.

.. warning::
   This client does not expose the *adjusted* prices as Marketstack's data is
   incorrect for them.
   Running a query for MNST on 2023-03-28 will show that, although there was a
   split, the adjusted prices are not corrected.

   .. code-block::
      :language: python

      async with MarketstackClient(token) as cli:
          result = await cli.get_eod(['MNST', date(2023, 3, 28)])
      assert 2 == result["split_factor"]

      # All of these fail
      for v in ["high", "low", "close"]:
          assert result[f"adj_{v}"] == result[v] * result["split_factor"]
"""

from __future__ import annotations

import warnings
from datetime import date, datetime
from enum import IntEnum
from typing import (
    TYPE_CHECKING,
    AsyncGenerator,
    Callable,
    Collection,
    Literal,
    Self,
)

import aiohttp
import structlog
from aiohttp import ClientResponse, ClientSession

from aiomarketstack.exceptions import (
    ForbiddenError,
    FunctionAccessRestrictedError,
    HttpsAccessRestrictedError,
    InactiveUserError,
    InternalErrorError,
    InvalidAccessKeyError,
    InvalidApiFunctionError,
    MissingAccessKeyError,
    NotFoundError,
    RateLimitReachedError,
    ResourceNotFoundError,
    ResponseError,
    TooManyRequestsError,
    UnauthorizedError,
    UnhandledResponseError,
    UsageLimitReachedError,
)

if TYPE_CHECKING:
    from .types import Eod, EodResponse, RawEod, Response

HTTP_BASE_URL = "http://api.marketstack.com/v1/eod"
HTTPS_BASE_URL = "https://api.marketstack.com/v1/eod"


class MarketstackPlan(IntEnum):
    """The type of the marketstack plan."""

    FREE = 0
    BASIC = 1
    PROFESSIONAL = 2
    BUSINESS = 3


class _MarketstackClient:
    def __init__(
        self: Self,
        base_url: str,
        access_key: str,
        plan: MarketstackPlan = MarketstackPlan.BASIC,
    ) -> None:
        """Initialize the MarketstackClient.

        Args:
        ----
            access_key: The marketstack token.
            plan:  The plan to use when connecting to marketstack.
            over_tls: Whether to use https or http for requests. Must
                match the permission level of your token.
            base_url: The base url of the API, stripped of the protocol.
        """
        self.base_url = base_url
        self.plan = plan
        self._client_session: ClientSession | None = None
        self._access_key = access_key
        self._log: structlog.stdlib.BoundLogger = structlog.get_logger()

    async def get_eod(
        self: Self,
        symbols: Collection[str],
        transaction_date: date,
        exchange_filter: str | None = None,
    ) -> tuple[Eod, ...]:
        """Query the EOD data for the given date.

        Args:
        ----
            symbols (Collection[str]): The symbols to search
            transaction_date (datetime.date): The target date in UTC+0.
            exchange_filter (str | None): The exchange MIC to filter by.

        Returns:
        -------
            The EOD data for the given date.
        """
        # Higher plans support querying directly for the eod at the given date.
        # The free plan however only supports ranges, so we need to use that.
        if self.plan < MarketstackPlan.BASIC:
            return (
                await self.get_eod_range(
                    symbols, (transaction_date, transaction_date), exchange_filter,
                )
            )

        async with self._session as sess:
            url = f"{self.base_url}/{self._format_date(transaction_date)}"
            params = {
                "access_key": self._access_key,
                "symbols": ",".join(symbols),
                **({} if exchange_filter is None else {"exchange": exchange_filter}),
            }
            log = self._log.bind(url=url, params=params)

            async with sess.get(url, params=params) as resp:
                body: EodResponse = await resp.json()
                log = log.bind(body=body, status_code=resp.status)
                log.debug("Finished Query.")

                await self._handle_if_error(resp, body, log)
                if (act_len := len(body["data"])) != 1:
                    log.error(
                        "Length of the response data is not 1", actual_length=act_len,
                    )

                return tuple(self._deserialize_eod(raw_eod) for raw_eod in body["data"])

    async def get_eod_range(
        self: Self,
        symbols: Collection[str],
        date_range: tuple[date, date],
        exchange_filter: str | None = None,
        max_requests: int = 10,
    ) -> tuple[Eod, ...]:
        """Query the EOD data for the given date range.

        Args:
        ----
            symbols: The symbols to search.
            date_range: The range of dates to search between.
            exchange_filter: The exchange MIC to filter by.
            max_requests: The maximum number of requests to make.

        Returns:
        -------
            A sequence of EOD values for the given date range, left-inclusive.

        If a number greater than max_requests is given, then the function will exit
        early with partial data, preventing making more than the given number of
        requests.
        """
        return tuple([
            self._deserialize_eod(d)
            async for d in self._get_eod_range_helper(
                symbols, date_range, exchange_filter, max_requests,
            )
        ])

    async def _get_eod_range_helper(
        self: Self,
        symbols: Collection[str],
        date_range: tuple[date, date],
        exchange_filter: str | None,
        max_requests: int = 10,
    ) -> AsyncGenerator[RawEod, None]:
        """Get the EOD range, returning a generator of bodies."""
        async with self._session as sess:
            url = self.base_url
            params = {
                "access_key": self._access_key,
                "symbols": ",".join(symbols),
                "date_from": self._format_date(date_range[0]),
                "date_to": self._format_date(date_range[1]),
                "limit": "1000",
                **({} if exchange_filter is None else {"exchange": exchange_filter}),
            }
            log = self._log.bind(url=url, params=params)

            for _ in range(max_requests):
                async with sess.get(url, params=params) as resp:
                    body: EodResponse = await resp.json()
                    log = log.bind(body=body, status_code=resp.status)
                    log.debug("Finished Query.")

                    await self._handle_if_error(resp, body, log)

                for d in body["data"]:
                    yield d

                total_so_far = (p := body["pagination"])["limit"] * p["offset"] + p[
                    "count"
                ]
                if total_so_far == body["pagination"]["total"]:
                    break

    async def __aenter__(self: Self) -> Self:
        """Start the HTTP session."""
        self._client_session = aiohttp.ClientSession()
        return self

    async def __aexit__(self: Self, *_: object) -> None:
        """Close the HTTP session."""
        await self._session.close()

    async def _handle_if_error(
        self: Self,
        resp: ClientResponse,
        body: Response,
        log: structlog.stdlib.BoundLogger,
    ) -> None:
        http_code_ok = 200
        if resp.status == http_code_ok:
            return

        err_map: dict[
            Literal["default"] | int,
            dict[str, Callable[[], ResponseError]],
        ] = {
            401: {
                "invalid_access_key": lambda: InvalidAccessKeyError(resp),
                "missing_access_key": lambda: MissingAccessKeyError(resp),
                "inactive_user": lambda: InactiveUserError(resp),
                "default": lambda: UnauthorizedError(resp),
            },
            403: {
                "https_access_restricted": lambda: HttpsAccessRestrictedError(resp),
                "function_access_restricted":
                    lambda: FunctionAccessRestrictedError(resp),
                "default": lambda: ForbiddenError(resp),
            },
            404: {
                "invalid_api_function": lambda: InvalidApiFunctionError(resp),
                "404_not_found": lambda: ResourceNotFoundError(resp),
                "default": lambda: NotFoundError(resp),
            },
            429: {
                "usage_limit_reached": lambda: UsageLimitReachedError(resp),
                "rate_limit_reached": lambda: RateLimitReachedError(resp),
                "default": lambda: TooManyRequestsError(resp),
            },
            500: {
                "default": lambda: InternalErrorError(resp),
            },
            "default": {
                "default": lambda: UnhandledResponseError(resp),
            },
        }

        log.warning("Unsuccessful response.")

        if resp.status not in err_map:
            default_exc = err_map["default"]["default"]()
            raise default_exc

        err_response = body.get("error")
        if err_response is None:
            err_msg = f"Unexpected response {body} missing an error."
            raise RuntimeError(err_msg)

        error = err_map[resp.status].get(
            err_response["message"],
            err_map[resp.status]["default"],
        )()
        raise error

    @property
    def _session(self: Self) -> ClientSession:
        if self._client_session is None:
            err_msg = (
                "MarketstackClient must be initialized within a context manager."
            )
            raise RuntimeError(err_msg)
        return self._client_session

    @staticmethod
    def _format_date(d: date) -> str:
        return d.strftime("%Y-%m-%d")

    @staticmethod
    def _deserialize_eod(raw_eod: RawEod) -> Eod:
        return {
            "open": raw_eod["open"],
            "high": raw_eod["high"],
            "low": raw_eod["low"],
            "close": raw_eod["close"],
            "volume": raw_eod["volume"],
            "split_factor": raw_eod["split_factor"],
            "dividend": raw_eod["dividend"],
            "symbol": raw_eod["symbol"],
            "exchange": raw_eod["exchange"],
            "date": datetime.fromisoformat(raw_eod["date"]).date(),
        }


class HttpMarketstackClient(_MarketstackClient):
    """The main marketstack client.

    For each marketstack token, you only need one of these.
    """

    def __init__(
        self: Self,
        access_key: str,
        plan: MarketstackPlan = MarketstackPlan.BASIC,
    ) -> None:
        """Create a HTTP Marketstack Client."""
        super().__init__(HTTP_BASE_URL, access_key, plan)


class HttpsMarketstackClient(_MarketstackClient):
    """The main marketstack client.

    For each marketstack token, you only need one of these.
    """

    def __init__(
        self: Self,
        access_key: str,
        plan: MarketstackPlan = MarketstackPlan.BASIC,
    ) -> None:
        """Create a HTTPS Marketstack Client."""
        if plan == MarketstackPlan.FREE:
            warnings.warn("Using the free plan isn't likely to work over SSL.",
                          stacklevel=2)

        super().__init__(HTTP_BASE_URL, access_key, plan)
