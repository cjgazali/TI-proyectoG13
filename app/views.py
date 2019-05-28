# from django.shortcuts import render
# from rest_framework import status  # generate status codes
from rest_framework.response import Response  # DRF's HTTPResponse
from rest_framework.decorators import api_view  # DRF improves function view to APIView
from rest_framework import status
from app.services import obtener_almacenes, obtener_productos_almacen, mover_entre_bodegas
from app.services import consultar_oc, ids_oc, rechazar_oc, recepcionar_oc, mover_entre_almacenes
from app.models import Product, RawMaterial
from app.serializers import OrderSerializer
from app.subtasks import get_current_stock, check_group_oc_time


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
    if 'sku' not in request.data or 'cantidad' not in request.data \
            or 'almacenId' not in request.data or 'oc' not in request.data:
        return Response({"error": "400 (Bad Request): Falta parámetro obligatorio."},
                        status=status.HTTP_400_BAD_REQUEST)

    oc_id = request.data['oc']
    order = consultar_oc(str(oc_id))
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
        # print('rechazado por que es producto tipo 3 (len >4)')
        rechazar_oc(oc_id)

    else:
        totals = get_current_stock()
        minimum_stock = RawMaterial.objects.filter(sku='1101').values()[0]['stock']
        if totals[data['sku']] - data['amount'] < minimum_stock:
            # print("rechazo por que no hay productos en bodega - disponible: ", totals[data['sku']])
            rechazar_oc(oc_id)
        else:
            # print("hay productos pero no se si tiempo")
            if check_group_oc_time(fecha_entrega):
                accepted_and_dispatched = True
                # print("hay productos y tiempo")
                # aceptar oc, hay productos y alcanza el tiempo
                recepcionar_oc(oc_id)


                almacenes = obtener_almacenes()
                ids_origen=[]
                for almacen in almacenes:
                    if almacen['despacho']:
                        id_almacen_despacho = almacen["_id"]
                    else:
                        ids_origen.append(almacen["_id"])#no estoy seguro que hacer con la cocina

                #Nuevo criteorio de mover y despachar productos uno por uno (para evitar problemas con la capcidad del almacen de despacho)
                cantidad_despachada = 0 #aunque podriamos usar el valor de la OC
                print(data['amount'], " > ", cantidad_despachada )
                while data["amount"] != cantidad_despachada:
                    for almacen in almacenes:
                        if not(almacen["cocina"] or almacen["despacho"]):
                            productos = obtener_productos_almacen(almacen["_id"], data['sku'])
                            for elem in productos:
                                a = mover_entre_almacenes(elem['_id'], id_almacen_despacho)
                                print(a)
                                b = mover_entre_bodegas(elem['_id'], data["storeId"], oc_id, 1)
                                print(b)
                                cantidad_despachada += 1
                                if cantidad_despachada == data['amount']:
                                    # Me salgo del primer for
                                    break
                        if cantidad_despachada == data['amount']:
                            # me salgo del segundo for y con eso no se cumplirá la condición del while
                            break

                    #TRATAR DE HACERLO DIRECTO DE LAS FUNCOINES DE SERVICES PARA QUE SEA MAS EFICIENTE

                    # # Mover entre bodegas
                    # move_product_dispatch(ids_origen, id_almacen_despacho, 1, data["sku"])#mover de a 1 es muy poco, hacerlo de a mas dependiendo capacidad de almacen despacho
                    # #subtask move_product_client que usa mover_entre_bodegas para data["amount"] productos
                    # print(data["sku"], 1, id_almacen_despacho, data["storeId"], oc_id, precio)
                    # move_product_client(data["sku"], 1, id_almacen_despacho, data["storeId"], oc_id, precio)#mover de a 1 es muy poco, hacerlo de a mas dependiendo capacidad de almacen despacho

                print("Productos despachados: ", cantidad_despachada)
                # Quizás aquí podrías ver que el estado de la oc sea completa, aunque no estoy seguro si se arregla inmediatamente
                accepted_and_dispatched = True

            else:
                print("hay productos pero NO tiempo")
                #rechazar oc por falta de tiempo
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
