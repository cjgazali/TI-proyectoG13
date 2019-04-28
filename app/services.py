import requests
import json
import hashlib
import hmac
from base64 import encodestring

# url API profe
url_base = 'https://integracion-2019-dev.herokuapp.com/bodega'

# url API grupos
server_url = "http://tuerca{}.ing.puc.cl"
inventories_url = server_url + "/inventories"
orders_url = server_url + "/orders"

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
    skus = json.loads(result.text)
    return skus


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


#
# Mueve un producto no vencido desde un almacén de despacho de un grupo a un almacén de recepcion de otro grupo.
# En caso que almacén de recepción se encuentre lleno, los productos quedan en almacén pulmón.  Recibe id_producto
# a mover (string) y el id  del almacén de destino (string)
def mover_entre_bodegas(id_producto, id_almacen_destino):
    frase_a_hashear = 'POST{}{}'.format(id_producto, id_almacen_destino)
    frase_hasheada = calcular_hash(frase_a_hashear)
    url = url_base + '/moveStockBodega'
    headers = {'Content-Type': 'application/json', 'Authorization': 'INTEGRACION grupo13:{}'.format(frase_hasheada)}
    body = {'productoId': id_producto, 'almacenId': id_almacen_destino, 'oc': 'YY'}
    result = requests.post(url, data=json.dumps(body), headers=headers)
    response = json.loads(result.text)
    return response


def get_group_stock(n_group):
    result = requests.get(inventories_url.format(n_group))
    response = json.loads(result.text)
    return response


if __name__ == '__main__':
    #a = obtener_almacenes()
    #for elem in a:
    #    print(elem)
    #for elem in a:
     #   f = obtener_productos_almacen(elem['_id'], '1001')
      #  for elem2 in f:
       #     print(elem2)

    # Este método es el que no está testeado aún, le pregunté al profe en una issue que onda
    f = mover_entre_bodegas('5cc22e96aa013f0004f0867e', '5cbd3ce444f67600049431d1')
    print(f)

    #print(obtener_productos_almacen('5cbd3ce444f67600049431fc', '1001'))
    #print(fabricar_sin_pago("1001", 10))
