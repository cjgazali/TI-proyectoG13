from django.urls import path
from app import views

urlpatterns = [
    path('inventories', views.stock_list),
    path('orders', views.create_order),
    path('orders/<int:id>/notification', views.order_status, name="order_status"),
    path('ventas', views.bonus_home),
    path('add_to_cart', views.add_to_cart),
    path('ventas/cart', views.see_cart)
]
