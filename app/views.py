from rest_framework.response import Response  # DRF's HTTPResponse
from rest_framework.decorators import api_view  # DRF improves function view to APIView
from rest_framework import status

from app.services import obtener_almacenes, obtener_skus_disponibles, obtener_productos_almacen, mover_entre_bodegas, consultar_oc
from app.services import consultar_oc, ids_oc, rechazar_oc, recepcionar_oc, mover_entre_almacenes, receipt_url, min_post_factor
from app.subtasks_bonus import update_cart_file, address_to_coordinates, receipt_creation, fabricar_bonus
from app.subtasks_bonus import get_client_ip, get_products_for_sale, add_to_cart_file, sku_with_name
from app.models import Order, Product, RawMaterial

from app.serializers import OrderSerializer
from app.subtasks import get_current_stock
from app.subtasks_defs import get_almacenes_origenes_destino
from app.subviews import check_group_oc_time
from django.shortcuts import render, redirect
from app.subtasks_defs import check_will_produce_order, lots_for_q, get_ingredients
from django.contrib import messages
import json
import requests
import os

accept_amount = 10


@api_view(['GET'])  # only allows GET, else error code 405
def stock_list(request):
    """
    Entrega stock disponible por sku en toda la bodega.
    :return: lista con cada { sku, nombre, total }
    """
    # Hacemos un diccionario sku - nombre producto
    aux_dict = {}
    for p in Product.objects.raw('SELECT sku, name FROM app_product'):
        aux_dict[p.sku] = p.name

    totals = get_current_stock()
    respuesta_final = []
    stock_minimos = {}
    productos = RawMaterial.objects.filter(material_type=1)
    for materia in productos:
        stock_minimos[materia.sku.sku] = materia.stock

    for elem in stock_minimos:
        disponible_venta = max(int(totals[elem] - min_post_factor * stock_minimos[elem]), 0)
        if disponible_venta != 0:
            respuesta_final.append({"sku": elem, "nombre": aux_dict[elem],
                                    "total": min(accept_amount, disponible_venta)})
    return Response(respuesta_final)


