from django.urls import path

from . import views

app_name = "pecas"

urlpatterns = [
    path("", views.lista_pecas, name="lista"),
    path("pecas/<int:pk>/", views.produto, name="produto"),
]
