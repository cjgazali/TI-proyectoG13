from django.urls import path
from app import views

urlpatterns = [
    path('inventories', views.stock_list),
    path('orders', views.create_order),
    path('probando', views.create_fake_order), #solo para pruebas locales
    path('orders/<int:id>/notification', views.order_status, name="order_status"),
]
