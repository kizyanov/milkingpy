import asyncio
import base64
import hashlib
import hmac
import json
import time
from urllib.parse import urljoin
from uuid import uuid1
from decimal import Decimal, ROUND_DOWN
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
base_stake = Decimal(config("BASE_STAKE", cast=int))
base_keep = Decimal(config("BASE_KEEP", cast=int))

base_uri = "https://api.kucoin.com"

order_book = {}

account_available = {"available": "0"}

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

telegram_url = f"https://api.telegram.org/bot{config('TELEGRAM_BOT_API_KEY', cast=str)}/sendMessage"

queue = asyncio.Queue()

for symbol in market.get_symbol_list_v2():
    if symbol["baseCurrency"] in currency and symbol["quoteCurrency"] == base_stable:
        order_book[symbol["symbol"]] = {
            "baseIncrement": Decimal(symbol["baseIncrement"]),
            "priceIncrement": Decimal(symbol["priceIncrement"]),
            "available": Decimal("0"),
        }


for tick in order_book:
    candle = market.get_kline(symbol=tick, kline_type=time_shift)
    order_book[tick].update({"open_price": Decimal(candle[0][1])})

for short_symbol in user.get_account_list(account_type="margin"):
    symbol = f"{short_symbol['currency']}-USDT"
    if symbol in order_book:
        order_book[symbol]["available"] = Decimal(short_symbol["available"])

for s in order_book:
    logger.debug(f"{s}:{order_book[s]}")


async def send_telegram_msg():
    """Отправка сообщения в телеграмм."""
    while True:
        msg = await queue.get()
        for chat_id in config("TELEGRAM_BOT_CHAT_ID", cast=Csv(str)):
            async with (
                aiohttp.ClientSession() as session,
                session.post(
                    telegram_url,
                    json={
                        "chat_id": chat_id,
                        "parse_mode": "HTML",
                        "disable_notification": True,
                        "text": msg,
                    },
                ),
            ):
                pass
        await asyncio.sleep(1)
        queue.task_done()


def get_payload(
    side: str,
    symbol: str,
    price: int,
    size: str,
    timeInForce: str,
    cancelAfter: int,
):
    return json.dumps(
        {
            "clientOid": "".join([each for each in str(uuid1()).split("-")]),
            "side": side,
            "type": "limit",
            "price": str(price),
            "symbol": symbol,
            "size": size,
            "timeInForce": timeInForce,
            "cancelAfter": cancelAfter,
        },
    )


def encrypted_msg(msg: str) -> str:
    """Шифрование сообщения для биржи."""
    return base64.b64encode(
        hmac.new(secret.encode("utf-8"), msg.encode("utf-8"), hashlib.sha256).digest(),
    ).decode()


async def make_limit_order(
    side: str,
    price: int,
    symbol: str,
    size: str,
    timeInForce: str = "GTC",
    cancelAfter: int = 0,
    method: str = "POST",
    method_uri: str = "/api/v1/orders",
):
    """Make limit order by price."""

    now_time = int(time.time()) * 1000

    data_json = get_payload(
        side=side,
        symbol=symbol,
        price=price,
        size=size,
        timeInForce=timeInForce,
        cancelAfter=cancelAfter,
    )

    logger.debug(data_json)

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
        res = await response.json()
        logger.debug(res)


async def change_account_balance(data: dict):
    """Обработка собития изминения баланса."""
    logger.debug(data)

    if (
        data["relationEvent"]
        == "margin.hold"  # Все действия с активом на маржинальном аккаунте
        and data["currency"] + "-USDT" in order_book
    ):
        order_book[data["relationContext"]["symbol"]]["available"] = Decimal(
            data["available"]
        )
        await queue.put(
            f"Change account:{data['relationContext']['symbol']} {data['available']}"
        )
        logger.info(
            f'{data["relationContext"]["symbol"]}:{order_book[data["relationContext"]["symbol"]]}'
        )


