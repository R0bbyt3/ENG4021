"""Carrinho do comprador (Sprint 7).

Regras principais:
- só o comprador autenticado mexe no próprio carrinho (itens de outros usuários dão 404);
- disponibilidade (peça ativa) e estoque são validados no servidor a cada ação;
- preços, subtotais e total vêm sempre do banco: o navegador envia apenas a quantidade.
"""
from decimal import Decimal
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import Cart, CartItem, Product, UserProfile

MAX_QUANTITY = 99
CENTS = Decimal('0.01')


def buyer_required(view):
    """Compradores (e a equipe, para testes) podem comprar; vendedores e marcas não."""
    @login_required
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        profile = getattr(request.user, 'profile', None)
        if not request.user.is_staff and (profile is None or profile.role != UserProfile.Role.BUYER):
            raise PermissionDenied('O carrinho é exclusivo para contas de comprador.')
        return view(request, *args, **kwargs)
    return wrapped


def parse_quantity(raw):
    """Converte o texto enviado em inteiro de 1 a MAX_QUANTITY; devolve None se inválido."""
    try:
        value = int(str(raw).strip())
    except (TypeError, ValueError):
        return None
    return value if 1 <= value <= MAX_QUANTITY else None


def unavailable_reason(product, quantity):
    """Motivo pelo qual `quantity` unidades da peça não podem ser compradas (ou None)."""
    if not product.is_active:
        return 'Esta peça não está mais à venda.'
    if product.stock < 1:
        return 'Peça esgotada.'
    if quantity > product.stock:
        unit = 'unidade' if product.stock == 1 else 'unidades'
        return f'Só há {product.stock} {unit} em estoque.'
    return None


def build_cart_summary(user):
    """Monta as linhas do carrinho e o total, calculados a partir do banco."""
    cart = Cart.objects.filter(user=user).first()
    lines, total, pieces = [], Decimal('0.00'), 0
    if cart is not None:
        items = cart.items.select_related('product').order_by('pk')
        for item in items:
            product = item.product
            problem = unavailable_reason(product, item.quantity)
            subtotal = (product.price * item.quantity).quantize(CENTS)
            lines.append({
                'item': item,
                'product': product,
                'subtotal': subtotal,
                'problem': problem,
                'max_quantity': max(1, min(product.stock, MAX_QUANTITY)),
            })
            # Itens indisponíveis ficam visíveis (para o comprador ajustar ou remover),
            # mas não entram no total.
            if problem is None:
                total += subtotal
                pieces += item.quantity
    return {
        'lines': lines,
        'total': total,
        'pieces': pieces,
        'has_unavailable': any(line['problem'] for line in lines),
    }


@login_required
def cart_page(request):
    return render(request, 'core/cart/cart.html', build_cart_summary(request.user))


@require_POST
@buyer_required
def cart_add(request, product_id):
    quantity = parse_quantity(request.POST.get('quantity', '1'))
    if quantity is None:
        messages.error(request, f'Informe uma quantidade inteira entre 1 e {MAX_QUANTITY}.')
        return redirect('cart_page')

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
    return redirect('cart_page')


@require_POST
@login_required
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
    return redirect('cart_page')


@require_POST
@login_required
def cart_remove_item(request, item_id):
    with transaction.atomic():
        Cart.objects.select_for_update().filter(user=request.user).first()
        item = get_object_or_404(CartItem.objects.select_related('product'), pk=item_id, cart__user=request.user)
        name = item.product.name
        item.delete()
    messages.success(request, f'“{name}” foi removida do carrinho.')
    return redirect('cart_page')
