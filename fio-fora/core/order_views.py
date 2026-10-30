from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods

from .cart_views import build_cart_summary, buyer_required
from .models import Order
from .order_services import CheckoutError, checkout_cart


@require_http_methods(['GET', 'POST'])
@buyer_required
def checkout(request):
    if request.method == 'POST':
        try:
            order = checkout_cart(request.user)
        except CheckoutError as error:
            messages.error(request, str(error))
            return redirect('cart_page')
        messages.success(request, 'Pedido confirmado! Sua compra demonstrativa foi registrada.')
        return redirect('order_detail', order_id=order.pk)

    summary = build_cart_summary(request.user)
    if not summary['lines']:
        messages.error(request, 'Seu carrinho está vazio.')
        return redirect('cart_page')
    return render(request, 'core/orders/checkout.html', summary)


@require_GET
@buyer_required
def order_list(request):
    orders = Order.objects.filter(user=request.user).prefetch_related('items').order_by('-created_at', '-pk')
    page = Paginator(orders, 10).get_page(request.GET.get('page'))
    return render(request, 'core/orders/list.html', {'page_obj': page})


@require_GET
@buyer_required
def order_detail(request, order_id):
    order = get_object_or_404(
        Order.objects.prefetch_related('items'), pk=order_id, user=request.user,
    )
    return render(request, 'core/orders/detail.html', {'order': order})
