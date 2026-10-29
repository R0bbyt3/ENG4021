from django.urls import path

from . import views, seller_views, cart_views, favorite_views, order_views


urlpatterns = [
    path('checkout/', order_views.checkout, name='checkout'),
    path('pedidos/<int:order_id>/', order_views.order_detail, name='order_detail'),
    path('carrinho/', cart_views.cart_page, name='cart_page'),
    path('carrinho/adicionar/<int:product_id>/', cart_views.cart_add, name='cart_add'),
    path('carrinho/itens/<int:item_id>/quantidade/', cart_views.cart_update_item, name='cart_update_item'),
    path('carrinho/itens/<int:item_id>/remover/', cart_views.cart_remove_item, name='cart_remove_item'),
    path('favoritos/', favorite_views.favorites_list, name='favorites'),
    path('favoritos/adicionar/<int:product_id>/', favorite_views.favorite_add, name='favorite_add'),
    path('favoritos/remover/<int:product_id>/', favorite_views.favorite_remove, name='favorite_remove'),
    path('pecas/cadastrar/', seller_views.product_create, name='seller_product_create'),
    path('minhas-pecas/', seller_views.my_products, name='my_products'),
    path('simulador/', seller_views.discount_simulator, name='discount_simulator'),
    path('usuarios/', views.user_list, name='user_list'),
    path('vitrine/', views.home, name='home'),
    path('produtos/novo/', views.product_create, name='product_create'),
    path('produtos/<int:product_id>/editar/', views.product_update, name='product_update'),
    path('produtos/<int:product_id>/remover/', views.product_delete, name='product_delete'),
]
