from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ProductForm
from .models import Product, UserProfile


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


# Listagem administrativa: não expõe dados de usuários a visitantes.


@staff_member_required
def user_list(request):
    users = get_user_model().objects.select_related("profile").order_by("first_name", "last_name", "pk")
    q = request.GET.get("q", "").strip()[:120]
    role = request.GET.get("role", "")
    status = request.GET.get("status", "")
    if q:
        users = users.filter(Q(first_name__icontains=q) | Q(last_name__icontains=q)
                             | Q(username__icontains=q) | Q(email__icontains=q)
                             | Q(profile__store_name__icontains=q))
    if role in UserProfile.Role.values:
        users = users.filter(profile__role=role)
    elif role == "unassigned":
        users = users.filter(profile__isnull=True)
    if status in ["active", "inactive"]:
        users = users.filter(is_active=(status == "active"))
    total = users.count()
    page = Paginator(users, 10).get_page(request.GET.get("page"))
    query = request.GET.copy()
    query.pop("page", None)
    return render(request, "core/users/list.html", {
        "page_obj": page, "total": total, "q": q, "role": role, "status": status,
        "roles": UserProfile.Role.choices, "filter_query": query.urlencode(),
    })
