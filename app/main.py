import asyncio
from kucoin.ws_client import KucoinWsClient
from kucoin.client import WsToken
from decouple import config
import aiohttp
from loguru import logger
import json
import hmac
import hashlib
import base64
import time
from urllib.parse import urljoin
from uuid import uuid1
from kucoin.client import User, Trade, Market

key = config("KEY", cast=str)
secret = config("SECRET", cast=str)
passphrase = config("PASSPHRASE", cast=str)
base_stable = config("BASE_STABLE", cast=str)
currency = config("CURRENCY", cast=str)
time_shift = config("TIME_SHIFT", cast=str)
base_stake = config("BASE_STAKE", cast=int)
fake_price_shift = config("FAKE_PRICE_SHIFT", cast=int)

base_uri = "https://api.kucoin.com"

book = {currency: {"side": "buy", "orderId": "1", "openprice": 1}}


headers_base = {
    "KC-API-KEY": key,
    "Content-Type": "application/json",
    "KC-API-KEY-VERSION": "2",
    "User-Agent": "kucoin-python-sdk/2",
}


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

    market = Market(
        key=key,
        secret=secret,
        passphrase=passphrase,
        is_sandbox=False,
    )

    for asset in user.get_account_list():
        logger.debug(asset)
        if asset["type"] == "trade":  # Get assert only on trade account
            if (
                asset["currency"] != base_stable
            ):  # Получаем все ордера в которых участвует этот актив, кроме USDT
                symbol_order = order.get_order_list(
                    **{
                        "symbol": f'{asset["currency"]}-{base_stable}',
                        # 'type':"limit_stop",
                        # "status":"active",
                    }
                )

                d = order.get_all_stop_order_details(
                    **{
                        "symbol": f'{asset["currency"]}-{base_stable}',
                    }
                )
                logger.debug(d)
                for order in symbol_order["items"]:

                    # logger.debug(order)
                    pass

                    # book[asset["currency"]] = {
                    # "available": asset["available"],
                    # "orderId": order["id"],
                    # }

                    # priceIncrement = market.get_symbol_list_v2()

                    # for ff in priceIncrement:
                    # if ff['baseCurrency'] in book:
                    # book[ff['baseCurrency']].update({"priceIncrement": ff['priceIncrement']})

            else:
                book[asset["currency"]] = {"available": asset["available"]}
    logger.debug(book)


# Нужно как-то выкачать priceIncrement

d = {"sell": "loss", "buy": "entry"}


def get_payload(side: str, symbol: str, price: int, priceIncrement: str):
    place = priceIncrement.split("1")[0].count("0")
    return json.dumps(
        {
            "clientOid": "".join([each for each in str(uuid1()).split("-")]),
            "side": side,
            "type": "limit",
            "stop": d[side],
            "stopPrice": str(price),
            "tradyType": "TRADE",
            "price": str(price),
            "timeInForce": "FOK",
            "symbol": symbol,
            "size": f"{float(base_stake / price):.{place}f}",
        }
    )


def encrypted_msg(msg: str) -> str:
    """."""
    return base64.b64encode(
        hmac.new(secret.encode("utf-8"), msg.encode("utf-8"), hashlib.sha256).digest()
    ).decode()


async def make_stop_limit_order(
    side: str,
    price: int,
    method: str = "POST",
    method_uri: str = "/api/v1/stop-order",
):
    """Make stop limit order by price."""

    now_time = int(time.time()) * 1000

    data_json = get_payload(
        side=side,
        symbol=f"{currency}-{base_stable}",
        price=price,
        priceIncrement="0.00001",
    )

    uri_path = method_uri + data_json
    str_to_sign = str(now_time) + method + uri_path

    headers = {
        "KC-API-SIGN": encrypted_msg(str_to_sign),
        "KC-API-TIMESTAMP": str(now_time),
        "KC-API-PASSPHRASE": encrypted_msg(passphrase),
    }
    headers.update(**headers_base)

    async with aiohttp.ClientSession() as session:
        async with session.post(
            urljoin(base_uri, method_uri),
            headers=headers,
            data=data_json,
        ) as response:
            result = await response.json()
            if result["code"] == "200000":
                return result["data"]["orderId"]


async def cancel_limit_stop_order(
    orderId: str,
    method: str = "DELETE",
    method_uri: str = "/api/v1/stop-order/",
):

    if orderId == "1":
        return

    now_time = int(time.time()) * 1000

    uri_path = method_uri + orderId
    str_to_sign = str(now_time) + method + uri_path

    headers = {
        "KC-API-SIGN": encrypted_msg(str_to_sign),
        "KC-API-TIMESTAMP": str(now_time),
        "KC-API-PASSPHRASE": encrypted_msg(passphrase),
    }
    headers.update(**headers_base)

    async with aiohttp.ClientSession() as session:
        async with session.delete(
            urljoin(base_uri, uri_path),
            headers=headers,
        ) as response:
            result = await response.json()


test_list = []
b = {"side": "sell"}


async def main():

    async def event(msg):
        match msg:  # Add Stop Order Event
            case {
                "data": dict() as candle,
                "type": "message",
                "subject": "trade.candles.update",
            }:

                open_price = float(candle["candles"][1])
                close_price = float(candle["candles"][2])

                if len(test_list) == 0:
                    test_list.append(open_price)
                    logger.info(f"{len(test_list)} {test_list}")

                if open_price != test_list[-1]:

                    if len(test_list) == 20:
                        test_list.pop(0)

                    test_list.append(open_price)

                avg = round(sum(test_list) / len(test_list), 2)

                if avg < close_price and b["side"] != "buy":
                    logger.info("buy")
                    b["side"] = "buy"
                    await send_telegram_msg('buy')

                elif avg > close_price and b["side"] != "sell":
                    logger.info("sell")
                    b["side"] = "sell"
                    await send_telegram_msg('sell')

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
                logger.info(book)

            case {
                "data": dict() as order,
                "type": "message",
                "subject": "stopOrder",
            }:
                symbol = order["symbol"].replace(f"-{base_stable}", "")
                if order["type"] == "cancel":
                    if symbol in book:
                        del book[symbol]["orderId"]

    # get_account_info()

    client = WsToken(
        key=key,
        secret=secret,
        passphrase=passphrase,
        url="https://openapi-v2.kucoin.com",
    )

    # balance = await KucoinWsClient.create(None, client, event, private=True)
    # order = await KucoinWsClient.create(None, client, event, private=True)
    # cancel_order = await KucoinWsClient.create(None, client, event, private=True)
    candle = await KucoinWsClient.create(None, WsToken(), event, private=False)

    # await balance.subscribe("/account/balance")
    await candle.subscribe(f"/market/candles:{currency}-{base_stable}_{time_shift}")
    # await order.subscribe("/spotMarket/tradeOrdersV2")
    # await cancel_order.subscribe("/spotMarket/advancedOrders")

    while True:
        await asyncio.sleep(60)


asyncio.run(main())
