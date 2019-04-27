# from django.shortcuts import render
# from rest_framework import status  # generate status codes
from rest_framework.response import Response  # DRF's HTTPResponse
from rest_framework.decorators import api_view  # DRF improves function view to APIView
from rest_framework.parsers import JSONParser
from rest_framework import status
from app.services import obtener_almacenes, obtener_skus_disponibles
from app.models import Order
from app.serializers import OrderSerializer

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
                respuesta_final.append({"Sku":producto["_id"] , "Cantidad": producto["total"]})
            else:
                for elemento in respuesta_final:
                    if producto["_id"] in elemento.values():
                        elemento["Cantidad"]=elemento["Cantidad"]+int(producto["total"])

    return Response(respuesta_final)


@api_view(['POST'])
def create_order(request):
    """
    Permite crear un pedido de otro grupo para nosotros.
    :return: json { sku, cantidad, almacenId, grupoProveedor,
                    aceptado, despachado }
    """
    serializer = OrderSerializer(data=request.data)  # solo guarda bien sku por ahora
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)