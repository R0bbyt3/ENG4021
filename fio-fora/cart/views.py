"""Carrinho do comprador.

Regras principais:
- só contas de comprador usam o carrinho, e cada uma mexe só no próprio (itens de outros usuários dão 404);
- disponibilidade (peça ativa) e estoque são validados no servidor a cada ação;
- preços, subtotais e total vêm sempre do banco: o navegador envia apenas a quantidade.
"""
from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.decorators import buyer_required
from products.models import Product

from .models import Cart, CartItem
from .services import MAX_QUANTITY, build_cart_summary, parse_quantity, unavailable_reason


@buyer_required
def cart_page(request):
    return render(request, 'cart/cart.html', build_cart_summary(request.user))


@require_POST
@buyer_required
def cart_add(request, product_id):
    quantity = parse_quantity(request.POST.get('quantity', '1'))
    if quantity is None:
        messages.error(request, f'Informe uma quantidade inteira entre 1 e {MAX_QUANTITY}.')
        return redirect('cart')

    with transaction.atomic():
        # Travar o carrinho do usuário evita que dois cliques seguidos furem o estoque.
        cart, _ = Cart.objects.select_for_update().get_or_create(user=request.user)
        product = get_object_or_404(Product.objects.select_for_update(), pk=product_id)
        item = CartItem.objects.filter(cart=cart, product=product).first()
        current = item.quantity if item else 0

        if product.seller_id == request.user.pk:
            messages.error(request, 'Você não pode comprar a sua própria peça.')
        elif (problem := unavailable_reason(product, current + quantity)) is not None:
            if current and product.is_active and product.stock >= 1:
                problem += f' Você já tem {current} no carrinho.'
            messages.error(request, f'Não foi possível adicionar “{product.name}”. {problem}')
        else:
            if item:
                item.quantity = current + quantity
                item.save(update_fields=['quantity'])
            else:
                CartItem.objects.create(cart=cart, product=product, quantity=quantity)
            messages.success(request, f'“{product.name}” foi adicionada ao carrinho.')
    return redirect('cart')


@require_POST
@buyer_required
def cart_update_item(request, item_id):
    quantity = parse_quantity(request.POST.get('quantity'))
    with transaction.atomic():
        Cart.objects.select_for_update().filter(user=request.user).first()
        # Filtrar por cart__user impede mexer no carrinho de outra pessoa (404).
        item = get_object_or_404(
            CartItem.objects.select_for_update().select_related('product'),
            pk=item_id, cart__user=request.user)
        if quantity is None:
            messages.error(request, f'Informe uma quantidade inteira entre 1 e {MAX_QUANTITY}. '
                                    'Para tirar a peça do carrinho, use “Remover”.')
        elif (problem := unavailable_reason(item.product, quantity)) is not None:
            messages.error(request, f'Quantidade não alterada para “{item.product.name}”. {problem}')
        else:
            item.quantity = quantity
            item.save(update_fields=['quantity'])
            messages.success(request, f'Quantidade de “{item.product.name}” atualizada.')
    return redirect('cart')


@require_POST
@buyer_required
def cart_remove_item(request, item_id):
    with transaction.atomic():
        Cart.objects.select_for_update().filter(user=request.user).first()
        item = get_object_or_404(CartItem.objects.select_related('product'), pk=item_id, cart__user=request.user)
        name = item.product.name
        item.delete()
    messages.success(request, f'“{name}” foi removida do carrinho.')
    return redirect('cart')
