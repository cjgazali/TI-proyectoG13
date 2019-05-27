from collections import defaultdict
from app.services import obtener_almacenes, obtener_skus_disponibles, mover_entre_almacenes, obtener_productos_almacen, get_group_stock, fabricar_sin_pago, post_order, mover_entre_bodegas, min_raws_factor
from app.models import Ingredient, Product, RawMaterial, Assigment
from datetime import datetime, timedelta


def empty_receptions():
    """Vacía recepción y pulmón hacia bodegas extra."""
    almacenes_extra = []
    almacenes = obtener_almacenes()
    for almacen in almacenes:
         if almacen['pulmon'] == True and almacen["usedSpace"] > 0:
             #print("Se cumple la condición")
             pulmon = almacen

             for almacen_extra in almacenes:
                 if almacen_extra["pulmon"] == False and almacen_extra["recepcion"] == False and almacen_extra["despacho"] == False and almacen_extra["cocina"] == False:
                     almacenes_extra.append(almacen_extra)

             skus = obtener_skus_disponibles(pulmon["_id"])
             for sku in skus:
                 productos = obtener_productos_almacen(pulmon["_id"], sku["_id"])
                 for producto in productos:
                     if almacenes_extra[0]["usedSpace"] < almacenes_extra[0]["totalSpace"]:
                         mover_entre_almacenes(producto["_id"], almacenes_extra[0]["_id"])
                     else:
                         if almacenes_extra[1]["usedSpace"] < almacenes_extra[1]["totalSpace"]:
                             mover_entre_almacenes(producto["_id"], almacenes_extra[1]["_id"])


def get_current_stock():
    """Entrega diccionario con default 0 con { sku: total en bodega }."""
    # No considera productos de almacen de despacho ni cocina
    totals = defaultdict(int)  # sku: total
    get_almacenes = obtener_almacenes()
    for almacen in get_almacenes:
        if not (almacen["despacho"] or almacen['cocina']):
            stock_response = obtener_skus_disponibles(almacen["_id"])
            for product in stock_response:
                totals[product["_id"]] += product["total"]
    return totals


def get_groups_stock():
    """Entrega lista de diccionarios con default 0,
    con { sku: total en bodega de otro grupo }"""
    dicts = []
    for n_group in range(1, 15):
        totals = defaultdict(int)  # sku: total
        if n_group == 13:  # diccionario vacío para nosotros
            dicts.append(totals)
            continue
        try:
            group_stock = get_group_stock(n_group)
        except:
            # print("fail", n_group)
            group_stock = []
        for product in group_stock:
            if isinstance(product, dict):
                try:
                    totals[product["sku"]] += product["total"]
                except:
                    # print("KeyError", n_group)
                    break
        dicts.append(totals)
        # print(totals)
    return dicts


def post_to_all(sku, quantity, groups_stock):
    almacenes = obtener_almacenes()
    for almacen in almacenes:
        if almacen['recepcion']:
            id_almacen_recepcion = almacen["_id"]
    for n_group in range(1,15):
        if n_group != 13:

            # Pido el mínimo entre lo que quiero y lo que el grupo tenga
            group_post_quantity = min(groups_stock[n_group - 1][sku], quantity)
            if group_post_quantity > 0:  # si tienen
                try:
                    response = post_order(n_group, sku, group_post_quantity, id_almacen_recepcion)
                except:
                    continue
                try:
                    if response["aceptado"]:
                        # Veo cuánto me falta
                        accepted_amount = response["cantidad"]
                        quantity = max(0, quantity - accepted_amount)
                        if quantity == 0:
                            break
                except:
                    continue
    return quantity


def post_to_all_test(sku, quantity):
    """post_to_all para testear APIs desde shell"""
    almacenes = obtener_almacenes()
    id_almacen_recepcion = ''
    for almacen in almacenes:
        if almacen['recepcion']:
            id_almacen_recepcion = almacen["_id"]
    for n_group in range(1,15):
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


def review_inventory(totals, groups_stock):
    # Primero, vemos que skus podemos fabricar
    query = Assigment.objects.filter(group__exact=13)
    skus_fabricables = []
    for dato in query:
        skus_fabricables.append(dato.sku.sku)

    productos = RawMaterial.objects.all()

    for materia in productos:
        desired_stock = min_raws_factor * materia.stock
        if totals[materia.sku.sku] < desired_stock:
            # Calculo cuanto me falta para obtener lo que quiero
            remaining = desired_stock - totals[materia.sku.sku]  # lo que me falta para tener lo que quiero

            # Intento pedir a los grupos y actualizo la cantidad faltante
            remaining = post_to_all(materia.sku.sku, remaining, groups_stock)

            # Trato de fabricar si no me dieron suficiente
            if remaining > 0 and materia.sku.sku in skus_fabricables:
                product_lot = Product.objects.filter(sku=materia.sku.sku).values("production_lot")[0]["production_lot"]
                if materia.material_type == 1:
                    manufacture_raws(materia.sku.sku, remaining, product_lot)
                else:
                    try_manufacture(totals, materia.sku, remaining, product_lot)


