"""Bloco 5: avisos de exemplo, para o sininho já aparecer com número na apresentação."""
from django.urls import reverse
from django.utils import timezone

from notifications.models import Notification

# {vendedor: [(texto, já lido?)]}, com os mesmos textos que o site gera nas compras e cancelamentos.
NOTIFICATIONS = {
    'julia@fiofora.com': [
        ('Nova venda: Calça de alfaiataria no pedido FF-SEED-PEDIDO-003.', False),
    ],
    'diego@fiofora.com': [
        ('O pedido FF-SEED-PEDIDO-004 foi cancelado pelo comprador (Jaqueta jeans com bolsos). '
         'O estoque já foi devolvido.', True),
    ],
}


def create_notifications(users):
    for email, notices in NOTIFICATIONS.items():
        for text, read in notices:
            # get_or_create pelo texto: rodar a seed de novo não repete o aviso.
            Notification.objects.get_or_create(user=users[email], text=text, defaults={
                'url': reverse('sales_list'), 'read_at': timezone.now() if read else None})
