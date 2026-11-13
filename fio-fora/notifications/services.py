"""Avisos do sininho, usados por outros apps (pedidos, avaliações)."""
from django.utils import timezone

from .models import Notification


def notify(user, text, url):
    """Cria um aviso para a pessoa. Quem chama decide o texto e para onde o aviso leva."""
    return Notification.objects.create(user=user, text=text, url=url)


def unread_count(user):
    """Quantos avisos a pessoa ainda não viu (o número ao lado do sininho)."""
    return Notification.objects.filter(user=user, read_at__isnull=True).count()


def mark_read(notifications):
    """Marca como lidos os avisos mostrados na tela."""
    Notification.objects.filter(pk__in=[item.pk for item in notifications], read_at__isnull=True).update(
        read_at=timezone.now())
