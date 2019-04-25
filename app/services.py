import requests
import json
import hashlib
import hmac
from base64 import encodestring


url_base = 'https://integracion-2019-dev.herokuapp.com/bodega'


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


if __name__ == '__main__':
    #print(obtener_almacenes())
    #print(obtener_skus_disponibles('5cbd3ce444f67600049431fc'))
    #print(obtener_productos_almacen('5cbd3ce444f67600049431fc', '1001'))
    print(fabricar_sin_pago("1007", 1))

