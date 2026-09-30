from django.shortcuts import get_object_or_404, redirect, render

from .forms import ProductForm
from .models import Product


def home(request):
    products = Product.objects.filter(is_active=True)
    return render(request, 'core/home.html', {'products': products})


def product_create(request):
    form = ProductForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('home')
    return render(request, 'core/product_form.html', {'form': form, 'title': 'Novo produto'})


def product_update(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    form = ProductForm(request.POST or None, instance=product)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('home')
    return render(request, 'core/product_form.html', {'form': form, 'title': 'Editar produto'})


def product_delete(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        product.delete()
        return redirect('home')
    return render(request, 'core/product_confirm_delete.html', {'product': product})


def login_page(request):
    if request.method == 'POST':
        return redirect('home')
    return render(request, 'core/login/login.html')


def password_reset_page(request):
    return render(request, 'core/login/password_reset.html', {'demo_notice': request.method == 'POST'})


def account_type_page(request):
    return render(request, 'core/login/account_type.html')


def buyer_register_page(request):
    if request.method == 'POST':
        return redirect('login_page')
    return render(request, 'core/login/buyer_register.html')


def seller_register_page(request):
    if request.method == 'POST':
        return redirect('login_page')
    return render(request, 'core/login/seller_register.html')


def brand_register_page(request):
    if request.method == 'POST':
        return redirect('login_page')
    return render(request, 'core/login/brand_register.html')
