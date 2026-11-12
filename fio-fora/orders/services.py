from uuid import uuid4

from django.core.mail import send_mail
from django.http import Http404
from django.db import transaction
from django.db.models import F
from django.template.loader import render_to_string

from cart.models import Cart
from cart.services import unavailable_reason
from products.models import Product

from .models import Order, OrderItem


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


def send_order_confirmation(order, order_url):
    """Envia ao comprador o e-mail de confirmação do pedido.

    Devolve True se o e-mail foi entregue ao servidor de envio. Uma falha no
    e-mail nunca desfaz o pedido, por isso o erro não sobe: quem chama decide
    o que avisar na tela.
    """
    if not order.user.email:
        return False
    context = {'order': order, 'items': order.items.all(), 'order_url': order_url}
    subject = render_to_string('orders/email/order_confirmation_subject.txt', context).strip()
    body = render_to_string('orders/email/order_confirmation.txt', context)
    html = render_to_string('orders/email/order_confirmation.html', context)
    try:
        send_mail(subject, body, None, [order.user.email], html_message=html)
    except OSError:
        return False
    return True


class OrderStatusError(ValueError):
    pass


STATUS_STEPS = (Order.Status.PENDING, Order.Status.PAID, Order.Status.SHIPPED, Order.Status.DELIVERED)
NEXT_SALE_STATUS = dict(zip(STATUS_STEPS, STATUS_STEPS[1:]))


def next_sale_status(items):
    statuses = {item.sale_status for item in items}
    if len(statuses) == 1:
        return NEXT_SALE_STATUS.get(statuses.pop())
    return None


@transaction.atomic
def advance_sale(order_id, seller, requested_status):
    # Serializa mudanças no mesmo pedido, inclusive no SQLite.
    owned_items = OrderItem.objects.filter(product__seller=seller, order_id=order_id)
    if not Order.objects.filter(pk=order_id, pk__in=owned_items.values('order_id')).update(status=F('status')):
        raise Http404
    order = Order.objects.prefetch_related('items__product').get(pk=order_id)
    items = list(order.items.all())
    seller_items = [item for item in items if item.product and item.product.seller_id == seller.pk]
    if not seller_items:
        raise Http404
    target = next_sale_status(seller_items)
    if target is None or requested_status != target:
        raise OrderStatusError('Essa mudança de status não está disponível. Confira o andamento da venda.')
    # Fixa o status anterior de itens legados antes de recalcular o pedido.
    order.items.filter(fulfillment_status__isnull=True).update(fulfillment_status=order.status)
    owned_items.update(fulfillment_status=target)
    statuses = set(order.items.values_list('fulfillment_status', flat=True))
    order.status = next(step for step in STATUS_STEPS if step in statuses)
    order.save(update_fields=['status'])
