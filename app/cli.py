import typer
import asyncio
import aiohttp
from rich.console import Console
from rich.table import Table
from typing import Optional

app = typer.Typer()
console = Console()


async def make_request(url: str, method: str) -> dict:
    """."""
    async with aiohttp.ClientSession() as session:
        match method:
            case "GET":
                async with session.get(url) as response:
                    result = await response.json()
                    return result
            case "POST":
                async with session.post(url) as response:
                    result = await response.json()
                    return result


bad_token = ["WBTC"]


@app.command()
def hello(name: str):
    print(f"Hello {name}")


@app.command()
def get_symbol_list(
    token: Optional[str] = None,
    filter_base: Optional[str] = None,
    trading: bool = True,
    market: Optional[str] = None,
):
    """Get all symbol list on KuCoin"""
    r = asyncio.run(make_request("https://api.kucoin.com/api/v2/symbols", "GET"))

    if r["code"] == "200000":
        table = Table(
            "№",
            "Symbol",
            "Name",
            "BaseCurrency",
            "quoteCurrency",
            "feeCurrency",
            "baseMinSize",
            "quoteMinSize",
            "baseIncrement",
            "quoteIncrement",
            "priceIncrement",
            "minFunds",
            "Market",
            "EnableTrading",
        )
        for index, item in enumerate(
            sorted(
                filter(
                    lambda x: (
                        (x["quoteCurrency"] == filter_base if filter_base else True)
                        and (x["enableTrading"] == trading)
                        and (x["market"] == market if market else True)
                        and not (
                            x["baseCurrency"].endswith("3L")
                            or x["baseCurrency"].endswith("3S")
                            or x["baseCurrency"].endswith("2L")
                            or x["baseCurrency"].endswith("2S")
                            or x["baseCurrency"].endswith("DOWN")
                            or x["baseCurrency"].endswith("UP")
                        )
                        and x["baseCurrency"] not in bad_token
                        and (x["baseCurrency"] == token if token else True)
                    ),
                    r["data"],
                ),
                key=lambda c: float(c["baseMinSize"]),
            )
        ):
            table.add_row(
                str(index),
                item["symbol"],
                item["name"],
                item["baseCurrency"],
                item["quoteCurrency"],
                item["feeCurrency"],
                item["baseMinSize"],
                item["quoteMinSize"],
                item["baseIncrement"],
                item["quoteIncrement"],
                item["priceIncrement"],
                item["minFunds"],
                item["market"],
                str(item["enableTrading"]),
            )
        console.print(table)
    else:
        raise typer.Exit()


if __name__ == "__main__":
    app()
