from decimal import Decimal
from uuid import uuid4

from django.core.mail import send_mail
from django.db import transaction
from django.db.models import F
from django.template.loader import render_to_string

from accounts.forms import ADDRESS_KEYS
from cart.models import Cart
from cart.services import purchase_summary, unavailable_reason
from products.models import Product

from .models import Order, OrderItem


class CheckoutError(ValueError):
    pass


# Partes do endereço sem as quais não dá para entregar (o complemento é opcional).
REQUIRED_ADDRESS_KEYS = ['cep', 'street', 'number', 'district', 'location']


@transaction.atomic
def checkout_cart(user, address):
    """Cria o pedido com o endereço e o frete, e desconta o estoque.

    `address` tem as chaves de accounts.forms.ADDRESS_KEYS. O frete e o total
    são calculados aqui, no servidor, a partir dos preços do banco.
    """
    if not address or not all(address.get(key) for key in REQUIRED_ADDRESS_KEYS):
        raise CheckoutError('Informe o endereço de entrega completo.')

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

    subtotal = sum((item.product.price * item.quantity for item in items), Decimal('0.00'))
    order = Order.objects.create(
        user=user,
        reference=f'FF-{uuid4().hex[:12].upper()}',
        shipping_cost=purchase_summary(subtotal)['shipping'],
        **{f'shipping_{key}': address.get(key, '') for key in ADDRESS_KEYS},
    )
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
    context = {'order': order, 'items': order.items.all(), 'order_url': order_url,
               'address_lines': order.shipping_address_lines}
    subject = render_to_string('orders/email/order_confirmation_subject.txt', context).strip()
    body = render_to_string('orders/email/order_confirmation.txt', context)
    html = render_to_string('orders/email/order_confirmation.html', context)
    try:
        send_mail(subject, body, None, [order.user.email], html_message=html)
    except OSError:
        return False
    return True
