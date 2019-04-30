# from django.shortcuts import render
# from rest_framework import status  # generate status codes
from rest_framework.response import Response  # DRF's HTTPResponse
from rest_framework.decorators import api_view  # DRF improves function view to APIView
from rest_framework.parsers import JSONParser
from rest_framework import status
from app.services import obtener_almacenes, obtener_skus_disponibles, obtener_productos_almacen, mover_entre_bodegas
from app.models import Order, Product  # , RawMaterial
from app.serializers import OrderSerializer
from django.http import Http404

@api_view(['GET'])  # only allows GET, else error code 405
def stock_list(request):
    """
    Entrega stock disponible por sku en toda la bodega.
    :return: lista con cada { sku, nombre, total }
    """
    almacenes = [] #Para almacenar los id de los almacenes
    skus = [] #Para llevar cuenta de qué skus ya he considerado
    respuesta_stock = [] #Stock de todos los almacenes
    respuesta_final = []
    prueba = obtener_almacenes()
    for almacen in prueba:
        almacenes.append(almacen["_id"])

    for id_almacen in almacenes:
        respuesta_stock.append(obtener_skus_disponibles(id_almacen))

    for resultado in respuesta_stock:
        for producto in resultado:

            if producto["_id"] not in skus:
                skus.append(producto["_id"])
                respuesta_final.append({"sku":producto["_id"] , "nombre": "", "total": producto["total"]})
            else:
                for elemento in respuesta_final:
                    if producto["_id"] in elemento.values():
                        elemento["total"] = elemento["total"] + int(producto["total"])

    return Response(respuesta_final)


@api_view(['POST'])
def create_order(request):
    """
    Permite crear un pedido de otro grupo para nosotros.
    :return: json { sku, cantidad, almacenId, grupoProveedor,
                    aceptado, despachado }
    """
    if 'sku' not in request.data or 'cantidad' not in request.data or 'almacenId' not in request.data:
        return Response({ "error": "400 (Bad Request): Falta parámetro obligatorio." }, status=status.HTTP_400_BAD_REQUEST)

    data = {'amount': int(request.data['cantidad']), 'sku':request.data['sku'], 'storeId':request.data['almacenId'], 'client_group':int(request.META['HTTP_GRUPO'])}

    query = Product.objects.all().values()  # esto se debe poder mejorar...
    sku_list=[]
    for p in query:
        sku_list.append(p['sku'])

    if data['sku'] not in sku_list:  # ...preguntar directamente si pertenece a conjunto sacado de BD
        #raise Http404
        return Response({ "error": "404 (Not Found): sku no existe."}, status=status.HTTP_404_NOT_FOUND)
        #return Response(serializer.errors, status=status.HTTP_404_NOT_FOUND)



    get_almacenes = obtener_almacenes()
    sku_stock = 0
    for almacen in get_almacenes:
        stock_response = obtener_productos_almacen(almacen["_id"], data["sku"])
        sku_stock += len(stock_response)

    print(sku_stock)

    accepted_and_dispatched = False

    # aceptar y despachar si tenemos excedente de ese sku...
    # respecto materias primas
    # usar info Seba
    # min_raw = RawMaterial.objects.filter(sku=data["sku"])
    # if min_raw:
    #     if sku_stock > min_raw.values().stock + data["amount"]:  # double check
    #         # mover a despacho
    #         # Mover entre bodegas
    #         accepted_and_dispatched = True
    # else:
    # respecto stock mínimo
    min_product = Product.objects.filter(sku=data["sku"]).values()  # double check
    if sku_stock > min_product.minimum_stock + data["amount"]:
        # mover a despacho
        almacenes = obtener_almacenes()
        for almacen in almacenes:
            if almacen['despacho']:
                id_almacen_despacho = almacen["_id"]
            else:
                ids_origen.append(almacen["_id"])
        # move_product_dispatch(ids_origen, id_almacen_despacho, data["amount"], data["sku"])
        # Mover entre bodegas
        # subtask move_product_client que usa mover_entre_bodegas para data["amount"] productos
        accepted_and_dispatched = True

    respuesta = {
		"sku" : data['sku'],
		"cantidad" : data['amount'],
		"almacenId" : data['storeId'],
		"grupoProveedor" : 13,
		"aceptado" : accepted_and_dispatched,
		"despachado" : accepted_and_dispatched
	}

    # falta accepted y dispatched en data

    serializer = OrderSerializer(data=data)
    if serializer.is_valid():
        serializer.save()
        return Response(respuesta, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
