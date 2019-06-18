from datetime import datetime, timedelta

"""funciones que se importan solamente en views.py"""


def check_group_oc_time(date):
    """Revisa si hay tiempo para despachar inmediatamente"""

    now = datetime.utcnow()
    extra = timedelta(minutes=10)  # margen arbitrario
    date = datetime.strptime(date, "%Y-%m-%dT%H:%M:%S.%fZ")

    if now + extra < date:
        return True
    else:
        return False
