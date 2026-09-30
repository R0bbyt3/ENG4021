from django.urls import path

from . import views


urlpatterns = [
    path('', views.login_page, name='login_page'),
    path('login/', views.login_page, name='login'),
    path('vitrine/', views.home, name='home'),
    path('recuperar-senha/', views.password_reset_page, name='password_reset_page'),
    path('cadastro/', views.account_type_page, name='account_type_page'),
    path('cadastro/comprador/', views.buyer_register_page, name='buyer_register_page'),
    path('cadastro/vendedor/', views.seller_register_page, name='seller_register_page'),
    path('cadastro/marca/', views.brand_register_page, name='brand_register_page'),
    path('produtos/novo/', views.product_create, name='product_create'),
    path('produtos/<int:product_id>/editar/', views.product_update, name='product_update'),
    path('produtos/<int:product_id>/remover/', views.product_delete, name='product_delete'),
]
