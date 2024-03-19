import asyncio
from loguru import logger
from kucoin.ws_client import KucoinWsClient
from kucoin.client import WsToken

symbol_status = {}

TIME_SCALP = "_1min"

INTEREST_TICKET = [
    "IMX-USDT",
    "WLD-USDT",
    "TON-USDT",
    "SEI-USDT",
    "SUI-USDT",
    "OP-USDT",
    "ARB-USDT",
    "ICP-USDT",
    "APT-USDT",
]


async def main():
    async def deal_msg(msg):
        match msg:
            case {
                "data": dict() as candle,
                "type": "message",
                "subject": "trade.candles.update",
            }:
                logger.debug(msg)
                logger.debug(candle)

    symbols = ",".join([ticket + TIME_SCALP for ticket in INTEREST_TICKET])

    ws_client = await KucoinWsClient.create(None, WsToken(), deal_msg, private=False)

    await ws_client.subscribe(f"/market/candles:{symbols}")

    while True:
        await asyncio.sleep(0)


asyncio.run(main())
