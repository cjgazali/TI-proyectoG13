from django.urls import path
from app import views

urlpatterns = [
    path('inventories/', views.stock_list),
]
