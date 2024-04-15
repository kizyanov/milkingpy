import asyncio
from kucoin.ws_client import KucoinWsClient
from kucoin.client import WsToken
from decouple import config
import aiohttp
from loguru import logger

from kucoin.client import User, Trade

book = {}

key = config("KEY", cast=str)
secret = config("SECRET", cast=str)
passphrase = config("PASSPHRASE", cast=str)
base_stable = config("BASE_STABLE", cast=str)


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


def get_account_info():
    """Get all assert in account."""
    user = User(
        key=key,
        secret=secret,
        passphrase=passphrase,
        is_sandbox=False,
    )

    order = Trade(
        key=key,
        secret=secret,
        passphrase=passphrase,
        is_sandbox=False,
    )

    for asset in user.get_account_list():
        if asset["type"] == "trade":
            if (
                asset["currency"] != base_stable
            ):  # Получаем все ордера в которых участвует этот актив
                symbol_order = order.get_order_list(
                    **{
                        "symbol": f'{asset["currency"]}-{base_stable}',
                        "status": "active",
                    }
                )
                for order in symbol_order["items"]:
                    book[asset["currency"]] = {
                        "available": asset["available"],
                        "orderId": order["id"],
                    }
            else:
                book[asset["currency"]] = {"available": asset["available"]}
    logger.debug(book)


async def main():
    async def event(msg):
        match msg: # Add Stop Order Event
            case {
                "data": dict() as candle,
                "type": "message",
                "subject": "trade.candles.update",
            }:
                pass
                # logger.debug(f"Candles Update: {msg}")
            case {
                "data": dict() as balance,
                "type": "message",
                "subject": "account.balance",
            }:
                book[balance["currency"]] = balance["available"]
                logger.debug(book)

            case {
                "data": dict() as order,
                "type": "message",
                "topic": "/spotMarket/tradeOrdersV2",
            }:
                logger.debug(order)
                symbol = order["symbol"].replace(f"-{base_stable}", "")
                match order["type"]:
                    case "canceled":
                        del book[symbol]["orderId"]
                    case "open":
                        if symbol in book:
                            book[symbol]["orderId"] = order["orderId"]
                        else:
                            book[symbol] = {"available": 0, "orderId": order["orderId"]}
                logger.debug(book)
            case {
                "data": dict() as order,
                "type": "message",
                "subject": "stopOrder",
            }:
                symbol = order["symbol"].replace(f"-{base_stable}", "")
                if order['type'] == 'cancel':
                    if symbol in book:
                        del book[symbol]["orderId"]
    get_account_info()

    client = WsToken(
        key=key,
        secret=secret,
        passphrase=passphrase,
        url="https://openapi-v2.kucoin.com",
    )

    balance = await KucoinWsClient.create(None, client, event, private=True)
    order = await KucoinWsClient.create(None, client, event, private=True)
    cancel_order = await KucoinWsClient.create(None, client, event, private=True)
    candle = await KucoinWsClient.create(None, WsToken(), event, private=False)

    await balance.subscribe("/account/balance")
    await candle.subscribe("/market/candles:BTC-USDT_1hour")
    await order.subscribe("/spotMarket/tradeOrdersV2")
    await cancel_order.subscribe("/spotMarket/advancedOrders")

    while True:
        await asyncio.sleep(60)


asyncio.run(main())
