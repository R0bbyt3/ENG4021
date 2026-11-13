"""Rotas do projeto: o admin e as rotas de cada app."""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('accounts.urls')),
    path('', include('products.urls')),
    path('', include('cart.urls')),
    path('', include('orders.urls')),
    path('', include('favorites.urls')),
    path('', include('reviews.urls')),
    path('', include('notifications.urls')),
]

# Em desenvolvimento o próprio Django entrega as fotos enviadas.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