def try_manufacture(products, sku, diference, lote_minimo):
    """Intenta producir el producto correspondiente a sku"""

    # Calculo la cantidad de lotes que necesito
    lots = (diference // lote_minimo) + 1

    ingredients = {}
    query = Ingredient.objects.filter(product_sku__exact=sku)
    for elem in query:
        ingredients[elem.ingredient_sku.sku] = elem.units_quantity

    for i in range(0, lots):
        producir = True
        for ingredient in ingredients.keys():
            if products[ingredient] < ingredients[ingredient]:
                producir = False

        if producir:
            manufacture(ingredients, sku, lote_minimo)
        else:
            break


def manufacture(ingredients, sku, cantidad):
    """Produce un lote del producto sku"""
    # Obtenemos el id del almacén de despacho
    # Obtenemos los demás ids de los almacenes de la bodega
    id_almacen_despacho = ""
    ids_origen = []
    almacenes = obtener_almacenes()
    for almacen in almacenes:
        if almacen['despacho']:
            id_almacen_despacho = almacen["_id"]
        else:
            ids_origen.append(almacen["_id"])

    # Debemos mover los ingredientes a despacho
    for ingredient in ingredients.keys():
        move_product_dispatch(ids_origen, id_almacen_despacho, ingredients[ingredient], ingredient)

    # Ahora podemos fabricar un lote
    fabricar_sin_pago(sku, cantidad)


def move_product_dispatch(lista_almacenes, almacen_destino, cantidad, sku):
    """Esta función mueve una cantidad del producto con sku desde una lista
    de almacenes a almacen de destino"""
    contador = 0
    while contador != cantidad and len(lista_almacenes) != 0:
        id_actual = lista_almacenes.pop()
        lista_ingredientes = obtener_productos_almacen(id_actual, sku)
        for elemento in lista_ingredientes:
            mover_entre_almacenes(elemento['_id'], almacen_destino)
            contador += 1
            if contador == cantidad:
                return
    return


def move_product_client(sku, cantidad_productos, id_almacen_despacho, id_almacen_destino, oc, precio):
    lista_productos = obtener_productos_almacen(id_almacen_despacho, sku)
    print(lista_productos)
    for i in range(cantidad_productos):
        print(lista_productos[i]['_id'], id_almacen_destino, oc, precio)
        mover_entre_bodegas(lista_productos[i]['_id'], id_almacen_destino, oc, precio)
    return


def review_raw_materials(totals, groups_stock):
    """ESTA FUNCION ESTA OBSOLETA"""
    query = Assigment.objects.filter(group__exact=13)
    skus_fabricables = []
    for dato in query:
        skus_fabricables.append(dato.sku.sku)
    materias_primas = RawMaterial.objects.all()
    for materia in materias_primas:
        desired_stock = min_raws_factor * materia.stock
        if totals[materia.sku.sku] < desired_stock:
            remaining = desired_stock - totals[materia.sku.sku]  # lo que me falta para tener lo que quiero
            # print(desired_stock, totals[materia.sku.sku], remaining)
            # print(materia.sku.sku, remaining)
            remaining = post_to_all(materia.sku.sku, remaining, groups_stock)  # descuenta lo que me acepten
            # print(materia.sku.sku, remaining)
            if remaining > 0 and materia.sku.sku in skus_fabricables:  # trato de fabricar si no me dieron suficiente
                product_lot = Product.objects.filter(sku=materia.sku.sku).values("production_lot")[0]["production_lot"]
                manufacture_raws(materia.sku.sku, remaining, product_lot)


def manufacture_raws(sku, diference, production_lot):
    lots = (diference // production_lot) + 1
    amount = lots * production_lot
    fabricar_sin_pago(sku, amount)


def check_time_availability(date, sku):
    """revisa si es que hay tiempo suficiente para
    fabricar el producto solicitado"""

    now = datetime.utcnow() - timedelta(hours=4)
    production_mins = Product.objects.filter(sku=sku).values()[0]['expected_production_time']
    production_delta = timedelta(minutes=production_mins)
    extra = timedelta(minutes=15)  # margen arbitrario
    date = datetime.strptime(date, "%Y-%m-%dT%H:%M:%S.%fZ")

    if now + production_delta + extra < date:
        return True
    else:
        return False
