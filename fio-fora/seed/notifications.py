"""Bloco 5: avisos de exemplo, para o sininho já aparecer com número na apresentação."""
from django.urls import reverse
from django.utils import timezone

from notifications.models import Notification
from orders.models import Order

# (conta, texto, já lido?, pedido ou None). Com pedido, o aviso leva ao pedido;
# sem, leva a Minhas vendas. Os textos são os mesmos que o site gera.
NOTIFICATIONS = [
    ('julia@fiofora.com', 'Nova venda: Calça de alfaiataria no pedido FF-SEED-PEDIDO-003.', False, None),
    ('diego@fiofora.com', 'O pedido FF-SEED-PEDIDO-004 foi cancelado pelo comprador (Jaqueta jeans com bolsos). '
                          'O estoque já foi devolvido.', True, None),
    ('rafael@fiofora.com', 'Pedido FF-SEED-PEDIDO-001: 2 peças com status “Entregue”. Já dá para avaliar.',
     True, 'FF-SEED-PEDIDO-001'),
    ('gabriel@fiofora.com', 'Pedido FF-SEED-PEDIDO-002: Calça jeans reta com status “Enviado”.',
     False, 'FF-SEED-PEDIDO-002'),
]


def create_notifications(users):
    for email, text, read, reference in NOTIFICATIONS:
        if reference:
            url = reverse('order_detail', args=[Order.objects.get(reference=reference).pk])
        else:
            url = reverse('sales_list')
        # get_or_create pelo texto: rodar a seed de novo não repete o aviso.
        Notification.objects.get_or_create(user=users[email], text=text, defaults={
            'url': url, 'read_at': timezone.now() if read else None})
