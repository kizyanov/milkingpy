from db import select_all_records


def get_all_amount() -> float | int:
    return sum([i[0] for i in select_all_records()])


def get_all_period():
    return len([i for i in select_all_records()])
