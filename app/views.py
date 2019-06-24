# from django.shortcuts import render
# from rest_framework import status  # generate status codes
from rest_framework.response import Response  # DRF's HTTPResponse
from rest_framework.decorators import api_view  # DRF improves function view to APIView
from rest_framework import status
from app.services import obtener_almacenes, obtener_skus_disponibles, obtener_productos_almacen, mover_entre_bodegas, consultar_oc
from app.services import consultar_oc, ids_oc, rechazar_oc, recepcionar_oc, mover_entre_almacenes
from app.services import get_client_ip, get_products_for_sale, add_to_cart_file, sku_to_name
from app.models import Order, Product, RawMaterial
from app.serializers import OrderSerializer
from app.subtasks import get_current_stock
from app.subtasks_defs import get_almacenes_origenes_destino
from app.subviews import check_group_oc_time
from django.shortcuts import render
from django.contrib import messages
import json

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
        disponible_venta = max(totals[elem] - stock_minimos[elem], 0)
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
    # precio = order[0]['precioUnitario']

    data = {'amount': order[0]['cantidad'], 'sku':order[0]['sku'], 'storeId':request.data['almacenId'], 'client_group':int(request.META['HTTP_GROUP'])}
    accepted_and_dispatched = False  # por default

    # revisa si el grupo proveedor efectivamente somos nosotros
    if order[0]['proveedor'] != ids_oc[13]:
        return Response({"error": "400 (Bad Request): ID Proveedor no corresponde"},
                        status=status.HTTP_400_BAD_REQUEST)

    # si el largo del sku > 4 entonces es producto tipo 3 y se rechaza
    if len(data['sku']) > 4:
        # print('rechazado porque es producto tipo 3 (len >4)')
        rechazar_oc(oc_id)
    elif data["amount"] > accept_amount:
        # print('rechazado porque pide más de 30')
        rechazar_oc(oc_id)
    elif data["sku"] not in ['1001', '1002', '1003', '1004', '1005', '1006', '1007', '1008',
                             '1009', '1010', '1011', '1012', '1013', '1014', '1015', '1016']:
        rechazar_oc(oc_id)
    else:
        totals = get_current_stock()
        raw_material = RawMaterial.objects.filter(sku=data['sku']).values()
        if not raw_material:  # Tested
            # raise Http404
            return Response({"error": "404 (Not Found): sku no existe."}, status=status.HTTP_404_NOT_FOUND)

        minimum_stock = raw_material[0]['stock']
        if totals[data['sku']] - data['amount'] < minimum_stock:
            # print("rechazo por que no hay productos en bodega - disponible: ", totals[data['sku']])
            rechazar_oc(oc_id)
        else:
            # print("hay productos pero no se si tiempo")
            if check_group_oc_time(fecha_entrega):
                # print("hay productos y tiempo")
                # aceptar oc, hay productos y alcanza el tiempo
                recepcionar_oc(oc_id)

                ids_origen, id_almacen_despacho = get_almacenes_origenes_destino()

                # Nuevo criteorio de mover y despachar productos uno por uno
                # (para evitar problemas con la capcidad del almacen de despacho)
                cantidad_despachada = 0  # aunque podriamos usar el valor de la OC
                # print(data['amount'], " > ", cantidad_despachada)
                # while data["amount"] != cantidad_despachada:
                for almacen in ids_origen:
                    productos = obtener_productos_almacen(almacen, data['sku'])
                    for elem in productos:
                        mover_entre_almacenes(elem['_id'], id_almacen_despacho)
                        response = mover_entre_bodegas(elem['_id'], data["storeId"], oc_id, 1)
                        # print(b)
                        # idea: check if response OK before count
                        cantidad_despachada += 1
                        if cantidad_despachada == data['amount']:
                            # Me salgo del primer for
                            break
                    if cantidad_despachada == data['amount']:
                        # me salgo del segundo for
                        break

                # print("Productos despachados: ", cantidad_despachada)
                # Quizás aquí podrías ver que el estado de la oc sea completa, aunque no estoy seguro si se arregla inmediatamente
                accepted_and_dispatched = True

            else:
                # print("hay productos pero NO tiempo")
                # rechazar oc por falta de tiempo
                rechazar_oc(oc_id)


    respuesta = {
		"sku" : data["sku"],
		"cantidad" : data["amount"],
		"almacenId" : data["storeId"],
		"grupoProveedor" : 13,
		"aceptado" : accepted_and_dispatched,
		"despachado" : accepted_and_dispatched
	}

    # falta accepted y dispatched en data
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
    return render(request, 'app/home.html', {"productos":productos})

def add_to_cart(request):
    productos = get_products_for_sale()
    valores = request.GET.items()
    pedido = {}
    for key, value in valores:
        pedido['sku'] = key
        pedido['cantidad'] = value
        pedido['ip'] = get_client_ip(request)

    messages.success(request, '¡Agregado al carro!')
    add_to_cart_file(request, pedido['sku'], pedido['cantidad'], pedido['ip'])
    return render(request, 'app/home.html', {'mensaje':True, 'productos':productos})


def see_cart(request):
    file_name = str(get_client_ip(request))+".json"
    try:
        with open(file_name) as outfile:
            data = json.load(outfile)

        return render(request, 'app/cart.html', {'carro_sku':data, 'carro_nombre':sku_to_name(data)})
    except FileNotFoundError:
        return render(request, 'app/cart.html', {'carro_sku':False})
