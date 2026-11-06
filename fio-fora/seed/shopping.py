"""Bloco 3: favoritos e carrinho dos compradores."""
from cart.models import Cart, CartItem
from favorites.models import Favorite

FAVORITES = {
    'rafael@fiofora.com': ['FF-SEED-001', 'FF-SEED-003', 'FF-SEED-005'],
    'gabriel@fiofora.com': ['FF-SEED-007', 'FF-SEED-008'],
}

# {comprador: [(sku, quantidade)]}
CARTS = {
    'rafael@fiofora.com': [('FF-SEED-002', 1), ('FF-SEED-007', 2)],
    'gabriel@fiofora.com': [('FF-SEED-005', 1)],
}


def create_shopping(users, products):
    for email, skus in FAVORITES.items():
        for sku in skus:
            Favorite.objects.get_or_create(user=users[email], product=products[sku])

    for email, items in CARTS.items():
        cart, _ = Cart.objects.get_or_create(user=users[email])
        for sku, quantity in items:
            CartItem.objects.get_or_create(cart=cart, product=products[sku], defaults={'quantity': quantity})
