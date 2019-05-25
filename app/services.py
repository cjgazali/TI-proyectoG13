from datetime import datetime
import requests
import json
import hashlib
import xml.etree.ElementTree as ET
import pysftp
import hmac
from base64 import encodestring

context = "DEVELOPMENT"  # or DEVELOPMENT
# url API profe
if context == "PRODUCTION":
    ids_oc = {1: '5cc66e378820160004a4c3bc', 2: '5cc66e378820160004a4c3bd', 3: '5cc66e378820160004a4c3be',
              4: '5cc66e378820160004a4c3bf', 5:	'5cc66e378820160004a4c3c0', 6: '5cc66e378820160004a4c3c1',
              7: '5cc66e378820160004a4c3c2', 8:	'5cc66e378820160004a4c3c3', 9: '5cc66e378820160004a4c3c4',
              10: '5cc66e378820160004a4c3c5', 11: '5cc66e378820160004a4c3c6', 12: '5cc66e378820160004a4c3c7',
              13: '5cc66e378820160004a4c3c8', 14: '5cc66e378820160004a4c3c9'}
    url_base = "https://integracion-2019-prod.herokuapp.com/bodega"
else:
    ids_oc = {1: '5cbd31b7c445af0004739be3', 2: '5cbd31b7c445af0004739be4', 3: '5cbd31b7c445af0004739be5',
              4: '5cbd31b7c445af0004739be6', 5: '5cbd31b7c445af0004739be7', 6: '5cbd31b7c445af0004739be8',
              7: '5cbd31b7c445af0004739be9', 8: '5cbd31b7c445af0004739bea', 9: '5cbd31b7c445af0004739beb',
              10: '5cbd31b7c445af0004739bec', 11: '5cbd31b7c445af0004739bed', 12: '5cbd31b7c445af0004739bee',
              13: '5cbd31b7c445af0004739bef', 14: '5cbd31b7c445af0004739bf0'}
    url_base = "https://integracion-2019-dev.herokuapp.com/bodega"
    url_oc = "https://integracion-2019-dev.herokuapp.com/oc"

# url API grupos
server_url = "http://tuerca{}.ing.puc.cl"
inventories_url = server_url + "/inventories"
orders_url = server_url + "/orders"

min_stock_factor = 2
min_raws_factor = 2


# Código replicado de https://sites.google.com/site/studyingpython/home/basis/hmac-sha1
# Esta función recibe texto a hashear (ejemplo API profe: GET534960ccc88ee69029cd3fb2)
def calcular_hash(texto):
    clave = str.encode("KbcdWTftPaKFKvO")
    frase = str.encode(texto)

    hash = hmac.new(clave, frase, hashlib.sha1).digest()
    b = encodestring(hash)
    b = b.rstrip()
    return b.decode("utf-8")


# Esta función devuelve una lista de almacenes
def obtener_almacenes():
    frase_a_hashear = 'GET'
    frase_hasheada = calcular_hash(frase_a_hashear)
    url = url_base + '/almacenes'
    headers = {'Content-Type': 'application/json', 'Authorization': 'INTEGRACION grupo13:{}'.format(frase_hasheada)}
    result = requests.get(url, headers=headers)
    # print(result)
    almacenes = json.loads(result.text)
    return almacenes


# Esta función muestra los productos no vencidos en el almacén ID para el SKU indicado
def obtener_productos_almacen(id_almacen, sku):
    frase_a_hashear = 'GET{}{}'.format(id_almacen, sku)
    frase_hasheada = calcular_hash(frase_a_hashear)
    url = url_base + '/stock?almacenId={}&sku={}'.format(id_almacen, sku)
    headers = {'Content-Type': 'application/json', 'Authorization': 'INTEGRACION grupo13:{}'.format(frase_hasheada)}
    result = requests.get(url, headers=headers)
    productos = json.loads(result.text)
    return productos


# Obtiene todos los skus que tienen stock no vencido en una bodega. Si un sku no tiene stock,
# no aparecerá en los resultados
def obtener_skus_disponibles(id_almacen):
    frase_a_hashear = 'GET{}'.format(id_almacen)
    frase_hasheada = calcular_hash(frase_a_hashear)
    url = url_base + '/skusWithStock?almacenId={}'.format(id_almacen)
    headers = {'Content-Type': 'application/json', 'Authorization': 'INTEGRACION grupo13:{}'.format(frase_hasheada)}
    result = requests.get(url, headers=headers)
    skus = json.loads(result.text)
    return skus


