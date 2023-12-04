"""Tests the aiomarketstack client."""

from __future__ import annotations

import os
from datetime import date, datetime, timedelta, timezone
from typing import Literal, Mapping, Sequence, TypedDict

import pytest

from aiomarketstack import (
    HttpMarketstackClient,
    HttpsMarketstackClient,
    MarketstackPlan,
)
from aiomarketstack.exceptions import UnauthorizedError

from .util import busdays


class MarketstackTestFixture(TypedDict):
    """Global test parameters."""

    access_token: str

@pytest.fixture()
def marketstack_test_fixture() -> MarketstackTestFixture:
    """Initialize the global marketstack test parameters."""
    access_token = os.getenv("MARKETSTACK_TOKEN_TEST")
    if access_token is None:
        err_msg = "The MARKETSTACK_TOKEN_TEST environment variable must be set."
        raise ValueError(err_msg)

    return { "access_token": access_token }


@pytest.mark.asyncio()
@pytest.mark.parametrize((
    "tickers",
    "target_date",
    "expected_prices",
), [
    (
        ("AMZN", ),
        date(2023, 7, 17),
        {
            "AMZN": {
            "open": 134.56,
            "high": 135.62,
            "low": 133.21,
            "close": 133.56,
            },
        },
    ),
    (
        ("AMZN", "MSFT"),
        date(2023, 7, 17),
        {
            # From finance.yahoo.com/quote/<TICKER>/history
            "AMZN": {
                "open": 134.56,
                "high": 135.62,
                "low": 133.21,
                "close": 133.56,
            },
            "MSFT": {
                "open": 345.68,
                "high": 346.99,
                "low": 342.20,
                "close": 345.73,
            },
        },
    ),
])
async def test_precise(
    marketstack_test_fixture: MarketstackTestFixture,
    tickers: Sequence[str],
    target_date: date,
    expected_prices:
        Mapping[
        str,
        Mapping[
            Literal["open", "high", "low", "close"],
            float,
        ],
    ],
) -> None:
    """Test the get_eod function for a particular date.

    Ensures correct date is returned.
    """
    async with HttpMarketstackClient(
        marketstack_test_fixture["access_token"],
        plan=MarketstackPlan.FREE,
    ) as client:
        results = await client.get_eod(tickers, target_date)

        assert len(results) == len(tickers), \
            "The query returned not as many results as there were tickers."

        for ticker in tickers:
            result = next(res for res in results if res["symbol"] == ticker)

            assert all([
                pytest.approx(value) == result[key]
                and target_date == result["date"]
                for key, value in expected_prices[ticker].items()
            ])


@pytest.mark.asyncio()
@pytest.mark.parametrize((
    "tickers",
    "date_range",
    "stock_exchange",
), [
    (
        ("AMZN", ), (date(2023, 2, 1), date(2023, 7, 17)), "XNAS",
    ),
    (
        (
            "AMZN",
            "MNST",
            "AAPL",
        ),
        (
            datetime.now(tz=timezone.utc).date() - timedelta(days=300),
            datetime.now(tz=timezone.utc).date() - timedelta(days=1),
        ),
        "XNAS",
    ),
])
async def test_range(
    marketstack_test_fixture: MarketstackTestFixture,
    tickers: tuple[str, ...],
    date_range: tuple[date, date],
    stock_exchange: str,
) -> None:
    """Test the get_eod_range function for a range of dates and tickers.

    Does not test the validity of the data (assumes marketstack is correct), but does
    test the data is returned for all open dates.

    """
    async with HttpMarketstackClient(
        marketstack_test_fixture["access_token"],
        plan=MarketstackPlan.FREE,
    ) as cli:
        result = await cli.get_eod_range(tickers, date_range)

        busy_days = set(busdays(stock_exchange, *date_range, inclusive=True))
        received_dates = {res["date"] for res in result}

        assert busy_days == received_dates


@pytest.mark.asyncio()
async def test_ssl_free_account_warns(
    marketstack_test_fixture: MarketstackTestFixture,
) -> None:
    """Test a warning is given for using the SSL client with a free account.

    This is necessary because marketstack does not let you use HTTPS on a free account.
    """
    with pytest.warns():
        async with HttpsMarketstackClient(
            marketstack_test_fixture["access_token"],
            plan=MarketstackPlan.FREE,
        ):
            pass

@pytest.mark.asyncio()
async def test_invalid_access_key() -> None:
    """Tests that using an invalid access key returns an UnauthorizedError."""
    with pytest.raises(UnauthorizedError):
        async with HttpMarketstackClient("i-am-a-bad-access-token",
                                         plan=MarketstackPlan.FREE) as client:
            await client.get_eod(
                ("AMZN", ),
                datetime.now(tz=timezone.utc).date() - timedelta(days=1),
            )

@pytest.mark.asyncio()
async def test_uninitialized_gracefully_fails(
    marketstack_test_fixture:
    MarketstackTestFixture,
) -> None:
    """Test that an uninitialized client gracefully fails."""
    client = HttpMarketstackClient(marketstack_test_fixture["access_token"])
    with pytest.raises(RuntimeError):
        await client.get_eod(
            ("AMZN", ),
            datetime.now(tz=timezone.utc).date() - timedelta(days=1),
        )
