from celery import shared_task
from app.subtasks import get_current_stock, get_groups_stock, review_inventory
from app.subtasks import lots_for_q, get_ingredients, check_time_availability, check_will_produce_order
from app.subtasks import review_order
from app.services import sftp_ocs, consultar_oc


# @shared_task
# def hello():
#     print("Hello there!")

@shared_task
def main():
    # print("hello main")

    # empty_receptions()
    # print("empty_receptions")

    totals = get_current_stock()
    # print("totals")

    groups_stock = get_groups_stock()
    # print("groups_stock")

    review_inventory(totals, groups_stock)
    # print("review_inventory")

    # print("bye main")


@shared_task
def ftp_ocs():
    # print("hello ftp_ocs")

    totals = get_current_stock()
    # print("totals")

    ocs_ids = sftp_ocs()
    # print("ocs_ids")

    for oc_id in ocs_ids:
        oc = consultar_oc(oc_id)[0]
        # print(oc)
        review_order(oc_id, totals, oc["fechaEntrega"], oc["sku"], oc["cantidad"])
    # print("ocs reviewed")

    # print("bye ftp_ocs")
