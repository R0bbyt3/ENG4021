from django.urls import path

from . import views

urlpatterns = [
    path('sobre/', views.about, name='about'),
    path('ajuda/', views.faq, name='faq'),
    path('trabalhe-conosco/', views.careers, name='careers'),
    path('contato/', views.contact, name='contact'),
    path('termos/', views.terms, name='terms'),
    path('privacidade/', views.privacy, name='privacy'),
    path('vitrine/', views.home, name='home'),
    path('marcas/', views.store_list, name='store_list'),
    path('marcas/<int:seller_id>/', views.store_detail, name='store_detail'),
    path('produtos/<int:product_id>/', views.product_detail, name='product_detail'),
    path('produtos/novo/', views.product_create, name='product_create'),
    path('produtos/<int:product_id>/editar/', views.product_update, name='product_update'),
    path('produtos/<int:product_id>/remover/', views.product_delete, name='product_delete'),
    path('produtos/<int:product_id>/fotos/<int:image_id>/principal/', views.product_photo_cover, name='product_photo_cover'),
    path('produtos/<int:product_id>/fotos/<int:image_id>/remover/', views.product_photo_delete, name='product_photo_delete'),
    path('minhas-pecas/', views.my_products, name='my_products'),
    path('simulador/', views.discount_simulator, name='discount_simulator'),
]
