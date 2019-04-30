from celery import shared_task
from collections import defaultdict
from app.services import obtener_almacenes, obtener_skus_disponibles, mover_entre_almacenes, obtener_productos_almacen, fabricar_sin_pago, min_stock_factor
from app.subtasks import get_current_stock, empty_receptions, get_groups_stock, try_manufacture, review_raw_materials, post_to_all
from app.models import Product


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

    review_raw_materials(totals, groups_stock)
    # print("raws reviewed")

    # products with minimum stock:
    products_set = Product.objects.filter(minimum_stock__gt=0)

    for product in products_set:
        # Masago es el único que el profe pide stock mínimo pero que es materia prima, se considera antes en
        # Revisar materias primas
        if product.sku == '1013':
            continue
        desired_stock = min_stock_factor * product.minimum_stock
        if totals[product.sku] < desired_stock:
            remaining = desired_stock - totals[product.sku]  # lo que me falta para tener lo que quiero
            # print(product.name, remaining)
            remaining = post_to_all(product.sku, remaining, groups_stock)  # descuenta lo que me acepten
            # print(product.name, remaining)
            if remaining > 0:  # trato de fabricar si no me dieron suficiente
                try_manufacture(totals, product.sku, remaining, product.production_lot)
                # print("try_manufacture done")

    # print("hello main end")
