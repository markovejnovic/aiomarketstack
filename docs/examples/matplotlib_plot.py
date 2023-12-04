from __future__ import annotations

import asyncio
from datetime import date

import matplotlib.pyplot as plt

from aiomarketstack import HttpMarketstackClient, MarketstackPlan
from aiomarketstack.exceptions import ResponseError
from aiomarketstack.types import Eod


async def main() -> None:
    date_range = (date(2023, 1, 1), date(2023, 1, 31))

    async with HttpMarketstackClient(
        "your-token-here",
        MarketstackPlan.FREE,
    ) as client:
        try:
            eod_values: tuple[Eod, ...] = (
                await client.get_eod_range(("AMZN", ), date_range)
            )
        except ResponseError as resp_err:
            print(f"Uh-oh, a response error ocurred: {resp_err}")
            raise

    # Note that there will be missing data (if the market was closed).
    plt_xaxis = [eod["date"] for eod in eod_values]
    plt_yaxes = {
        key: [eod[key] for eod in eod_values]
        for key in ("open", "high", "low", "close")
    }

    for label, data in plt_yaxes.items():
        plt.plot(plt_xaxis, data, label=label)
    plt.legend()
    plt.grid()
    plt.title("End-of-day prices for AMZN for January 2023")
    plt.xlabel("Date in January")
    plt.ylabel("Price in $")
    plt.show()


asyncio.run(main())
