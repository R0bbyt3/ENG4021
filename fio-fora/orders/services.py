from decimal import Decimal
from uuid import uuid4

from django.core.mail import send_mail
from django.http import Http404
from django.db import transaction
from django.db.models import F
from django.template.loader import render_to_string
from django.urls import reverse

from accounts.forms import ADDRESS_KEYS
from cart.models import Cart
from cart.services import purchase_summary, unavailable_reason
from notifications.services import notify
from products.models import Product

from .models import Order, OrderItem


class CheckoutError(ValueError):
    pass


def items_by_seller(items):
    """Agrupa os itens de um pedido por loja: cada loja recebe um aviso, não um por peça."""
    groups = {}
    for item in items:
        # Peça apagada ou sem vendedor não tem loja para avisar.
        if item.product is not None and item.product.seller_id is not None:
            groups.setdefault(item.product.seller, []).append(item)
    return groups


def pieces_text(items):
    """“Vestido floral” para uma peça, “2 peças” para mais de uma."""
    return items[0].product_name if len(items) == 1 else f'{len(items)} peças'


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
    order_items = []
    for item in items:
        updated = Product.objects.filter(
            pk=item.product_id, is_active=True, stock__gte=item.quantity,
        ).update(stock=F('stock') - item.quantity)
        if not updated:
            raise CheckoutError('O estoque mudou. Confira seu carrinho antes de finalizar novamente.')
        order_items.append(OrderItem.objects.create(
            order=order,
            product=item.product,
            product_name=item.product.name,
            unit_price=item.product.price,
            quantity=item.quantity,
        ))

    cart.items.filter(pk__in=[item.pk for item in items]).delete()
    # Aviso ao vendedor: dentro da transação, então só existe se a compra deu certo.
    for seller, seller_items in items_by_seller(order_items).items():
        notify(seller, f'Nova venda: {pieces_text(seller_items)} no pedido {order.reference}.', reverse('sales_list'))
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


class OrderStatusError(ValueError):
    pass


STATUS_STEPS = (Order.Status.PENDING, Order.Status.PAID, Order.Status.SHIPPED, Order.Status.DELIVERED)
NEXT_SALE_STATUS = dict(zip(STATUS_STEPS, STATUS_STEPS[1:]))
# Texto do botão do vendedor para levar a venda a cada status.
SALE_ACTIONS = {
    Order.Status.PAID: 'Confirmar pagamento',
    Order.Status.SHIPPED: 'Marcar como enviado',
    Order.Status.DELIVERED: 'Confirmar entrega',
}


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
    refresh_order_status(order)
    notify_buyer_status(order, seller_items, target)


def refresh_order_status(order):
    """O status geral do pedido é a etapa mais atrasada entre as peças (de todas as lojas)."""
    statuses = set(order.items.values_list('fulfillment_status', flat=True))
    order.status = next(step for step in STATUS_STEPS if step in statuses)
    order.save(update_fields=['status'])


def notify_buyer_status(order, items, status):
    """Avisa o comprador que peças do pedido mudaram de status."""
    text = f'Pedido {order.reference}: {pieces_text(items)} com status “{status.label}”.'
    if status == Order.Status.DELIVERED:
        text += ' Já dá para avaliar.'
    notify(order.user, text, reverse('order_detail', args=[order.pk]))


class ReceiptError(ValueError):
    pass


def shipped_items_from(order, seller_id):
    """Peças de uma loja neste pedido que já foram enviadas e esperam o comprador confirmar."""
    items = order.items.select_related('order', 'product__seller')
    return [item for item in items
            if item.product and item.product.seller_id == seller_id and item.sale_status == Order.Status.SHIPPED]


@transaction.atomic
def confirm_receipt(order_id, buyer, seller_id):
    """“Recebi a peça”: o comprador marca como entregues as peças enviadas por uma loja.

    Vale para a loja inteira, porque o vendedor também avança todas as peças
    dele juntas. Não tem volta: entregue é o último status.
    """
    # Trava o pedido (só o do próprio comprador) para dois cliques não confirmarem duas vezes.
    if not Order.objects.filter(pk=order_id, user=buyer).update(status=F('status')):
        raise Http404
    order = Order.objects.get(pk=order_id)
    items = shipped_items_from(order, seller_id)
    if not items:
        raise ReceiptError('Não há peças enviadas desta loja para confirmar neste pedido.')
    order.items.filter(fulfillment_status__isnull=True).update(fulfillment_status=order.status)
    OrderItem.objects.filter(pk__in=[item.pk for item in items]).update(fulfillment_status=Order.Status.DELIVERED)
    refresh_order_status(order)
    buyer_name = buyer.get_full_name() or buyer.get_username()
    notify(items[0].product.seller,
           f'{buyer_name} confirmou que recebeu {pieces_text(items)} do pedido {order.reference}.',
           reverse('sales_list'))


class OrderCancellationError(ValueError):
    pass


CANCELLABLE_STATUSES = (Order.Status.PENDING, Order.Status.PAID)
DISPATCHED_STATUSES = (Order.Status.SHIPPED, Order.Status.DELIVERED)


def can_cancel_order(order, items):
    return order.status in CANCELLABLE_STATUSES and not any(
        item.sale_status in DISPATCHED_STATUSES for item in items
    )


@transaction.atomic
def cancel_order(order_id, buyer):
    orders = Order.objects.filter(pk=order_id, user=buyer)
    # Só a primeira transição para cancelado pode repor o estoque.
    if not orders.filter(status__in=CANCELLABLE_STATUSES).update(status=Order.Status.CANCELLED):
        if not orders.exists():
            raise Http404
        raise OrderCancellationError('Este pedido não pode mais ser cancelado.')

    items = OrderItem.objects.filter(order_id=order_id)
    if items.filter(fulfillment_status__in=DISPATCHED_STATUSES).exists():
        # Em pedidos de várias lojas, o primeiro envio já impede o cancelamento.
        raise OrderCancellationError('O pedido não pode ser cancelado porque uma peça já foi enviada.')

    for product_id, quantity in items.exclude(product_id=None).order_by('product_id').values_list('product_id', 'quantity'):
        Product.objects.filter(pk=product_id).update(stock=F('stock') + quantity)

    order = Order.objects.get(pk=order_id)
    for seller, seller_items in items_by_seller(items.select_related('product__seller')).items():
        notify(seller, f'O pedido {order.reference} foi cancelado pelo comprador ({pieces_text(seller_items)}). '
                       'O estoque já foi devolvido.', reverse('sales_list'))
