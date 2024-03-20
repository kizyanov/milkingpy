import asyncio
from loguru import logger
from kucoin.ws_client import KucoinWsClient
from kucoin.client import WsToken
from decouple import config
import aiohttp
from aiotinydb import AIOTinyDB
from interesticker import INTEREST_TICKET
from tinydb import Query

symbol_status = {}

TIME_SCALP = "_1day"

Tickert = Query()

storage = {}


def db(command: str, ticket: str, funds: float | None = None):
    result = 0
    match command:
        case "remove":
            storage.pop(ticket)
        case "update":
            storage[ticket] = funds
        case "count":
            result = int(ticket in storage)
    return result


async def send_telegram_msg(msg: str):
    """."""
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
    logger.debug("Welcome to Milking Bot")

    async def deal_msg(msg):
        match msg:
            case {
                "data": dict() as candle,
                "type": "message",
                "subject": "trade.candles.update",
            }:
                open_price = float(candle.get("candles")[1])
                close_price = float(candle.get("candles")[2])

                if open_price > close_price:  # open price > close price
                    if db("count", candle.get("symbol")) == 1:
                        db("remove", candle.get("symbol"))
                        msg = (
                            f'Sell {candle.get("symbol")} {open_price=} {close_price=}'
                        )
                        logger.debug(msg)
                        await send_telegram_msg(msg)

                elif open_price < close_price:
                    if db("count", candle.get("symbol")) == 0:
                        db("update", candle.get("symbol"), funds=199.22)
                        msg = f'Buy {candle.get("symbol")} {open_price=} {close_price=}'
                        logger.debug(msg)
                        await send_telegram_msg(msg)

    symbols = ",".join([ticket + TIME_SCALP for ticket in INTEREST_TICKET])

    ws_client = await KucoinWsClient.create(None, WsToken(), deal_msg, private=False)

    await ws_client.subscribe(f"/market/candles:{symbols}")

    while True:
        await asyncio.sleep(0)


asyncio.run(main())