# Este servicio será deprecado. A través de este servicio se envían a fabricar productos con o sin
# materias primas. Este servicio no requiere realizar el pago de la fabricación.
# SKU es un string y cantidad es un int
def fabricar_sin_pago(sku, cantidad):
    frase_a_hashear = 'PUT{}{}'.format(sku, str(cantidad))
    frase_hasheada = calcular_hash(frase_a_hashear)
    url = url_base + '/fabrica/fabricarSinPago'
    headers = {'Content-Type': 'application/json', 'Authorization': 'INTEGRACION grupo13:{}'.format(frase_hasheada)}
    body = {'sku': sku, 'cantidad': cantidad}
    result = requests.put(url, data=json.dumps(body), headers=headers)
    response = json.loads(result.text)
    return response


# Mueve un producto de un almacén a otro dentro de una misma bodega. Recibe id_producto a mover (string) y el id
# del almacén de destino (string)
def mover_entre_almacenes(id_producto, id_almacen_destino):
    frase_a_hashear = 'POST{}{}'.format(id_producto, id_almacen_destino)
    frase_hasheada = calcular_hash(frase_a_hashear)
    url = url_base + '/moveStock'
    headers = {'Content-Type': 'application/json', 'Authorization': 'INTEGRACION grupo13:{}'.format(frase_hasheada)}
    body = {'productoId': id_producto, 'almacenId': id_almacen_destino}
    result = requests.post(url, data=json.dumps(body), headers=headers)
    response = json.loads(result.text)
    return response


# Mueve un producto no vencido desde un almacén de despacho de un grupo a un almacén de recepcion de otro grupo.
# En caso que almacén de recepción se encuentre lleno, los productos quedan en almacén pulmón.  Recibe id_producto
# a mover (string), el id  del almacén de destino (string) y opcionalmente la orden de compra con precio
def mover_entre_bodegas(id_producto, id_almacen_destino, oc="BLABLA", precio=10):
    frase_a_hashear = 'POST{}{}'.format(id_producto, id_almacen_destino)
    frase_hasheada = calcular_hash(frase_a_hashear)
    url = url_base + '/moveStockBodega'
    headers = {'Content-Type': 'application/json', 'Authorization': 'INTEGRACION grupo13:{}'.format(frase_hasheada)}
    body = {'productoId': id_producto, 'almacenId': id_almacen_destino, 'oc': oc, "precio": precio}
    result = requests.post(url, data=json.dumps(body), headers=headers)
    response = json.loads(result.text)
    return response


# Despacha un producto asociado a una orden de compra
def despachar_producto(id_producto, id_oc, direccion="BLABLA", precio=1):
    frase_a_hashear = 'DELETE{}{}{}{}'.format(id_producto, direccion, precio, id_oc)
    frase_hasheada = calcular_hash(frase_a_hashear)
    url = url_base + '/stock'
    headers = {'Content-Type': 'application/json', 'Authorization': 'INTEGRACION grupo13:{}'.format(frase_hasheada)}
    body = {'productoId': id_producto, 'oc': id_oc, 'direccion': direccion, 'precio': precio}
    result = requests.delete(url, data=json.dumps(body), headers=headers)
    response = json.loads(result.text)
    return response


def get_group_stock(n_group):
    result = requests.get(inventories_url.format(n_group))
    response = json.loads(result.text)
    return response


def post_order(n_group, sku, quantity, id_almacen_despacho):
    aceptado = False
    headers = {'Content-Type': 'application/json', "group": "13"}
    body = {'sku': str(sku), 'cantidad': str(quantity), "almacenId": id_almacen_despacho}
    result = requests.post(orders_url.format(n_group), data=json.dumps(body), headers=headers)
    response = json.loads(result.text)
    return response


# Consulta una orden de compra
def consultar_oc(id_orden):
    url = url_oc + '/obtener/{}'.format((id_orden))
    headers = {'Content-Type': 'application/json'}
    body = {'id': id_orden}
    result = requests.get(url, data=json.dumps(body), headers=headers)
    response = json.loads(result.text)
    return response


