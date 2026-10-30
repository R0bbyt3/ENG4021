from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .models import Favorite, Product


def _redirect_back(request):
    """Volta para a página de onde o usuário veio (só dentro do próprio site)."""
    target = request.POST.get('next', '')
    if target and url_has_allowed_host_and_scheme(
        target, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return redirect(target)
    return redirect(reverse('favorites'))


@login_required
def favorites_list(request):
    favorites = (
        Favorite.objects.filter(user=request.user)
        .select_related('product', 'product__category')
        .order_by('-created_at', '-pk')
    )
    return render(request, 'core/favorites/list.html', {'favorites': favorites})


@login_required
@require_POST
def favorite_add(request, product_id):
    # Só peças ativas na vitrine podem ser favoritadas.
    product = get_object_or_404(Product, pk=product_id, is_active=True)
    _, created = Favorite.objects.get_or_create(user=request.user, product=product)
    if created:
        messages.success(request, f'"{product.name}" foi adicionada aos seus favoritos.')
    else:
        messages.info(request, f'"{product.name}" já estava nos seus favoritos.')
    return _redirect_back(request)


@login_required
@require_POST
def favorite_remove(request, product_id):
    # Remove só o favorito do próprio usuário; se já não existir, nada acontece.
    deleted, _ = Favorite.objects.filter(user=request.user, product_id=product_id).delete()
    if deleted:
        messages.success(request, 'Peça removida dos seus favoritos.')
    return _redirect_back(request)
