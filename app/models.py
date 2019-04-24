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
