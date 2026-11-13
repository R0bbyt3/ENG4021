from django.urls import path

from . import views

urlpatterns = [
    path('avisos/', views.notification_list, name='notifications'),
]
