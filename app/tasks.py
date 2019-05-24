from celery import shared_task
from app.subtasks import get_current_stock, get_groups_stock
from app.subtasks import review_inventory


# @shared_task
# def hello():
#     print("Hello there!")

@shared_task
def main():
    # print("hello main")

    # empty_receptions()
    # print("empty_receptions")

    totals = get_current_stock()
    # print(totals)

    groups_stock = get_groups_stock()
    # print(groups_stock)

    review_inventory(totals, groups_stock)

    # print("hello main end")
