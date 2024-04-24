import asyncio
import base64
import hashlib
import hmac
import json
import time
from urllib.parse import urljoin
from uuid import uuid1

import aiohttp
from decouple import config
from kucoin.client import Market, Trade, User, WsToken
from kucoin.ws_client import KucoinWsClient
from loguru import logger

key = config("KEY", cast=str)
secret = config("SECRET", cast=str)
passphrase = config("PASSPHRASE", cast=str)
base_stable = config("BASE_STABLE", cast=str)
currencys = config("CURRENCYS", cast=str)
time_shift = config("TIME_SHIFT", cast=str)

base_uri = "https://api.kucoin.com"

order_book = {}

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

client = WsToken(
    key=key,
    secret=secret,
    passphrase=passphrase,
    url="https://openapi-v2.kucoin.com",
)

headers_base = {
    "KC-API-KEY": key,
    "Content-Type": "application/json",
    "KC-API-KEY-VERSION": "2",
    "User-Agent": "kucoin-python-sdk/2",
}


async def send_telegram_msg(msg: str) :
    """Отправка сообщения в телеграмм."""
    async with (
        aiohttp.ClientSession() as session,
        session.post(
            f"https://api.telegram.org/bot{config('TELEGRAM_BOT_API_KEY', cast=str)}/sendMessage",
            json={
                "chat_id": config("TELEGRAM_BOT_CHAT_ID", cast=str),
                "parse_mode": "HTML",
                "disable_notification": True,
                "text": msg,
            },
        ) as response,
    ):
        logger.info(response)


def get_account_info():
    """Get all assert in account."""

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
                    },
                )

                d = order.get_all_stop_order_details(
                    **{
                        "symbol": f'{asset["currency"]}-{base_stable}',
                    },
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
        },
    )


def encrypted_msg(msg: str) -> str:
    """."""
    return base64.b64encode(
        hmac.new(secret.encode("utf-8"), msg.encode("utf-8"), hashlib.sha256).digest(),
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

    async with (
        aiohttp.ClientSession() as session,
        session.post(
            urljoin(base_uri, method_uri),
            headers=headers,
            data=data_json,
        ) as response,
    ):
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

    async with aiohttp.ClientSession() as session, session.delete(
            urljoin(base_uri, uri_path),
            headers=headers,
        ) as response:
        result = await response.json()


async def change_account_balance(data: dict):
    """Обработка собития изминения баланса."""
    logger.success(data)
    msg = "Change account balance"
    match data["relationEvent"]:
        case "trade.setted":
            await send_telegram_msg(msg)
        case _:
            pass


async def change_candle(data: dict):
    """Обработка изминений свечей."""
    logger.debug(data)


async def change_order(data: dict):
    """Обработка изменений ордеров."""
    logger.debug(data)

    # type=received
    # status=new

    # type=open
    # status=open

    # type=match
    # status=match

    # type=update
    # status=open

    # type=filled
    # status=done

    # type=canceled
    # status=done

    match data["status"]:
        case "new":
            # ордер поступает в систему сопоставления
            pass
        case "open":
            # ордер находится в книге ордеров (maker order)
            pass
        case "match":
            # когда ордер тейкера исполняется с ордерами в стакане
            pass
        case "done":
            # ордер полностью исполнен успешно
            pass

    match data["type"]:
        case "received":
            # Сообщение, отправленное при поступлении заказа в систему сопоставления
            # status=new
            pass
        case "open":
            # ордер находится в книге ордеров (maker order)
            pass
        case "match":
            # сообщение, отправленное при совпадении ордера
            pass
        case "update":
            # Сообщение, отправленное в связи с модификацией ордера
            pass


async def main() -> None:
    """Главная функция приложения."""
    logger.info("Start market to bulge")
    # /api/v1/orders?status=active&type=limit&symbol=BTC-USDT


    async def event(msg:dict) -> None:
        match msg:  # Add Stop Order Event
            case {
                "data": dict() as candle,
                "type": "message",
                "subject": "trade.candles.update",
            }:
                await change_candle(candle)

            case {
                "data": dict() as balance,
                "type": "message",
                "subject": "account.balance",
            }:
                await change_account_balance(balance)

            case {
                "data": dict() as order,
                "type": "message",
                "topic": "/spotMarket/tradeOrdersV2",
            }:
                await change_order(order)

    # get_account_info()

    # balance = await KucoinWsClient.create(None, client, event, private=True)
    # order = await KucoinWsClient.create(None, client, event, private=True)
    candle = await KucoinWsClient.create(None, WsToken(), event, private=False)

    # await balance.subscribe("/account/balance")
    await candle.subscribe(f"/market/candles:{currency}-{base_stable}_{time_shift}")
    # await order.subscribe("/spotMarket/tradeOrdersV2")

    while True:
        await asyncio.sleep(60)


asyncio.run(main())
