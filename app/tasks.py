from celery import shared_task
from app.services import obtener_almacenes, obtener_skus_disponibles


@shared_task
def hello():
    print("Hello there!")

@shared_task
def main():
    print("hello main")

    ### get current stock

    totals = {}  # sku: total

    get_almacenes = obtener_almacenes()
    for almacen in get_almacenes:
        stock_response = obtener_skus_disponibles(almacen["_id"])
        for product in stock_response:
            if product["_id"] not in totals:
                totals[product["_id"]] = product["total"]
            else:
                totals[product["_id"]] += product["total"]

    print(totals)

    # get current stock

    print("hello main end")
