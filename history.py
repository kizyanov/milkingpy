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

    async with (
        aiohttp.ClientSession() as session,
        session.delete(
            urljoin(base_uri, uri_path),
            headers=headers,
        ) as response,
    ):
        result = await response.json()
