import asyncio
from loguru import logger
from kucoin.ws_client import KucoinWsClient
from kucoin.client import WsToken
from decouple import config, Csv
import aiohttp
from aiotinydb import AIOTinyDB
from interesticker import INTEREST_TICKET
from tinydb import Query
from kucoin.client import Market

from datetime import datetime, UTC

symbol_status = {}

TIME_SCALP = "_1hour"

Tickert = Query()

storage = {}
fee = 0.1


def db(
    command: str, ticket: str, cost: float | None = None, funds: float | None = None
):
    result = 0
    match command:
        case "remove":
            storage.pop(ticket)
        case "update":
            storage[ticket] = {"funds": funds, "cost": cost}
        case "count":
            result = int(ticket in storage)
        case "cost":
            result = storage[ticket]["cost"]
    return result


async def send_telegram_msg(msg: str):
    """Отправка сообщения в телеграмм."""
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"https://api.telegram.org/bot{config('TELEGRAM_BOT_API_KEY', cast=str)}/sendMessage",
            json={
                "chat_id": config("TELEGRAM_BOT_CHAT_ID", cast=str),
                "parse_mode": "HTML",
                "disable_notification": True,
                "text": msg,
            },
        ):
            pass


async def main():

    tickets = config("TICKETS", cast=Csv(str))
    logger.debug(f"Trade for {len(tickets)} tickets, enjoy!")

    async def deal_msg(msg):
        match msg:
            case {
                "data": dict() as candle,
                "type": "message",
                "subject": "trade.candles.update",
            }:
                open_price = float(candle.get("candles")[1])
                close_price = float(candle.get("candles")[2])
                symbol = candle.get("symbol")

                if open_price > close_price:
                    if db("count", symbol) == 1:
                        get_cost = db("cost", symbol)
                        logger.debug(f"{get_cost=}")
                        percent_dirty_profit = (get_cost / close_price) * 100 - 100
                        logger.debug(f"{percent_dirty_profit=}")
                        clear_percent = percent_dirty_profit - fee - fee

                        if clear_percent > 0:
                            emoji = "✅"
                        else:
                            emoji = "❌"
                        msg = f"{emoji} Sell \t\t{symbol} \t\topen:{open_price} \t\tclose:{close_price} \t\tpr:{clear_percent:.3f}%"
                        logger.debug(msg)
                        await send_telegram_msg(msg)
                        db("remove", symbol)

                elif open_price < close_price:
                    if db("count", symbol) == 0:
                        db("update", symbol, cost=close_price, funds=199.22)
                        msg = f"Buy \t\t{symbol} \t\topen:{open_price} \t\tclose:{close_price} \t\tpr:{(close_price/open_price) * 100 -100:.3f}%"
                        logger.debug(msg)

    symbols = ",".join([ticket + TIME_SCALP for ticket in tickets])

    ws_client = await KucoinWsClient.create(None, WsToken(), deal_msg, private=False)

    await ws_client.subscribe(f"/market/candles:{symbols}")

    while True:
        await asyncio.sleep(60)


async def main1():
    total_coins = len(INTEREST_TICKET)

    client = Market()

    while True:

        now = datetime.now(tz=UTC).strftime("%H.%M.%S")
        if now in [
            "00.00.00",
            "01.00.00",
            "02.00.00",
            "03.00.00",
            "04.00.00",
            "05.00.00",
            "06.00.00",
            "07.00.00",
            "08.00.00",
            "09.00.00",
            "10.00.00",
            "11.00.00",
            "12.00.00",
            "13.00.00",
            "14.00.00",
            "15.00.00",
            "16.00.00",
            "17.00.00",
            "18.00.00",
            "19.00.00",
            "20.00.00",
            "21.00.00",
            "22.00.00",
            "23.00.00",
            "24.00.00",
        ]:
            profit_dirty = 0

            for i in INTEREST_TICKET:
                data = float(client.get_24h_stats(i)["changeRate"])
                logger.debug(f"{i} \t {data}")
                profit_dirty += data

            profit = profit_dirty / total_coins * 100

            logger.debug(f"PROFIT: {profit:.2f} %")

            await send_telegram_msg(f"Profit is: {profit:.2f}%")

        await asyncio.sleep(1)


asyncio.run(main1())
