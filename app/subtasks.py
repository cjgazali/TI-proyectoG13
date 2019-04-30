from collections import defaultdict
from app.services import obtener_almacenes, obtener_skus_disponibles, mover_entre_almacenes, obtener_productos_almacen, get_group_stock, fabricar_sin_pago, post_order, mover_entre_bodegas
from app.models import Ingredient, Product, RawMaterial, Assigment


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
    totals = defaultdict(int)  # sku: total
    get_almacenes = obtener_almacenes()
    for almacen in get_almacenes:
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
            print("fail", n_group)
            group_stock = []
        for product in group_stock:
            if isinstance(product, dict):
                try:
                    totals[product["sku"]] += product["total"]
                except:
                    print("KeyError", n_group)
                    break
        dicts.append(totals)
        print(totals)
    return dicts


def post_to_all(sku, quantity, groups_stock):
    almacenes = obtener_almacenes()
    for almacen in almacenes:
        if almacen['despacho']:
            id_almacen_despacho = almacen["_id"]
    for n_group in range(1,15):
        if n_group == 13:
            continue
        # pido lo que quiero, o lo que tengan, si tienen pero menos
        group_post_quantity = min(groups_stock[n_group - 1][sku], quantity)
        if group_post_quantity > 0:  # si tienen
            try:
                response = post_order(n_group, sku, group_post_quantity, id_almacen_despacho)
            except:
                print("fail", n_group)
                continue
            try:
                if response["aceptado"]:
                    # veo cuánto me falta
                    accepted_amount = response["cantidad"]
                    quantity = max(0, quantity - accepted_amount)
            except:
                print("KeyError", n_group)
                continue
            print("OK", n_group)
    return quantity


def try_manufacture(products, sku, diference, lote_minimo):
    """Intenta producir el producto correspondiente a sku,
     si no, pide materias primas necesarias"""

    # Calculo la cantidad de unidades que me faltan en bodega
    # diference = stock_minimo - products[sku]

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
            print("manufacture")
            manufacture(ingredients, sku, lote_minimo)
            print("manufacture done")
        else:
            print("no ingredients")
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

def move_product_client(sku, cantidad_productos, id_almacen_despacho, id_almacen_destino):
    lista_productos = obtener_productos_almacen(id_almacen_despacho, sku)
    for i in range(cantidad_productos):
        mover_entre_bodegas(lista_productos[i]['_id'], id_almacen_destino)
    return


def review_raw_materials(totals, groups_stock):
    query = Assigment.objects.filter(group__exact=13)
    skus_fabricables = []
    for dato in query:
        skus_fabricables.append(dato.sku.sku)
    materias_primas = RawMaterial.objects.all()
    for materia in materias_primas:
        desired_stock = materia.stock
        if totals[materia.sku.sku] < desired_stock:
            remaining = desired_stock - totals[materia.sku.sku]  # lo que me falta para tener lo que quiero
            print(desired_stock, totals[materia.sku.sku], remaining)
            print(materia.sku.sku, remaining)
            remaining = post_to_all(materia.sku.sku, remaining, groups_stock)  # descuenta lo que me acepten
            print(materia.sku.sku, remaining)
            if remaining > 0 and materia.sku.sku in skus_fabricables:  # trato de fabricar si no me dieron suficiente
                product_lot = Product.objects.filter(sku=materia.sku.sku).values("production_lot")[0]["production_lot"]
                manufacture_raws(materia.sku.sku, remaining, product_lot)

def manufacture_raws(sku, diference, production_lot):
    lots = (diference // production_lot) + 1
    amount = lots * production_lot
    response = fabricar_sin_pago(sku, amount)
    print(response)
    print("manufactured", sku, response["cantidad"])
