from django.urls import path

from . import views

urlpatterns = [
    path('minhas-vendas/', views.sales_list, name='sales_list'),
    path('minhas-vendas/<int:order_id>/status/', views.sale_status_update, name='sale_status_update'),
    path('checkout/', views.checkout, name='checkout'),
    path('pedidos/', views.order_list, name='order_list'),
    path('pedidos/<int:order_id>/', views.order_detail, name='order_detail'),
]
