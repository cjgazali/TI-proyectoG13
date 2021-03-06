from collections import defaultdict
from app.services import obtener_almacenes, obtener_skus_disponibles, mover_entre_almacenes, obtener_productos_almacen
from app.services import min_raws_factor, recepcionar_oc, rechazar_oc, despachar_producto
from app.models import Product, RawMaterial, Assigment, SushiOrder
from app.serializers import MarkSerializer, SushiOrderSerializer
from app.subtasks_defs import lots_for_q, get_ingredients
from app.subtasks_defs import post_to_all, manufacture_raws, try_manufacture
from app.subtasks_defs import check_time_availability, check_will_produce_order, produce_order
from datetime import datetime

"""Funciones que se importan en tasks.py."""


def empty_reception():
    """Vacía recepción hacia bodegas extra."""
    almacenes_extra = []
    almacenes = obtener_almacenes()
    for almacen in almacenes:
        if almacen['recepcion']:
            recepcion = almacen
        elif not almacen["pulmon"] and not almacen["despacho"] and not almacen["cocina"]:
            almacenes_extra.append(almacen)

    if recepcion["usedSpace"] > 0:
        skus = obtener_skus_disponibles(recepcion["_id"])
        for sku in skus:
            productos = obtener_productos_almacen(recepcion["_id"], sku["_id"])
            for producto in productos:
                if almacenes_extra[0]["usedSpace"] < almacenes_extra[0]["totalSpace"]:
                    mover_entre_almacenes(producto["_id"], almacenes_extra[0]["_id"])
                elif almacenes_extra[1]["usedSpace"] < almacenes_extra[1]["totalSpace"]:
                    mover_entre_almacenes(producto["_id"], almacenes_extra[1]["_id"])
                else:
                    print("Alerta, almacenes extra llenos")
                    return

                almacenes_extra = []
                almacenes = obtener_almacenes()
                for almacen in almacenes:
                    if not almacen['recepcion'] and not almacen["pulmon"] and not almacen["despacho"] and not almacen["cocina"]:
                        almacenes_extra.append(almacen)


def empty_pulmon():
    """Vacía pulmon hacia bodegas extra."""
    almacenes_extra = []
    almacenes = obtener_almacenes()
    for almacen in almacenes:
        if almacen['pulmon']:
            pulmon = almacen
        elif not almacen["recepcion"] and not almacen["despacho"] and not almacen["cocina"]:
            almacenes_extra.append(almacen)

    if pulmon["usedSpace"] > 0:
        skus = obtener_skus_disponibles(pulmon["_id"])
        for sku in skus:
            productos = obtener_productos_almacen(pulmon["_id"], sku["_id"])
            for producto in productos:
                if almacenes_extra[0]["usedSpace"] < almacenes_extra[0]["totalSpace"]:
                    mover_entre_almacenes(producto["_id"], almacenes_extra[0]["_id"])
                elif almacenes_extra[1]["usedSpace"] < almacenes_extra[1]["totalSpace"]:
                    mover_entre_almacenes(producto["_id"], almacenes_extra[1]["_id"])
                else:
                    print("Alerta, almacenes extra llenos")
                    return

                almacenes_extra = []
                almacenes = obtener_almacenes()
                for almacen in almacenes:
                    if not almacen['recepcion'] and not almacen["pulmon"] and not almacen["despacho"] and not almacen["cocina"]:
                        almacenes_extra.append(almacen)


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


