from collections import defaultdict
from app.services import obtener_almacenes, obtener_skus_disponibles, mover_entre_almacenes, obtener_productos_almacen, get_group_stock, fabricar_sin_pago
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
        try:
            group_stock = get_group_stock(n_group)
        except:
            group_stock = []
        # print(group_stock)
        for product in group_stock:
            totals[product["sku"]] += product["total"]
        dicts.append(totals)
    # print(dicts)
    return dicts


def try_manufacture(products, sku, stock_minimo, lote_minimo):
    """Intenta producir el producto correspondiente a sku,
     si no, pide materias primas necesarias"""

    # Calculo la cantidad de unidades que me faltan en bodega
    diference = stock_minimo - products[sku]

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


def review_raw_material(totals):
    query = Assigment.object.filter(group__exact=13)
    skus_fabricables = []
    for dato in query:
        skus_fabricables.append(dato.sku.sku)
    materias_primas = RawMaterial.objects.all()
    for materia in materias_primas:
        if totals[materia.sku.sku] < materia.stock:
            if materia.sku.sku in skus_fabricables:
                # Fabrico
                pass
            else:
                # Pido a los demás grupos
                pass

