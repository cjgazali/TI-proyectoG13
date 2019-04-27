from rest_framework import serializers
from app.models import Order, Product, Ingredient, Assigment


class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ('id', 'created', 'client_group', 'sku', 'amount',
                  'storeId', 'accepted', 'dispatched')


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ('id', 'sku', 'name', 'description', 'sale_price', 'number_ingredients_needed',
                  'number_products', 'expected_duration_time', 'equivalence_units',
                  'measurement_unit', 'production_lot', 'expected_production_time',
                  'producer_groups', 'dispatch_space', 'reception_space', 'minimum_stock')


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ('id', 'product_sku', 'product_name', 'ingredient_sku', 'ingredient_name',
                  'quantity', 'measurement_unit', 'production_lot', 'quantity_for_lot',
                  'units_quantity')


class AssigmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Assigment
        fields = ('id', 'sku', 'group')
