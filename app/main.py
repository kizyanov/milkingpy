from test import assert_data
from db import count_records, sum_records, insert_value_in_db
from loguru import logger
from decouple import config
import time
from telegram import send_message

TARGET = config("TARGET", cast=int)
BASE_TAKE = config("BASE_TAKE", cast=int)
TIME_SHIFT = config("TIME_SHIFT", cast=str)
TRADE_SYMBOL = config("TRADE_SYMBOL", cast=str)

def get_current_amount_in_usd():
    pass


def trade():
    current_step = (count_records() + 1) * BASE_TAKE
    total_amount = sum_records()
    logger.debug(total_amount)
    usd_amount = total_amount * get_current_amount_in_usd()

    disition = current_step - usd_amount

    if disition > 0:
        # Buy
        logger.debug(f"Buy on  \t${disition:.2f} \tby ${get_current_amount_in_usd():.3f}")
        # send_message()
    else:
        # Sell
        logger.debug(f"Sell on \t${disition:.2f} \tby ${get_current_amount_in_usd():.3f}")
        # send_message()

    insert_value_in_db(disition / get_current_amount_in_usd())

    logger.debug("================================================================")


def main():
    for i in range(TARGET // BASE_TAKE):
        trade()

    logger.debug(f"Total amount {sum_records()} coins")

    time.sleep(1000)

main()
