"""Common testing utilities."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Generator, TypeVar

import numpy as np

K = TypeVar("K")
V = TypeVar("V")
T = TypeVar("T")

_HOLIDAYS = {
    "NYSE": {
        date(2020, 1, 1),
        date(2020, 1, 20),
        date(2020, 2, 17),
        date(2020, 4, 10),
        date(2020, 5, 25),
        date(2020, 7, 3),
        date(2020, 9, 7),
        date(2020, 11, 26),
        date(2020, 12, 25),
        date(2021, 1, 1),
        date(2021, 1, 18),
        date(2021, 2, 15),
        date(2021, 4, 2),
        date(2021, 5, 31),
        date(2021, 7, 5),
        date(2021, 9, 6),
        date(2021, 11, 25),
        date(2021, 12, 24),
        date(2022, 1, 17),
        date(2022, 2, 21),
        date(2022, 4, 15),
        date(2022, 5, 30),
        date(2022, 6, 20),
        date(2022, 7, 4),
        date(2022, 9, 5),
        date(2022, 11, 24),
        date(2022, 12, 26),
        date(2023, 1, 2),
        date(2023, 1, 16),
        date(2023, 2, 20),
        date(2023, 4, 7),
        date(2023, 5, 29),
        date(2023, 6, 19),
        date(2023, 7, 4),
        date(2023, 9, 4),
        date(2023, 11, 23),
        date(2023, 12, 25),
    },
    "XNAS": {
        # 2022
        date(2022, 1, 17),
        date(2022, 2, 21),
        date(2022, 4, 15),
        date(2022, 5, 30),
        date(2022, 6, 20),
        date(2022, 7, 4),
        date(2022, 9, 5),
        date(2022, 11, 24),
        #date(2022, 11, 25), <- Early close
        date(2022, 12, 26),
        # 2023
        date(2023, 1, 2),
        date(2023, 1, 16),
        date(2023, 2, 20),
        date(2023, 4, 7),
        date(2023, 5, 29),
        date(2023, 6, 19),
        #date(2023, 7, 3), <- Early close
        date(2023, 7, 4),
        date(2023, 9, 4),
        date(2023, 11, 23),
        #date(2023, 11, 24), <- Early close
        date(2023, 12, 25),
        # 2024
        date(2024, 1, 1),
        date(2024, 1, 15),
        date(2024, 2, 19),
        date(2024, 3, 29),
        date(2024, 5, 27),
        date(2024, 6, 19),
        date(2024, 7, 3),
        date(2024, 7, 4),
        date(2024, 9, 2),
        date(2024, 11, 28),
        date(2024, 11, 29),
        date(2024, 12, 25),
    },
}


def is_market_open(exchange: str, for_date: date) -> bool:
    """Query whether the exchange was open for the given date."""
    friday_index = 5
    return for_date.isoweekday() <= friday_index and for_date not in _HOLIDAYS[exchange]


def busday_count(
    exchange: str,
    date_from: date,
    date_to: date,
    inclusive: bool = False,
) -> int:
    """Calculate the number of days the market was open for between the given dates.

    Args:
    ----
        exchange: The target exchange.
        date_from: The start date.
        date_to: The end date.
        inclusive: Whether the last date is to be included.
    """
    end_date = date_to + timedelta(days=1) if inclusive else date_to

    holiday_count = len([h for h in _HOLIDAYS[exchange] if date_from <= h < end_date])

    return int(np.busday_count(date_from, end_date)) - holiday_count


def busdays(
    exchange: str,
    date_from: date,
    date_to: date,
    inclusive: bool = False,
) -> Generator[date, None, None]:
    """Create a generator of days for which the given market is open.

    Args:
    ----
        exchange: The target exchange.
        date_from: The start date.
        date_to: The end date.
        inclusive: Whether the last date is to be included.
    """
    end_date = date_to + timedelta(days=1) if inclusive else date_to
    count = (end_date - date_from).days
    all_date_gen = (date_from + timedelta(days=n) for n in range(count))

    return (d for d in all_date_gen if is_market_open(exchange, d))