@api_view(['POST'])
def create_order(request):
    """
    Permite crear un pedido de otro grupo para nosotros.
    :return: json { sku, cantidad, almacenId, grupoProveedor,
                    aceptado, despachado }
    """
    if 'sku' not in request.data or 'cantidad' not in request.data \
            or 'almacenId' not in request.data or 'oc' not in request.data:
        return Response({"error": "400 (Bad Request): Falta parámetro obligatorio."},
                        status=status.HTTP_400_BAD_REQUEST)

    oc_id = request.data['oc']
    order = consultar_oc(str(oc_id))
    if not order:
        return Response({"error": "400 (Bad Request): ID de oc no corresponde"},
                        status=status.HTTP_400_BAD_REQUEST)
    fecha_entrega = order[0]['fechaEntrega']

    data = {'amount': order[0]['cantidad'], 'sku':order[0]['sku'], 'storeId':request.data['almacenId'], 'client_group':int(request.META['HTTP_GROUP'])}
    accepted_and_dispatched = False  # por default

    if order[0]['proveedor'] != ids_oc[13]:
        return Response({"error": "400 (Bad Request): ID Proveedor no corresponde"},
                        status=status.HTTP_400_BAD_REQUEST)

    if data["sku"] not in ['1001', '1002', '1003', '1004', '1005', '1006', '1007', '1008',
                           '1009', '1010', '1011', '1012', '1013', '1014', '1015', '1016']:
        rechazar_oc(oc_id)
    elif data["amount"] > accept_amount:
        rechazar_oc(oc_id)
    else:
        totals = get_current_stock()
        raw_material = RawMaterial.objects.filter(sku=data['sku']).values()
        if not raw_material:
            return Response({"error": "404 (Not Found): sku no existe."}, status=status.HTTP_404_NOT_FOUND)

        minimum_stock = raw_material[0]['stock']
        if totals[data['sku']] - data['amount'] < minimum_stock * min_post_factor:
            rechazar_oc(oc_id)
        else:
            if check_group_oc_time(fecha_entrega):
                # hay productos y tenemos al menos 10 minutos para despachar

                ids_origen, id_almacen_despacho = get_almacenes_origenes_destino()

                cantidad_despachada = 0
                for almacen in ids_origen:
                    productos = obtener_productos_almacen(almacen, data['sku'])
                    for elem in productos:
                        mover_entre_almacenes(elem['_id'], id_almacen_despacho)
                        response = mover_entre_bodegas(elem['_id'], data["storeId"], oc_id, 1)
                        if response:
                            cantidad_despachada += 1
                        if cantidad_despachada == data['amount']:
                            break
                    if cantidad_despachada == data['amount']:
                        break

                if cantidad_despachada == data['amount']:
                    recepcionar_oc(oc_id)  # aceptamos cuando ya aseguramos despacho completo
                    accepted_and_dispatched = True

            else:
                rechazar_oc(oc_id)

    respuesta = {
        "sku": data["sku"],
        "cantidad": data["amount"],
        "almacenId": data["storeId"],
        "grupoProveedor": 13,
        "aceptado": accepted_and_dispatched,
        "despachado": accepted_and_dispatched
    }

    data['accepted'] = accepted_and_dispatched
    data['dispatched'] = accepted_and_dispatched

    serializer = OrderSerializer(data=data)
    if serializer.is_valid():
        serializer.save()
        return Response(respuesta, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def order_status(request, id):
    if 'status' not in request.data:
        return Response({ "error": "400 (Bad Request): Falta parámetro obligatorio." }, status=status.HTTP_400_BAD_REQUEST)
    respuesta = {"status":request.data["status"]}
    return Response(respuesta, status=status.HTTP_204_NO_CONTENT)


def bonus_home(request):
    productos = get_products_for_sale()
    return render(request, 'app/home.html', {"productos": productos})


def add_to_cart(request):
    productos = get_products_for_sale()
    valores = request.GET.items()
    pedido = {}
    for key, value in valores:
        pedido['sku'] = key
        pedido['cantidad'] = value
        pedido['ip'] = get_client_ip(request)

    messages.success(request, '¡Agregado al carro!')
    add_to_cart_file(pedido['sku'], pedido['cantidad'], pedido['ip'])
    return render(request, 'app/home.html', {'mensaje': True, 'productos': productos})


def update_cart(request):
    valores = request.GET.items()
    pedido = {}
    for key, value in valores:
        pedido['sku'] = key
        pedido['cantidad'] = value
        pedido['ip'] = get_client_ip(request)
    update_cart_file(request, pedido['sku'], pedido['cantidad'], pedido['ip'])

    file_name = str(get_client_ip(request))+".json"

    with open(file_name) as outfile:
        data = json.load(outfile)

    aux = sku_with_name(data)
    return render(request, 'app/cart.html', {'carro': aux[0], 'valor': aux[1]})


def see_cart(request):
    file_name = str(get_client_ip(request))+".json"
    try:
        with open(file_name) as outfile:
            data = json.load(outfile)
        aux = sku_with_name(data)
        return render(request, 'app/cart.html', {'carro': aux[0], 'valor': aux[1]})
    except FileNotFoundError:
        return render(request, 'app/cart.html', {'carro': False})


def confirm_purchase(request):
    respuesta = {}
    valores = request.GET.items()
    for key, value in valores:
        respuesta.update({key: value})
    # Revisar factibilidad del pedido
    file_name = str(get_client_ip(request)) + ".json"
    try:
        products = get_current_stock()
        with open(file_name) as outfile:
            data = json.load(outfile)
        infactibles = []
        for elem in data:
            product_lot = Product.objects.filter(sku=elem).values("production_lot")[0]["production_lot"]
            lots = lots_for_q(data[elem], product_lot)
            ingredients = get_ingredients(elem)
            will_produce = check_will_produce_order(products, lots, ingredients)
            if not will_produce:
                infactibles.append(elem)

        if len(infactibles) == 0:
            return render(request, 'app/purchase.html', {'coordenadas': (-70.6693, -33.4489), 'zoom': 9,
                                                         'valor': respuesta['valor']})
        else:
            productos = get_products_for_sale()
            infactibles_nombre = []
            for sku in infactibles:
                infactibles_nombre.append(productos[sku]['name'])
            return render(request, 'app/invalid_purchase.html', {'infactibles': infactibles_nombre})
            # Aqui debemos retornar una alerta de que no tenemos stock suficiente para sushi con los ids en lista infactibles

    except FileNotFoundError:
        return render(request, 'app/cart.html', {'carro': False})


def get_address(request):
    respuesta = {}
    valores = request.GET.items()
    for key, value in valores:
        respuesta.update({key: value})
    coordenadas = address_to_coordinates(respuesta["calle"], respuesta["numero"])
    return render(request, 'app/purchase.html', {'coordenadas': coordenadas, 'zoom': 16,
                                                 'valor': respuesta['valor']})


def generate_receipt(request):
    respuesta = {}
    valores = request.GET.items()
    for key, value in valores:
        respuesta.update({key: value})
    entregar = receipt_creation(respuesta['nombre'], respuesta['valor'])
    oc = entregar["_id"]
    bruto = entregar["bruto"]
    total = entregar["total"]
    iva = entregar["iva"]
    url_exitosa = "http://tuerca13.ing.puc.cl%2Fboleta%2F{}%2F{}%2F{}%2F{}".format(oc, bruto, total, iva)

    # Avisar que no el pago falló. Se debe codificar como url component
    url_fracaso = "http://tuerca13.ing.puc.cl%2Fpayment_error"
    redireccion = receipt_url + '/web/pagoenlinea?callbackUrl={}'.format(url_exitosa)
    redireccion += "&cancelUrl={}".format(url_fracaso)
    redireccion += "&boletaId={}".format(oc)
    return redirect(redireccion)


def mostrar_boleta(request, oc, bruto, total, iva):
    file_name = str(get_client_ip(request)) + ".json"

    with open(file_name) as outfile:
        data = json.load(outfile)

    fabricar_bonus(data, oc)

    os.remove("../"+file_name)
    return render(request, "app/receipt.html", {'oc': oc, 'bruto': bruto, 'total': total, 'iva': iva})

def payment_error(request):
    return render(request, 'app/payment_error.html')
