from collections import defaultdict
from app.services import obtener_almacenes, obtener_skus_disponibles
from app.services import post_order

"""funciones que no se usan pero sirven para probar cosas"""


def get_complete_current_stock():
    """Para debugear, muestra todo lo que se tiene en cualquier parte."""
    totals = defaultdict(int)  # sku: total
    get_almacenes = obtener_almacenes()
    for almacen in get_almacenes:
        stock_response = obtener_skus_disponibles(almacen["_id"])
        for product in stock_response:
            totals[product["_id"]] += product["total"]
    return totals


def post_to_all_test(sku, quantity):
    """post_to_all para testear APIs desde shell"""
    almacenes = obtener_almacenes()
    id_almacen_recepcion = ''
    for almacen in almacenes:
        if almacen['recepcion']:
            id_almacen_recepcion = almacen["_id"]
    for n_group in range(1, 15):
        if n_group == 13:
            continue
        try:
            response = post_order(n_group, sku, quantity, id_almacen_recepcion)
        except:
            print("fail", n_group)
            continue
        try:
            if response["aceptado"]:
                print("OK", n_group, response["cantidad"])
        except:
            print("KeyError", n_group)
            continue
    return quantity
