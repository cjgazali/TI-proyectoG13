from celery import shared_task
from collections import defaultdict
from app.services import obtener_almacenes, obtener_skus_disponibles, mover_entre_almacenes, obtener_productos_almacen, fabricar_sin_pago
from app.subtasks import get_current_stock, empty_receptions, get_groups_stock
from app.models import Product


@shared_task
def hello():
    print("Hello there!")

@shared_task
def main():
    print("hello main")

    empty_receptions()
    print("empty_receptions")

    totals = get_current_stock()
    print(totals)

    groups_stock = get_groups_stock()
    print(groups_stock)

    # products with minimum stock:
    products_set = Product.objects.filter(minimum_stock__gt=0)

    for product in products_set:
        if totals[product.sku] < product.minimum_stock:
            print(product.name)

    print("hello main end")
