import asyncio
import base64
import hashlib
import hmac
import json
import time
from urllib.parse import urljoin
from uuid import uuid1

import aiohttp
from decouple import config, Csv
from kucoin.client import Market, Trade, User, WsToken
from kucoin.ws_client import KucoinWsClient
from loguru import logger

key = config("KEY", cast=str)
secret = config("SECRET", cast=str)
passphrase = config("PASSPHRASE", cast=str)
base_stable = config("BASE_STABLE", cast=str)
currency = config("CURRENCY", cast=Csv(str))
time_shift = config("TIME_SHIFT", cast=str)
base_stake = config("BASE_STAKE", cast=int)

base_uri = "https://api.kucoin.com"

order_book = {}

background_tasks = set()

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


symbol_list = {}

for symbol in market.get_symbol_list_v2():
    if "." in symbol["baseIncrement"] and "." in symbol["priceIncrement"]:
        symbol_list.update(
            {
                symbol["symbol"]: {
                    "baseIncrement": len(symbol["baseIncrement"].split(".")[1]),
                    "sizeIncrement": len(symbol["priceIncrement"].split(".")[1]),
                }
            }
        )

    else:
        symbol_list.update(
            {
                symbol["symbol"]: {
                    "baseIncrement": len(symbol["baseIncrement"]),
                    "sizeIncrement": len(symbol["priceIncrement"]),
                }
            }
        )


async def send_telegram_msg(msg: str):
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
        logger.info(f"Sent teleg:{response.status}")


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


def get_payload2(
    side: str,
    symbol: str,
    price: int,
    size: str,
):
    return json.dumps(
        {
            "clientOid": "".join([each for each in str(uuid1()).split("-")]),
            "side": side,
            "type": "limit",
            "price": str(price),
            "symbol": symbol,
            "size": size,
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


async def make_limit_order(
    side: str,
    price: int,
    symbol: str,
    size: str,
    method: str = "POST",
    method_uri: str = "/api/v1/orders",
):
    """Make limit order by price."""

    now_time = int(time.time()) * 1000

    data_json = get_payload2(
        side=side,
        symbol=symbol,
        price=price,
        size=size,
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
        logger.warning(result)
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

    async with (
        aiohttp.ClientSession() as session,
        session.delete(
            urljoin(base_uri, uri_path),
            headers=headers,
        ) as response,
    ):
        result = await response.json()


async def change_account_balance(data: dict):
    """Обработка собития изминения баланса."""
    if data["currency"] == "USDT":
        holdChange = float(data["holdChange"])
        total = float(data["total"])
        task = asyncio.create_task(
            send_telegram_msg(f"Change account balance: {total:.2f} USDT")
        )

        background_tasks.add(task)

        task.add_done_callback(background_tasks.discard)


async def change_candle(data: dict):
    """Обработка изминений свечей."""

    if data["symbol"] in order_book:
        if order_book[data["symbol"]]["open_price"] != data["candles"][1]:
            # Новая свечка

            baseIncrement = order_book[data["symbol"]]["baseIncrement"]
            market_price = float(data["candles"][1])
            size = f"{base_stake / market_price:.{baseIncrement}f}"

            task = asyncio.create_task(
                make_limit_order(
                    side="buy",
                    price=str(market_price),
                    symbol=data["symbol"],
                    size=size,
                )
            )
            background_tasks.add(task)

            task.add_done_callback(background_tasks.discard)

            order_book[data["symbol"]]["open_price"] = data["candles"][1]
    else:
        order_book[data["symbol"]] = {
            "open_price": data["candles"][1],
            "baseIncrement": symbol_list[data["symbol"]]["baseIncrement"],
            "sizeIncrement": symbol_list[data["symbol"]]["sizeIncrement"],
        }


async def change_order(data: dict):
    """Обработка изменений ордеров."""
    # logger.debug(data)

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

    if data["status"] == "done" and data["type"] == "filled":
        if data["side"] == "buy":
            logger.success(f"Success buy:{data['symbol']}")
            plus_one_percent = float(data["price"]) * 1.01
            sizeIncrement = order_book[data["symbol"]]["sizeIncrement"]

            task = asyncio.create_task(
                make_limit_order(
                    side="sell",
                    price=f"{plus_one_percent:.{sizeIncrement}f}",
                    symbol=data["symbol"],
                    size=data["size"],
                )
            )

            background_tasks.add(task)

            task.add_done_callback(background_tasks.discard)

        elif data["side"] == "sell":
            logger.success(f"Success sell:{data['symbol']}")

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
    # await send_telegram_msg("Start market to bulge")

    async def event(msg: dict) -> None:
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

    balance = await KucoinWsClient.create(None, client, event, private=True)
    order = await KucoinWsClient.create(None, client, event, private=True)
    candle = await KucoinWsClient.create(None, WsToken(), event, private=False)

    tokens = ",".join([f"{sym}-{base_stable}_{time_shift}" for sym in currency])

    await balance.subscribe("/account/balance")
    await candle.subscribe(f"/market/candles:{tokens}")
    await order.subscribe("/spotMarket/tradeOrdersV2")

    while True:
        await asyncio.sleep(60)


asyncio.run(main())