def review_inventory():
    totals = get_current_stock()

    query = Assigment.objects.filter(group__exact=13)
    skus_fabricables = []
    for dato in query:
        skus_fabricables.append(dato.sku.sku)

    productos = RawMaterial.objects.all()
    for materia in productos:
        desired_stock = min_raws_factor * materia.stock
        if totals[materia.sku.sku] < desired_stock:
            remaining = desired_stock - totals[materia.sku.sku]
            remaining = int((remaining // 2) + 1)
            product_lot = Product.objects.filter(sku=materia.sku.sku).values("production_lot")[0]["production_lot"]
            if materia.material_type == 1:
                if materia.sku.sku in skus_fabricables:
                    manufacture_raws(materia.sku.sku, remaining, product_lot)
            else:
                try_manufacture(totals, materia.sku.sku, remaining, product_lot)


def review_post():
    totals = get_current_stock()

    productos = RawMaterial.objects.filter(material_type=1)
    for materia in productos:
        desired_stock = min_raws_factor * materia.stock
        if totals[materia.sku.sku] < desired_stock:
            remaining = desired_stock - totals[materia.sku.sku]
            # print("{} {} will post_to_all".format(materia.sku.sku, remaining))
            post_to_all(materia.sku.sku, remaining)


def review_order(oc_id, products, date, sku, amount, state):
    """Acepta o rechaza orden de sushi, y manda producir si acepta."""
    # Validar plazo
    ok_time = check_time_availability(date, sku)
    if not ok_time:
        print("review_order: oc rejected: not ok_time")
        # reject
        rechazar_oc(oc_id[0])
        data = {'name': oc_id[1]}
        new = MarkSerializer(data=data)
        if new.is_valid():
            new.save()
        return

    product_lot = Product.objects.filter(sku=sku).values("production_lot")[0]["production_lot"]
    lots = lots_for_q(amount, product_lot)
    ingredients = get_ingredients(sku)
    # Validar ingredientes
    will_produce_order = check_will_produce_order(products, lots, ingredients)
    if will_produce_order:
        if state == "creada":
            print("review_order: will produce")
            # produce
            produced = produce_order(sku, product_lot, lots, ingredients)
            if not produced:
                print("review_order: not produced")
                return
            # accept
            recepcionar_oc(oc_id[0])
            print("review_order: oc accepted")

            data = {'name': oc_id[1]}
            new = MarkSerializer(data=data)
            if new.is_valid():
                new.save()

            # Agregamos registros a SushiOrder
            for i in range(amount):
                aux = datetime.strptime(date, "%Y-%m-%dT%H:%M:%S.%fZ")
                epoch = datetime.utcfromtimestamp(0)
                delta = aux - epoch
                seconds = int(delta.total_seconds())
                data2 = {'oc': oc_id[0], 'sku': sku, 'delivery_date': seconds, 'dispatched': False}
                new2 = SushiOrderSerializer(data=data2)
                if new2.is_valid():
                    new2.save()
        else:
            data = {'name': oc_id[1]}
            new = MarkSerializer(data=data)
            if new.is_valid():
                new.save()
    else:
        print("review_order: not will_produce_order")
        pass


def find_and_dispatch_sushi():
    almacenes = obtener_almacenes()

    sushi_products = {}
    id_almacen_despacho = ""
    for almacen in almacenes:
        if not almacen["despacho"]:
            sku_stock_list = obtener_skus_disponibles(almacen["_id"])
            # print("got skus", skus)
            for sku_stock in sku_stock_list:
                sku = sku_stock["_id"]
                if len(sku) > 4:
                    sushis_here = obtener_productos_almacen(almacen["_id"], sku)
                    # print("got sushis here", sushis_here)
                    if sku in sushi_products:
                        sushi_products[sku] += sushis_here
                    else:
                        sushi_products[sku] = sushis_here
        else:
            id_almacen_despacho = almacen["_id"]

    # print("got all sushi products by sku", sushi_products)

    for sku in sushi_products:

        now = datetime.utcnow()
        epoch = datetime.utcfromtimestamp(0)
        delta_now = now - epoch
        seconds_now = int(delta_now.total_seconds())
        # se considera modelo ordenado por delivery_date creciente, descarta obsoletas
        pendings = SushiOrder.objects.filter(sku__exact=sku, dispatched=False, delivery_date__gt=seconds_now)
        if not pendings:
            continue

        pendings_counter = 0
        for product in sushi_products[sku]:
            pending = pendings[pendings_counter]

            mover_entre_almacenes(product["_id"], id_almacen_despacho)
            response = despachar_producto(product["_id"], pending.oc)
            try:
                if response["despachado"]:
                    print("find_and_dispatch_sushi: sushi despachado")
                    pending.dispatched = True
                    pending.save()
                    pendings_counter += 1
            except KeyError:
                pass
            if pendings_counter == len(pendings):
                print("find_and_dispatch_sushi: oc sushi terminada")
                break
