"""Quem pode fazer o quê. Usado pelas views (decorators) e pelos templates (context processor)."""
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect

from .models import UserProfile

# Mensagem única para vendedor ou marca que tenta usar uma área de comprador.
BUYER_ONLY_MESSAGE = ('Carrinho, favoritos e compras são só para contas de comprador. '
                      'Vendedores e marcas podem ver as peças, mas não comprar nem favoritar.')


def has_role(user, *roles):
    """A equipe (staff) passa em qualquer verificação, para facilitar os testes manuais."""
    if not user.is_authenticated:
        return False
    if user.is_staff:
        return True
    profile = getattr(user, 'profile', None)
    return profile is not None and profile.role in roles


def is_buyer(user):
    return has_role(user, UserProfile.Role.BUYER)


def is_seller(user):
    return has_role(user, UserProfile.Role.SELLER, UserProfile.Role.BRAND)


def role_required(check, message, redirect_to=None):
    """Exige login e o tipo de conta certo.

    Sem redirect_to, quem não tem o tipo de conta recebe acesso negado (403).
    Com redirect_to, volta para essa página e vê a mensagem, em vez de um erro.
    """
    def decorator(view):
        @login_required
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            if not check(request.user):
                if redirect_to:
                    messages.error(request, message)
                    return redirect(redirect_to)
                raise PermissionDenied(message)
            return view(request, *args, **kwargs)
        return wrapped
    return decorator


# Vendedor que tenta comprar volta para a vitrine com a explicação, sem tela de erro.
buyer_required = role_required(is_buyer, BUYER_ONLY_MESSAGE, redirect_to='home')
seller_required = role_required(is_seller, 'Esta área é exclusiva para vendedores e marcas.')
