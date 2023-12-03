from db import insert_value_in_db
from test import assert_data
from logic import get_all_amount, get_all_period

from loguru import logger


base_take = 1000


def main():
    logger.debug(f"{base_take=}")

    # Первый случай покупки
    logger.debug(
        f"Buy on {base_take} USD by {assert_data[0]} price is {base_take / assert_data[0]:.6f}"
    )
    insert_value_in_db(base_take / assert_data[0])
    
    for i in range(1, 100)[:15]:
        logger.debug(f"Run is {i+1}")
        full_steps = get_all_period() * base_take
        total_amount = (
            get_all_amount() * assert_data[i]
        )  # Всего количество актива на сейчас в USD

        logger.debug(f"{full_steps=} {get_all_amount()=:.6f} {total_amount=:.2f}")

        if full_steps < total_amount:
            # Количество ступени меньше чем у нас накопилось, нужно продать излишки
            dif = base_take -  (total_amount - full_steps) # сколько нужно продать излишков
            sell_size = dif / assert_data[i] # сколько это будет в активе
            
            logger.debug(
                f"Buy on {dif:.2f} USD by {assert_data[i]} price is {sell_size:.6f}"
            )
            insert_value_in_db(sell_size)

        elif full_steps > total_amount:
            # Количество ступени больше чем у нас накопилось, нужно докупить недостаток
            dif = base_take + full_steps - total_amount # сколько нужно докупть до целей
            buy_size = dif / assert_data[i] # сколько это будет в активе
            logger.debug(
                f"Buy on {dif:.2f} USD by {assert_data[i]} price is {buy_size:.6f}"
            )
            insert_value_in_db(buy_size)

        logger.debug("================================================================")


main()
