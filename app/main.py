from db import insert_value_in_db
from test import assert_data
from logic import get_all_amount, get_all_period

from loguru import logger

target = 100_000 # In USD
base_take = 1000


def main():
    for i in range(target//base_take):
        current_step = (get_all_period() + 1) * base_take
        total_amount = get_all_amount()
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

    logger.debug(f"Total amount {get_all_amount()} coins")
main()