# Crear una orden de compra
def crear_oc(cliente, proveedor, sku, fecha_entrega, cantidad, precio_unitario, canal, url_notificacion):
    url = url_oc + '/crear'
    headers = {'Content-Type': 'application/json'}
    body = {'cliente': cliente, 'proveedor': proveedor, 'sku': int(sku),
            'fechaEntrega': int(fecha_entrega), 'cantidad': int(cantidad),
            'precioUnitario': int(precio_unitario), 'canal': canal,
            'urlNotificacion': url_notificacion}
    result = requests.put(url, data=json.dumps(body), headers=headers)
    response = json.loads(result.text)
    return response


# Anula una orden de compra
def anular_oc(id_orden):
    url = url_oc + '/anular/{}'.format(id_orden)
    headers = {'Content-Type': 'application/json'}
    body = {'id': id_orden, 'anulacion': 'Anulación de prueba'}
    result = requests.delete(url, data=json.dumps(body), headers=headers)
    response = json.loads(result.text)
    return response


# Rechazar oc
def rechazar_oc(id_orden):
    url = url_oc + '/rechazar/{}'.format(id_orden)
    headers = {'Content-Type': 'application/json'}
    body = {'id': id_orden, 'rechazo': 'Reechazo de prueba'}
    result = requests.post(url, data=json.dumps(body), headers=headers)
    response = json.loads(result.text)
    return response


# Recepcionar oc
def recepcionar_oc(id_orden):
    url = url_oc + '/recepcionar/{}'.format(id_orden)
    headers = {'Content-Type': 'application/json'}
    body = {'id': id_orden}
    result = requests.post(url, data=json.dumps(body), headers=headers)
    response = json.loads(result.text)
    return response


# Ver servidor
def prueba_servidor():
    host_name = "fierro.ing.puc.cl"
    user_name = "grupo13_dev"
    password = "c7vq41weKJGcvas"
    cnopts = pysftp.CnOpts()
    cnopts.hostkeys = None
    with pysftp.Connection(host=host_name, username=user_name, password=password, port=22, cnopts=cnopts) as sftp:
        print("Connection succesfully stablished ... ")
        sftp.cwd('/pedidos')
        directory_structure = sftp.listdir_attr()
        cont = 0
        for attr in directory_structure:
            cont += 1
            if cont < 3:
                with sftp.open(attr.filename) as archivo:
                    tree = ET.parse(archivo)
                    root = tree.getroot()
                    for elem in root:
                        if elem.tag == 'id':
                            print('id a consultar: {}'.format(elem.text))
                            response = consultar_oc(elem.text)
                            fecha_entrega = response[0]['fechaEntrega']
                            print(fecha_entrega)
                            # Desarrollar algoritmo
            print(attr.filename, type(attr.filename))


if __name__ == '__main__':
    #a = obtener_almacenes()
    #for elem in a:
    #    print(elem)
    #for elem in a:
    #    f = obtener_productos_almacen(elem['_id'], '1001')
    #    for elem2 in f:
    #        print(elem2)
    print(despachar_producto('5ce838757f76a200046f4d83', '5ce8878e87a0f1000481559e'))
    #l = mover_entre_almacenes('5cc6250c93360b0004f0431b', '5cbd3ce444f67600049431fc')
    #print(l)
    # Este método es el que no está testeado aún, le pregunté al profe en una issue que onda
    #f = mover_entre_bodegas('5cc22ede compra96aa013f0004f0867e', '5cbd3ce444f67600049431d1')
    #print(f)
    #f = obtener_productos_almacen('5cbd3ce444f67600049431ff', '1001')
    #print(f)
    #fecha_minima = "1970-01-01"
    #fecha1 = datetime.strptime(fecha_minima, '%Y-%m-%d')
    #tomorrow = "2019-05-28"
    #fecha2 = datetime.strptime(tomorrow, '%Y-%m-%d')
    #diff = fecha2 - fecha1
    #print(type(diff), type(diff * 1000), diff)
    #print(crear_oc('5cbd31b7c445af0004739beb', '5cbd31b7c445af0004739bef', 1001, diff.total_seconds() * 1000,
    #               1, 1, 'b2b', "http://ejemplo.com/notificacion/{_id}"))
    #por_borrar = '5ce213be9305c300043eda19'
    #print(rechazar_oc('5ce33bc7bed9c00004d897fa'))
    #prueba_servidor()
    #print(obtener_productos_almacen('5cbd3ce444f67600049431fc', '1001'))
    #print(fabricar_sin_pago("1001", 10))
