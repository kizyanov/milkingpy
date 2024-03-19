from test import assert_data
from db import count_records, sum_records, insert_value_in_db
from loguru import logger
from decouple import config
import time
from telegram import send_message


def main():
   
    logger.debug(f"Total amount {sum_records()} coins")

    time.sleep(1000)

main()
