from uuid import uuid4

from django.db import transaction
from django.db.models import F

from .cart_views import unavailable_reason
from .models import Cart, Order, OrderItem, Product


class CheckoutError(ValueError):
    pass


@transaction.atomic
def checkout_cart(user):
    cart = Cart.objects.select_for_update().filter(user=user).first()
    if cart is None:
        raise CheckoutError('Seu carrinho está vazio.')

    items = list(cart.items.select_for_update().select_related('product').order_by('product_id'))
    if not items:
        raise CheckoutError('Seu carrinho está vazio.')

    for item in items:
        if item.product.seller_id == user.pk:
            raise CheckoutError('Você não pode comprar a sua própria peça.')
        problem = unavailable_reason(item.product, item.quantity)
        if problem:
            raise CheckoutError(f'Não foi possível finalizar “{item.product.name}”. {problem}')

    order = Order.objects.create(user=user, reference=f'FF-{uuid4().hex[:12].upper()}')
    for item in items:
        updated = Product.objects.filter(
            pk=item.product_id, is_active=True, stock__gte=item.quantity,
        ).update(stock=F('stock') - item.quantity)
        if not updated:
            raise CheckoutError('O estoque mudou. Confira seu carrinho antes de finalizar novamente.')
        OrderItem.objects.create(
            order=order,
            product=item.product,
            product_name=item.product.name,
            unit_price=item.product.price,
            quantity=item.quantity,
        )

    cart.items.filter(pk__in=[item.pk for item in items]).delete()
    return order
