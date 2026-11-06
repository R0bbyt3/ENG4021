"""Bloco 4: pedidos (um de cada status) e avaliações das peças compradas."""
from orders.models import Order, OrderItem
from reviews.models import Review

ORDERS = [
    {'reference': 'FF-SEED-PEDIDO-001', 'buyer': 'rafael@fiofora.com', 'status': 'shipped',
     'items': ['FF-SEED-003', 'FF-SEED-001']},
    {'reference': 'FF-SEED-PEDIDO-002', 'buyer': 'gabriel@fiofora.com', 'status': 'paid',
     'items': ['FF-SEED-005']},
    # Pendente e sem avaliação: mostra o formulário "Avaliar esta peça".
    {'reference': 'FF-SEED-PEDIDO-003', 'buyer': 'rafael@fiofora.com', 'status': 'pending',
     'items': ['FF-SEED-008']},
    {'reference': 'FF-SEED-PEDIDO-004', 'buyer': 'gabriel@fiofora.com', 'status': 'cancelled',
     'items': ['FF-SEED-006']},
]

# {(pedido, sku): (nota, comentário)}
REVIEWS = {
    ('FF-SEED-PEDIDO-001', 'FF-SEED-003'): (5, 'A mancha é bem menor do que eu imaginava e some na estampa.'),
    ('FF-SEED-PEDIDO-001', 'FF-SEED-001'): (4, 'Chegou como no anúncio. A costura solta foi fácil de arrumar.'),
    ('FF-SEED-PEDIDO-002', 'FF-SEED-005'): (4, 'O desbotado aparece, mas combina com o estilo da calça.'),
}


def create_purchases(users, products):
    for data in ORDERS:
        order, _ = Order.objects.get_or_create(reference=data['reference'], defaults={
            'user': users[data['buyer']], 'status': data['status']})
        # Itens só entram em pedido novo, para não mexer em um histórico que já existe.
        if order.items.exists():
            continue
        for sku in data['items']:
            product = products[sku]
            item = OrderItem.objects.create(order=order, product=product, product_name=product.name,
                                            unit_price=product.price, quantity=1)
            review = REVIEWS.get((order.reference, sku))
            if review:
                Review.objects.create(order_item=item, user=order.user, rating=review[0], comment=review[1])
