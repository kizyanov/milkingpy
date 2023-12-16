from test import assert_data
from db import count_records, sum_records, insert_value_in_db
from loguru import logger

target = 100_000  # In USD
base_take = 1000


def main():
    for i in range(target // base_take):
        current_step = (count_records() + 1) * base_take
        total_amount = sum_records()
        logger.debug(total_amount)
        usd_amount = total_amount * assert_data[i]

        disition = current_step - usd_amount

        if disition > 0:
            # Buy
            logger.success(f"Buy on  \t${disition:.2f} \tby ${assert_data[i]:.3f}")
        else:
            # Sell
            logger.error(f"Sell on \t${disition:.2f} \tby ${assert_data[i]:.3f}")

        insert_value_in_db(disition / assert_data[i])

        logger.debug("================================================================")

    logger.debug(f"Total amount {sum_records()} coins")


main()
