from celery import shared_task
from app.subtasks import get_current_stock, review_inventory, review_post
from app.subtasks import review_order, find_and_dispatch_sushi
from app.models import Mark
from app.services import sftp_ocs, consultar_oc


@shared_task
def renew_inventory():
    # print("hello renew_inventory")

    review_inventory()
    # print("renew_inventory review_inventory")

    # print("bye renew_inventory")


@shared_task
def post_inventory():
    print("hello post_inventory")

    review_post()
    print("post_inventory review_post")

    print("bye post_inventory")


@shared_task
def ftp_ocs():
    # print("hello ftp_ocs")

    totals = get_current_stock()
    # print("ftp_ocs totals")

    lista = list(Mark.objects.values_list('name', flat=True))
    ocs_ids = sftp_ocs(lista)
    # print("ftp_ocs ocs_ids")

    for oc_id in ocs_ids:
        oc = consultar_oc(oc_id[0])[0]
        # print("ftp_ocs", oc)
        review_order(oc_id, totals, oc["fechaEntrega"], oc["sku"], oc["cantidad"], oc["estado"])
    # print("ftp_ocs ocs reviewed")

    # print("bye ftp_ocs")


@shared_task
def dispatch_sushi():
    # print("hello dispatch_sushi")

    find_and_dispatch_sushi()
    # print("dispatch_sushi sushi ocs considered")

    # print("bye dispatch_sushi")
