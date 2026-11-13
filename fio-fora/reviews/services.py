"""Regras de avaliação usadas por mais de um app (pedidos, peça e vendedor)."""
from decimal import Decimal, ROUND_HALF_UP

from django.db.models import Avg, Count

from orders.models import Order

from .forms import ReviewForm
from .models import Review


AWAITING_DELIVERY = 'Você poderá avaliar esta peça quando a entrega for confirmada.'


def review_block_reason(item):
    """Motivo pelo qual o item não pode ser avaliado, ou None se pode."""
    if item.order.status == Order.Status.CANCELLED:
        return 'Pedidos cancelados não podem ser avaliados.'
    if item.product_id is None:
        return 'Esta peça não existe mais e não pode ser avaliada.'
    # Só dá para opinar sobre a peça depois de recebê-la (vale para avaliar e para editar).
    if item.sale_status != Order.Status.DELIVERED:
        return AWAITING_DELIVERY
    return None


def attach_review_forms(items):
    """Anexa a cada item do pedido a avaliação já feita (ou None) e o formulário para preenchê-la."""
    reviews = {r.order_item_id: r for r in Review.objects.filter(order_item__in=items)}
    for item in items:
        item.review_done = reviews.get(item.pk)
        reason = review_block_reason(item)
        item.can_review = reason is None
        # Antes da entrega a tela explica quando vai dar para avaliar, em vez de não mostrar nada.
        item.awaiting_delivery = reason == AWAITING_DELIVERY
        item.review_form = ReviewForm(instance=item.review_done, auto_id=f'review_{item.pk}_%s')
    return items


def rating_summary(reviews):
    """Nota média (uma casa decimal) e quantidade de avaliações de um conjunto de avaliações."""
    data = reviews.aggregate(average=Avg('rating'), count=Count('pk'))
    average = data['average']
    if average is not None:
        average = Decimal(average).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)
    return {'average': average, 'count': data['count']}


def product_reviews(product):
    return Review.objects.filter(order_item__product=product).select_related('user')


def store_reviews(seller):
    """Avaliações de todas as peças do vendedor."""
    return Review.objects.filter(order_item__product__seller=seller)
