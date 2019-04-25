from rest_framework import serializers
from app.models import Order


class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ('id', 'created', 'client_group', 'sku', 'amount',
                  'storeId', 'accepted', 'dispatched')
