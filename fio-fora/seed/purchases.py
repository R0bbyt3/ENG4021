"""Bloco 4: pedidos (pendente, enviado, entregue e cancelado) e avaliações das peças compradas."""
from cart.services import SHIPPING_COST
from orders.models import Order, OrderItem
from reviews.models import Review

ORDERS = [
    # Entregue: libera as avaliações.
    {'reference': 'FF-SEED-PEDIDO-001', 'buyer': 'rafael@fiofora.com', 'status': 'delivered',
     'items': ['FF-SEED-003', 'FF-SEED-001']},
    # Enviado: mostra o botão "Recebi a peça"; depois de confirmar, libera a avaliação.
    {'reference': 'FF-SEED-PEDIDO-002', 'buyer': 'gabriel@fiofora.com', 'status': 'shipped',
     'items': ['FF-SEED-005']},
    # Pendente: mostra que só dá para avaliar depois da entrega.
    {'reference': 'FF-SEED-PEDIDO-003', 'buyer': 'rafael@fiofora.com', 'status': 'pending',
     'items': ['FF-SEED-008']},
    {'reference': 'FF-SEED-PEDIDO-004', 'buyer': 'gabriel@fiofora.com', 'status': 'cancelled',
     'items': ['FF-SEED-006']},
]

# {(pedido, sku): (nota, comentário)}. Só pedidos entregues têm avaliação.
REVIEWS = {
    ('FF-SEED-PEDIDO-001', 'FF-SEED-003'): (5, 'A mancha é bem menor do que eu imaginava e some na estampa.'),
    ('FF-SEED-PEDIDO-001', 'FF-SEED-001'): (4, 'Chegou como no anúncio. A costura solta foi fácil de arrumar.'),
}


def shipping_data(user):
    """Frete e endereço do pedido: uma cópia do endereço que está no perfil do comprador."""
    profile = user.profile
    return {
        'shipping_cost': SHIPPING_COST,
        'shipping_cep': profile.address_cep,
        'shipping_street': profile.address_street,
        'shipping_number': profile.address_number,
        'shipping_complement': profile.address_complement,
        'shipping_district': profile.address_district,
        'shipping_location': profile.address_location,
    }


def create_purchases(users, products):
    for data in ORDERS:
        buyer = users[data['buyer']]
        order, _ = Order.objects.get_or_create(reference=data['reference'], defaults={
            'user': buyer, 'status': data['status'], **shipping_data(buyer)})
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
