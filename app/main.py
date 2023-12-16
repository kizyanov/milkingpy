from test import assert_data
from db import count_records, sum_records, insert_value_in_db
from loguru import logger
from decouple import config
import time
from telegram import send_message

TARGET = config("TARGET", cast=int)
BASE_TAKE = config("BASE_TAKE", cast=int)


def main():
    for i in range(TARGET // BASE_TAKE):
        current_step = (count_records() + 1) * BASE_TAKE
        total_amount = sum_records()
        logger.debug(total_amount)
        usd_amount = total_amount * assert_data[i]

        disition = current_step - usd_amount

        if disition > 0:
            # Buy
            logger.debug(f"Buy on  \t${disition:.2f} \tby ${assert_data[i]:.3f}")
            send_message()
        else:
            # Sell
            logger.debug(f"Sell on \t${disition:.2f} \tby ${assert_data[i]:.3f}")
            send_message()

        insert_value_in_db(disition / assert_data[i])

        logger.debug("================================================================")

    logger.debug(f"Total amount {sum_records()} coins")

    time.sleep(1000)


main()
