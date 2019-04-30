from celery import shared_task
from collections import defaultdict
from app.services import obtener_almacenes, obtener_skus_disponibles, mover_entre_almacenes, obtener_productos_almacen, fabricar_sin_pago
from app.subtasks import get_current_stock, empty_receptions, get_groups_stock, try_manufacture, review_raw_materials
from app.models import Product


@shared_task
def hello():
    print("Hello there!")

@shared_task
def main():
    print("hello main")

    # empty_receptions()
    # print("empty_receptions")

    totals = get_current_stock()
    print(totals)

    groups_stock = get_groups_stock()
    print(groups_stock)

    # review_raw_materials(totals)

    # products with minimum stock:
    products_set = Product.objects.filter(minimum_stock__gt=0)

    for product in products_set:
        desired_stock = product.minimum_stock
        if totals[product.sku] < desired_stock:
            # Masago es el único que el profe pide stock mínimo pero que es materia prima, se considera antes en
            # Revisar materias primas
            if product.sku != '1013':
                try_manufacture(totals, product.sku, desired_stock, product.production_lot)
                print(product.name)

    print("hello main end")