async def change_candle(data: dict):
    """Обработка изминений свечей."""

    new_open_price = Decimal(data["candles"][1])

    if order_book[data["symbol"]]["open_price"] != new_open_price:
        logger.info(data)
        balance = new_open_price * order_book[data["symbol"]]["available"]
        if balance != Decimal("0"):
            logger.info(balance)
            await queue.put(
                f"Balance:{data['symbol']} ({balance:.2f} USDT) {base_keep} need sell/buy:{base_keep-balance:.2f}"
            )

        # Новая свечка
        # получить количество токенов за base_stake USDT
        # tokens_count = base_stake / Decimal(data["candles"][1])

        # open_price = float(order_book[data["symbol"]]["open_price"])
        # close_price = float(data["candles"][1])

        # if open_price > close_price:
        #     result = "buy"
        # else:
        #     result = "sell"

        # logger.debug(f"Change price:{result=} {open_price=} {close_price=}")

        # await queue.put(f'{data["symbol"]} need {result}')

        # task = asyncio.create_task(
        #     make_limit_order(
        #         side="buy",
        #         price=data["candles"][1],
        #         symbol=data["symbol"],
        #         size=str(
        #             tokens_count.quantize(
        #                 order_book[data["symbol"]]["baseIncrement"],
        #                 ROUND_DOWN,
        #             )
        #         ),  # округление
        #         timeInForce="GTT",
        #         cancelAfter=86400,  # ровно сутки
        #     )
        # )
        # background_tasks.add(task)

        # task.add_done_callback(background_tasks.discard)

        order_book[data["symbol"]]["open_price"] = Decimal(data["candles"][1])


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
        logger.info(data)

        # if data["side"] == "buy":
        #     # Поставить лимитку на продажу вверху, когда купили актив
        #     logger.success(f"Success buy:{data['symbol']}")

        # увеличить актив на 1 процент
        # plus_one_percent = Decimal(data["price"]) * Decimal("1.01")

        # task = asyncio.create_task(
        #     make_limit_order(
        #         side="sell",
        #         price=str(
        #             plus_one_percent.quantize(
        #                 order_book[data["symbol"]]["priceIncrement"],
        #                 ROUND_DOWN,
        #             )
        #         ),  # округлить цену,
        #         symbol=data["symbol"],
        #         size=data["size"],
        #     )
        # )

        # background_tasks.add(task)

        # task.add_done_callback(background_tasks.discard)

        # elif data["side"] == "sell":
        #     # Поставить лимитку на покупку внизу, когда продали актив
        #     logger.success(f"Success sell:{data['symbol']}")

        # получить количество токенов за base_stake USDT
        # tokens_count = base_stake / Decimal(
        #     order_book[data["symbol"]]["open_price"]
        # )

        # task = asyncio.create_task(
        #     make_limit_order(
        #         side="buy",
        #         price=order_book[data["symbol"]]["open_price"],
        #         symbol=data["symbol"],
        #         size=str(
        #             tokens_count.quantize(
        #                 order_book[data["symbol"]]["baseIncrement"],
        #                 ROUND_DOWN,
        #             )
        #         ),  # округление
        #         timeInForce="GTT",
        #         cancelAfter=86400,  # ровно сутки
        #     )
        # )

        # background_tasks.add(task)

        # task.add_done_callback(background_tasks.discard)

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

    ws_private = await KucoinWsClient.create(None, client, event, private=True)
    ws_public = await KucoinWsClient.create(None, WsToken(), event, private=False)

    tokens = ",".join([f"{sym}-{base_stable}_{time_shift}" for sym in currency])

    await ws_private.subscribe("/account/balance")
    await ws_public.subscribe(f"/market/candles:{tokens}")
    # await ws_private.subscribe("/spotMarket/tradeOrdersV2")

    await send_telegram_msg()


asyncio.run(main())


# 200
# 21.521
# 20.8
# init
# 242.321
# 252.55
########
# 494.871
# plus 1030.92
########
# 1525.79 # 06/05/2024
# plus 204.7
########
# 1730.49  09/05/2024
# plus 308.73
########
# 2039.22 10/05/2024
