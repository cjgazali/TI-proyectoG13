import requests
import json
import hashlib
import xml.etree.ElementTree as ET
import pysftp
import hmac
from base64 import encodestring

context = "DEVELOPMENT"  # PRODUCTION or DEVELOPMENT
# url API profe
if context == "PRODUCTION":
    ids_oc = {1: '5cc66e378820160004a4c3bc', 2: '5cc66e378820160004a4c3bd', 3: '5cc66e378820160004a4c3be',
              4: '5cc66e378820160004a4c3bf', 5:	'5cc66e378820160004a4c3c0', 6: '5cc66e378820160004a4c3c1',
              7: '5cc66e378820160004a4c3c2', 8:	'5cc66e378820160004a4c3c3', 9: '5cc66e378820160004a4c3c4',
              10: '5cc66e378820160004a4c3c5', 11: '5cc66e378820160004a4c3c6', 12: '5cc66e378820160004a4c3c7',
              13: '5cc66e378820160004a4c3c8', 14: '5cc66e378820160004a4c3c9'}
    url_base = "https://integracion-2019-prod.herokuapp.com/bodega"
    url_oc = "https://integracion-2019-prod.herokuapp.com/oc"
    sftp_user_name = "grupo13"
    sftp_password = "UM5Hh7PbLZxJ8t241"
else:
    ids_oc = {1: '5cbd31b7c445af0004739be3', 2: '5cbd31b7c445af0004739be4', 3: '5cbd31b7c445af0004739be5',
              4: '5cbd31b7c445af0004739be6', 5: '5cbd31b7c445af0004739be7', 6: '5cbd31b7c445af0004739be8',
              7: '5cbd31b7c445af0004739be9', 8: '5cbd31b7c445af0004739bea', 9: '5cbd31b7c445af0004739beb',
              10: '5cbd31b7c445af0004739bec', 11: '5cbd31b7c445af0004739bed', 12: '5cbd31b7c445af0004739bee',
              13: '5cbd31b7c445af0004739bef', 14: '5cbd31b7c445af0004739bf0'}
    url_base = "https://integracion-2019-dev.herokuapp.com/bodega"
    url_oc = "https://integracion-2019-dev.herokuapp.com/oc"
    sftp_user_name = "grupo13_dev"
    sftp_password = "c7vq41weKJGcvas"

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
def mover_entre_bodegas(id_producto, id_almacen_destino, oc, precio):
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
    result = requests.get(inventories_url.format(n_group), timeout=8)
    response = json.loads(result.text)
    return response


def post_order(n_group, sku, quantity, id_almacen_recepcion, id_oc):
    headers = {'Content-Type': 'application/json', "group": "13"}
    body = {'sku': str(sku), 'cantidad': str(quantity), "almacenId": id_almacen_recepcion, 'oc': id_oc}
    result = requests.post(orders_url.format(n_group), data=json.dumps(body), headers=headers, timeout=20)
    response = json.loads(result.text)
    return response


# Consulta una orden de compra
def consultar_oc(id_orden):
    url = url_oc + '/obtener/{}'.format(id_orden)
    headers = {'Content-Type': 'application/json'}
    body = {'id': id_orden}
    result = requests.get(url, data=json.dumps(body), headers=headers)
    # print(result.status_code)
    if result.status_code != 200:
        # para uniformar casos (ver views l.53)
        return []
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


# Usar FTP para entregar OCs encontradas en servidor
def sftp_ocs(file_list):
    """Establece conección sftp, obtiene información, cierra conexión y entrega información obtenida"""
    host_name = "fierro.ing.puc.cl"
    cnopts = pysftp.CnOpts()
    cnopts.hostkeys = None
    ocs = []
    with pysftp.Connection(host=host_name, username=sftp_user_name, password=sftp_password,
                           port=22, cnopts=cnopts) as sftp:
        sftp.cwd('/pedidos')
        directory_structure = sftp.listdir_attr()
        for attr in directory_structure:
            if attr.filename not in file_list:
                with sftp.open(attr.filename) as archivo:
                    tree = ET.parse(archivo)
                    root = tree.getroot()
                    for elem in root:
                        if elem.tag == 'id':
                            ocs.append((elem.text, attr.filename))
    return ocs


# Postear notificacion luego de recibir orden
def post_notification(status, n_group, order_id):
    headers = {'Content-Type': 'application/json'}
    body = {'status':status}
    result = requests.post(orders_url.format(n_group)+"/{}/notification".format(order_id), data=json.dumps(body), headers=headers)
    response = json.loads(result.text)
    return response


if __name__ == '__main__':
    pass
