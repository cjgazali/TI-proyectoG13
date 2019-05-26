from celery import shared_task
from app.subtasks import get_current_stock, get_groups_stock, review_inventory, check_time_availability
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

    ocs_ids = sftp_ocs()
    # print("ocs_ids")

    for oc_id in ocs_ids:
        oc = consultar_oc(oc_id)[0]
        # print(oc)
        # Validar plazo
        ok_time = check_time_availability(oc["fechaEntrega"], oc["sku"])
        if not ok_time:
            continue
        # Validar ingredientes
        ## Mandar a fabricar sushi
    # print("ocs considered")

    # print("bye ftp_ocs")
