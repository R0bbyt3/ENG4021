from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.shortcuts import redirect, render

from .seller_forms import DiscountSimulationForm, ProductRegistrationForm
from .models import Product, UserProfile


def seller_required(view):
    @login_required
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        profile = getattr(request.user, 'profile', None)
        if not request.user.is_staff and (
            profile is None or profile.role not in (UserProfile.Role.SELLER, UserProfile.Role.BRAND)
        ):
            raise PermissionDenied('Esta área é exclusiva para vendedores e marcas.')
        return view(request, *args, **kwargs)
    return wrapped


@seller_required
def product_create(request):
    form = ProductRegistrationForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        product = form.save(commit=False)
        product.seller = request.user
        product.save()
        form.save_defeito(product)
        messages.success(request, 'Peça cadastrada com sucesso.')
        return redirect('my_products')
    return render(request, 'core/seller/product_form.html', {'form': form, 'title': 'Cadastrar peça'})


@seller_required
def my_products(request):
    products = Product.objects.filter(seller=request.user).select_related('category', 'defeito').order_by('-created_at', '-pk')
    page = Paginator(products, 12).get_page(request.GET.get('page'))
    return render(request, 'core/seller/my_products.html', {'page_obj': page})


def discount_simulator(request):
    form = DiscountSimulationForm(request.POST if request.method == 'POST' else None)
    result = form.preview() if request.method == 'POST' and form.is_valid() else None
    return render(request, 'core/seller/discount_simulator.html', {'form': form, 'result': result})