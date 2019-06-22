from django.urls import path
from app import views

urlpatterns = [
    path('inventories', views.stock_list),
    path('orders', views.create_order),
    path('orders/<int:id>/notification', views.order_status, name="order_status"),
    path('ventas', views.bonus_home),
]
