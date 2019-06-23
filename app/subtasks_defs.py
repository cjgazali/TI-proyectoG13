import requests
from app.services import obtener_almacenes, mover_entre_almacenes, obtener_productos_almacen, fabricar_sin_pago
from app.services import get_group_stock, post_order, crear_oc, ids_oc
from app.models import Ingredient, Product
from datetime import datetime, timedelta

"""funciones que se importan al menos en subtasks.py"""


def lots_for_q(amount, min_lot):
    """Calcula lotes para una cantidad con lote mínimo de algún producto"""
    if amount % min_lot == 0:
        return int(amount / min_lot)
    else:
        return (amount // min_lot) + 1


def get_ingredients(sku):
    """Obtiene ingredientes para un producto con su cantidad para lote."""
    ingredients = {}
    query = Ingredient.objects.filter(product_sku__exact=sku)
    for elem in query:
        ingredients[elem.ingredient_sku.sku] = elem.units_quantity
    return ingredients


def get_almacenes_origenes_destino(to_kitchen=False):
    """Entrega conjunto de almacenes de origen (pulmón, recepción, extras)
    y un almacén de destino (despacho o cocina)"""
    id_destino = ""
    ids_origen = []
    almacenes = obtener_almacenes()
    if not to_kitchen:
        destiny = 'despacho'
        ignore = 'cocina'
        # mandaremos a despacho lo disponible menos en cocina
        # en cocina solo hay productos para cocinar sushi o sushi para despachar
    else:
        destiny = 'cocina'
        ignore = 'despacho'
        # mandaremos a cocina lo disponible menos en despacho
        # en despacho solo hay productos para fabricar o productos para despachar
    for almacen in almacenes:
        if almacen[destiny]:
            id_destino = almacen["_id"]
        elif not almacen[ignore]:
            ids_origen.append(almacen["_id"])
    return ids_origen, id_destino


def move_product_destiny(lista_almacenes, almacen_destino, cantidad, sku):
    """for produce:
    Esta función mueve una cantidad del producto con sku desde una lista
    de almacenes a almacen de destino"""
    contador = 0
    for almacen in lista_almacenes:
        lista_ingredientes = obtener_productos_almacen(almacen, sku)
        for elemento in lista_ingredientes:
            response = mover_entre_almacenes(elemento['_id'], almacen_destino)
            if response:
                contador += 1
            if contador == cantidad:
                return


def produce(sku, lot_quantity, ingredients, ids_origen, id_destino):
    """Prepara ingredientes y manda producir un lote de un producto."""
    # Debemos mover los ingredientes a almacén correspondiente
    for ingredient in ingredients.keys():
        move_product_destiny(ids_origen, id_destino, ingredients[ingredient], ingredient)
    # Mandamos a fabricar
    response = fabricar_sin_pago(sku, lot_quantity)
    if response:
        return True
    return False


# START defs for review_post
def group_sku_stock(group, sku):
    stock = 2

    try:
        group_stock = get_group_stock(group)
        if not isinstance(group_stock, list):
            group_stock = []
    except requests.exceptions.Timeout:
        # print(str(group) + " GET timeout ****")
        group_stock = []
        stock = 0
    except:
        # print(str(group) + " failed to GET")
        group_stock = []
        stock = 0

    for product in group_stock:
        if isinstance(product, dict):
            try:
                if product["sku"] == sku:
                    stock = product["total"]
                    break
            except:
                # print(str(group) + " bad response from GET")
                break
        else:
            break
    return stock


def post_to_all(sku, quantity):
    """Hace post a todos por una cantidad objetivo."""
    id_almacen_recepcion = ""
    almacenes = obtener_almacenes()
    for almacen in almacenes:
        if almacen['recepcion']:
            id_almacen_recepcion = almacen["_id"]

    for n_group in range(1, 15):
        if n_group == 13:
            continue

        available = group_sku_stock(n_group, sku)
        # print("{} {} {} to POST".format(n_group, sku, available))
        # Pido el mínimo entre lo que quiero y lo que el grupo tenga
        group_post_quantity = min(available, quantity)
        if group_post_quantity > 0:  # si tienen
            # print(str(n_group) + " will post -------------------")
            now = datetime.utcnow() - timedelta(hours=4)
            now += timedelta(hours=24)
            fecha = now.timestamp() * 1000
            url = 'http://tuerca13.ing.puc.cl/orders/{_id}/notification'
            try:
                response = crear_oc(ids_oc[13], ids_oc[n_group], sku, fecha, quantity, 1, 'b2b', url)
                id_oc = response['_id']
            except:
                # print(str(n_group) + " failed to crear_oc")
                continue

            try:
                response = post_order(n_group, sku, group_post_quantity, id_almacen_recepcion, id_oc)
            except requests.exceptions.Timeout:
                # print(str(n_group) + " POST timeout ****")
                continue
            except:
                # print(str(n_group) + " failed to POST")
                continue

            try:
                if response["aceptado"]:
                    # Veo cuánto me falta
                    accepted_amount = response["cantidad"]
                    # print("{} {} {} accepted -------------------".format(n_group, sku, accepted_amount))
                    quantity = max(0, quantity - accepted_amount)
                    if quantity == 0:
                        break
                else:
                    # print(str(n_group) + " not accepted -------------------")
                    pass
            except:
                # print(str(n_group) + " bad response from POST -------------------")
                continue
        else:
            # print(str(n_group) + " will NOT post")
            pass
# END defs for review_post


# START defs for review_inventory
def manufacture_raws(sku, diference, production_lot):
    """for review_inventory"""
    lots = lots_for_q(diference, production_lot)
    amount = int(lots * production_lot)
    fabricar_sin_pago(sku, amount)


def best_attempt_production(products, sku, min_lot, lots, ingredients):
    """Manda a fabricar lotes de producto, si hay ingredientes suficientes para cada lote.
    Sirve para abastecerse de productos tipo 2."""
    ids_origen, id_destino = get_almacenes_origenes_destino()
    for i in range(0, int(lots)):
        producir = True
        for ingredient in ingredients.keys():
            if products[ingredient] < ingredients[ingredient]:
                producir = False
                break

        if producir:
            produce(sku, min_lot, ingredients, ids_origen, id_destino)
        else:
            break


def try_manufacture(products, sku, diference, lote_minimo):
    """Intenta producir el producto correspondiente a sku"""

    # Calculo la cantidad de lotes que necesito
    lots = lots_for_q(diference, lote_minimo)

    ingredients = get_ingredients(sku)

    best_attempt_production(products, sku, lote_minimo, lots, ingredients)
# END defs for review_inventory


# START defs for review_order
def check_time_availability(date, sku):
    """revisa si es que hay tiempo suficiente para
    fabricar el producto solicitado"""

    now = datetime.utcnow()  # - timedelta(hours=4) servidor del profe también tiene desfase de 4 hrs
    production_mins = Product.objects.filter(sku=sku).values()[0]['expected_production_time']
    production_delta = timedelta(minutes=production_mins)
    extra = timedelta(minutes=10)  # margen arbitrario
    date = datetime.strptime(date, "%Y-%m-%dT%H:%M:%S.%fZ")

    if now + production_delta + extra < date:
        return True
    else:
        return False


def check_will_produce_order(products, lots, ingredients):
    """Decide si fabricar lotes de producto, si hay ingredientes para todos los lotes.
    Sirve para decidir si aceptar orden de sushi."""
    for ingredient in ingredients.keys():
        if products[ingredient] < ingredients[ingredient] * lots:
            return False
    return True


def produce_order(sku, min_lot, lots, ingredients):
    """Produce orden completa de sushi, cuando ya se decidió con check_will_produce_order.
    Produce de a lotes para no saturar cocina."""
    ids_origen, id_destino = get_almacenes_origenes_destino(True)  # True = to_kitchen
    for i in range(0, lots):
        produced = produce(sku, min_lot, ingredients, ids_origen, id_destino)
        if not produced:
            return False
    return True
# END defs for review_order
