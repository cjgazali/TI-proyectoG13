from django.db import models


class Order(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    client_group = models.IntegerField(default=0)
    sku = models.CharField(max_length=10, default='')
    amount = models.IntegerField(default=0)
    storeId = models.CharField(max_length=30, default='')
    accepted = models.BooleanField(default=False)
    dispatched = models.BooleanField(default=False)

    class Meta:
        ordering = ('created',)


class Product(models.Model):
    # created = models.DateTimeField(auto_now_add=True)
    sku = models.CharField(primary_key=True, max_length=10, default='')
    name = models.TextField()
    description = models.TextField()
    sale_price = models.IntegerField(default=0) # Quizás puede no ser entero?
    number_ingredients_needed = models.IntegerField(default=0)
    number_products = models.IntegerField(default=0)
    expected_duration_time = models.FloatField()
    equivalence_units = models.FloatField()
    measurement_unit = models.CharField(max_length=10, default='')
    production_lot = models.IntegerField()
    expected_production_time = models.IntegerField()
    producer_groups = models.TextField()
    dispatch_space = models.IntegerField()
    reception_space = models.IntegerField()
    minimum_stock = models.IntegerField(default=0)


class Ingredient(models.Model):
    # Me parece que las tres columnas relevantes es produc_sku, ingredient_sku y units_quantity
    product_sku = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='products_column')
    product_name = models.TextField()
    ingredient_sku = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='ingredients_column')
    ingredient_name = models.TextField()
    quantity = models.FloatField()
    measurement_unit = models.CharField(max_length=10, default='')
    production_lot = models.IntegerField()
    quantity_for_lot = models.FloatField()
    units_quantity = models.IntegerField()


class Assigment(models.Model):
    sku = models.ForeignKey(Product, on_delete=models.CASCADE)
    group = models.IntegerField()


