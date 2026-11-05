from django.urls import path

from . import views

urlpatterns = [
    path('sobre/', views.about, name='about'),
    path('vitrine/', views.home, name='home'),
    path('produtos/<int:product_id>/', views.product_detail, name='product_detail'),
    path('produtos/novo/', views.product_create, name='product_create'),
    path('produtos/<int:product_id>/editar/', views.product_update, name='product_update'),
    path('produtos/<int:product_id>/remover/', views.product_delete, name='product_delete'),
    path('minhas-pecas/', views.my_products, name='my_products'),
    path('simulador/', views.discount_simulator, name='discount_simulator'),
]
