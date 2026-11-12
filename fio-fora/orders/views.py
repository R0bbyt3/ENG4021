from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods

from accounts.decorators import buyer_required
from cart.services import build_cart_summary
from reviews.services import attach_review_forms

from .forms import CheckoutAddressForm
from .models import Order
from .services import CheckoutError, checkout_cart, send_order_confirmation


@require_http_methods(['GET', 'POST'])
@buyer_required
def checkout(request):
    summary = build_cart_summary(request.user)
    if not summary['lines']:
        messages.error(request, 'Seu carrinho está vazio.')
        return redirect('cart')

    profile = getattr(request.user, 'profile', None)
    form = CheckoutAddressForm(request.POST if request.method == 'POST' else None, profile=profile)
    if request.method == 'POST' and form.is_valid():
        try:
            order = checkout_cart(request.user, form.address_data())
        except CheckoutError as error:
            messages.error(request, str(error))
            return redirect('cart')
        if form.cleaned_data['save_to_profile'] and profile is not None:
            for key, value in form.address_data().items():
                setattr(profile, f'address_{key}', value)
            profile.save()
        messages.success(request, 'Pedido confirmado! Sua compra demonstrativa foi registrada.')
        order_url = request.build_absolute_uri(reverse('order_detail', args=[order.pk]))
        if not send_order_confirmation(order, order_url):
            messages.warning(request, 'Não foi possível enviar o e-mail de confirmação, mas o pedido está salvo.')
        return redirect('order_detail', order_id=order.pk)

    return render(request, 'orders/checkout.html', {**summary, 'form': form})


@require_GET
@buyer_required
def order_list(request):
    orders = Order.objects.filter(user=request.user).prefetch_related('items').order_by('-created_at', '-pk')
    page = Paginator(orders, 10).get_page(request.GET.get('page'))
    return render(request, 'orders/list.html', {'page_obj': page})


@require_GET
@buyer_required
def order_detail(request, order_id):
    order = get_object_or_404(
        Order.objects.prefetch_related('items'), pk=order_id, user=request.user,
    )
    items = attach_review_forms(list(order.items.all()))
    return render(request, 'orders/detail.html', {'order': order, 'items': items})
