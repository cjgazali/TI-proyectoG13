# from django.shortcuts import render
# from rest_framework import status  # generate status codes
from rest_framework.response import Response  # DRF's HTTPResponse
from rest_framework.decorators import api_view  # DRF improves function view to APIView
from rest_framework.parsers import JSONParser
from rest_framework import status
from app.services import obtener_almacenes, obtener_skus_disponibles, obtener_productos_almacen, mover_entre_bodegas
from app.models import Order, Product, RawMaterial
from app.serializers import OrderSerializer
from django.http import Http404
from app.subtasks import move_product_dispatch, move_product_client, get_current_stock


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
    productos = RawMaterial.objects.all()
    for materia in productos:
        stock_minimos[materia.sku.sku] = materia.stock

    for elem in stock_minimos:
        disponible_venta = max(totals[elem] - stock_minimos[elem], 0)
        if disponible_venta != 0:
            respuesta_final.append({"sku": elem, "nombre": aux_dict[elem],
                                    "total": disponible_venta})
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

    data = {'amount': int(request.data['cantidad']), 'sku':request.data['sku'], 'storeId':request.data['almacenId'], 'client_group':int(request.META['HTTP_GROUP']), 'order_id':request.data['oc']}
    
    query = Product.objects.all().values()  # esto se debe poder mejorar...
    sku_list=[]
    for p in query:
        sku_list.append(p['sku'])

    if data['sku'] not in sku_list:  # ...preguntar directamente si pertenece a conjunto sacado de BD
        #raise Http404
        return Response({ "error": "404 (Not Found): sku no existe."}, status=status.HTTP_404_NOT_FOUND)
        #return Response(serializer.errors, status=status.HTTP_404_NOT_FOUND)

    print("ok")

    get_almacenes = obtener_almacenes()
    sku_stock = 0
    for almacen in get_almacenes:
        stock_response = obtener_productos_almacen(almacen["_id"], data["sku"])
        sku_stock += len(stock_response)

    print(sku_stock)

    accepted_and_dispatched = False
    # aceptar y despachar si tenemos excedente de ese sku...

    # respecto materias primas
    min_raw = RawMaterial.objects.filter(sku=data["sku"]).values()
    if min_raw:
        if sku_stock > min_raw[0]['stock'] + data["amount"]:
            # mover a despacho
            almacenes = obtener_almacenes()
            ids_origen=[]
            for almacen in almacenes:
                if almacen['despacho']:
                    id_almacen_despacho = almacen["_id"]
                else:
                    ids_origen.append(almacen["_id"])
            # Mover entre bodegas
            move_product_dispatch(ids_origen, id_almacen_despacho, data["amount"], data["sku"])
            #subtask move_product_client que usa mover_entre_bodegas para data["amount"] productos
            move_product_client(data["sku"], data["amount"], id_almacen_despacho, data["storeId"])
            accepted_and_dispatched = True
    else:
        #respecto stock mínimo
        minimum_stock = Product.objects.filter(sku=data["sku"]).values('minimum_stock')[0]['minimum_stock']  # double check
        if sku_stock > minimum_stock + data["amount"]:
            # mover a despacho
            almacenes = obtener_almacenes()
            ids_origen=[]
            for almacen in almacenes:
                if almacen['despacho']:
                    id_almacen_despacho = almacen["_id"]
                else:
                    ids_origen.append(almacen["_id"])   #(QUE ES IDS_ORIGEN, NO ESTA DEFINIDO)
            # Mover entre bodegas
            move_product_dispatch(ids_origen, id_almacen_despacho, data["amount"], data["sku"]) #(IMPORTAR move_product_dispatch DE subtask)
            #subtask move_product_client que usa mover_entre_bodegas para data["amount"] productos #(DONDE ESTA LA FUNCION? SUPONGO QUE MUEVE DE DESPACHO NUESTRA A RECEPCION DEL OTRO GRUPO)
            move_product_client(data["sku"], data["amount"], id_almacen_despacho, data["storeId"])
            accepted_and_dispatched = True #(YO SOLO DEJARIA ACCEPTED EN TRUE, NO DISPATCHED)

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

    print("ok")

    serializer = OrderSerializer(data=data)
    if serializer.is_valid():
        serializer.save()
        print("ok")
        return Response(respuesta, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
