from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import seller_required
from favorites.models import mark_favorites
from reviews.services import product_reviews, rating_summary, store_reviews

from .forms import DiscountSimulationForm, ProductForm
from .models import (
    FAIXAS_SEVERIDADE, PESO_EXTENSAO, PESO_LOCALIZACAO, PESO_TIPO,
    Category, Defeito, Product,
)


def home(request):
    """Todos os controles da vitrine compartilham a mesma URL por GET."""
    band = request.GET.get('faixa', '').strip()
    if band not in dict(FAIXAS_SEVERIDADE):
        band = ''  # faixa desconhecida: mostra todas as peças
    brand = request.GET.get('marca', '').strip()
    category = request.GET.get('categoria', '').strip()
    size = request.GET.get('tamanho', '').strip()
    query = request.GET.get('q', '').strip()
    ordering = request.GET.get('ordem', '')
    if ordering not in ('preco', 'desconto'):
        ordering = ''

    active_products = Product.objects.filter(is_active=True)
    # Opções vêm do catálogo ativo inteiro, não apenas do resultado filtrado.
    brands = list(active_products.exclude(brand='').order_by('brand')
                  .values_list('brand', flat=True).distinct())
    sizes = list(active_products.exclude(size='').order_by('size')
                 .values_list('size', flat=True).distinct())
    categories = list(Category.objects.filter(products__is_active=True).distinct())
    products = active_products.select_related('defeito', 'category').prefetch_related('images')
    if band:
        products = products.with_severity_band(band)
    if brand:
        products = products.filter(brand=brand)
    if category:
        products = products.filter(category__slug=category)
    if size:
        products = products.filter(size=size)
    if query:
        products = products.filter(Q(name__icontains=query) | Q(brand__icontains=query))

    products = list(mark_favorites(products.order_by('-created_at', '-pk'), request.user))
    if ordering == 'preco':
        products.sort(key=lambda product: (product.price, -product.pk))
    elif ordering == 'desconto':
        # Reutiliza o desconto real exibido no card, sem copiar sua fórmula.
        products.sort(key=lambda product: (-(product.discount_percent or 0), product.price, -product.pk))

    selected = {'marca': brand, 'categoria': category, 'tamanho': size, 'q': query, 'ordem': ordering}
    filter_query = request.GET.copy()
    filter_query.clear()
    filter_query.update({key: value for key, value in selected.items() if value})
    band_links = []
    for value, label in [('', 'Todas'), *FAIXAS_SEVERIDADE]:
        params = filter_query.copy()
        if value:
            params['faixa'] = value
        band_links.append({'value': value, 'label': label, 'query': params.urlencode()})

    return render(request, 'products/home.html', {
        'products': products,
        'result_count': len(products),
        'brands': brands,
        'categories': categories,
        'sizes': sizes,
        'selected_brand': brand,
        'selected_category': category,
        'selected_size': size,
        'search_query': query,
        'ordering': ordering,
        'unknown_brand': bool(brand and brand not in brands),
        'unknown_category': bool(category and category not in [item.slug for item in categories]),
        'unknown_size': bool(size and size not in sizes),
        'has_filters': bool(band or brand or category or size or query),
        'has_controls': bool(band or brand or category or size or query or ordering),
        'band_links': band_links,
        'active_band': band,
    })


def about(request):
    criteria = [
        {'name': 'Tipo', 'weight': PESO_TIPO, 'levels': zip(Defeito.TIPO_CHOICES, (
            'Afeta a aparência da peça, como uma pequena mancha ou falha de acabamento.',
            'Afeta uma função, mas admite reparo, como um botão faltando.',
            'Afeta uma função e não admite reparo, segundo a descrição do vendedor.',
        ))},
        {'name': 'Localização', 'weight': PESO_LOCALIZACAO, 'levels': zip(Defeito.LOCALIZACAO_CHOICES, (
            'Fica em uma parte pouco aparente, como o forro interno.',
            'Pode aparecer conforme o movimento ou a posição da peça.',
            'Fica em uma parte aparente da peça, como a região frontal.',
        ))},
        {'name': 'Extensão', 'weight': PESO_EXTENSAO, 'levels': zip(Defeito.EXTENSAO_CHOICES, (
            'Defeito com medida de até 2 cm.',
            'Defeito com medida maior que 2 cm e até 10 cm.',
            'Defeito com medida acima de 10 cm.',
        ))},
    ]
    return render(request, 'products/about.html', {'criteria': criteria})


def product_detail(request, product_id):
    products = (Product.objects.filter(is_active=True)
                .select_related('defeito', 'category', 'seller__profile').prefetch_related('images'))
    product = get_object_or_404(mark_favorites(products, request.user), id=product_id)
    reviews = product_reviews(product)
    return render(request, 'products/detail.html', {
        'product': product,
        'rating': rating_summary(reviews),
        'reviews': reviews[:10],  # só as mais recentes
        'store_rating': rating_summary(store_reviews(product.seller)) if product.seller else None,
    })


def discount_simulator(request):
    form = DiscountSimulationForm(request.POST if request.method == 'POST' else None)
    result = form.preview() if request.method == 'POST' and form.is_valid() else None
    return render(request, 'products/discount_simulator.html', {'form': form, 'result': result})


@seller_required
def my_products(request):
    products = (Product.objects.filter(seller=request.user)
                .select_related('defeito').prefetch_related('images').order_by('-created_at', '-pk'))
    page = Paginator(products, 12).get_page(request.GET.get('page'))
    return render(request, 'products/my_products.html', {'page_obj': page})


@seller_required
def product_create(request):
    return product_form(request, Product(seller=request.user), 'Cadastrar peça', 'Peça cadastrada com sucesso.')


@seller_required
def product_update(request, product_id):
    product = get_object_or_404(Product, pk=product_id, seller=request.user)
    return product_form(request, product, 'Editar peça', 'Peça atualizada com sucesso.')


@seller_required
def product_delete(request, product_id):
    product = get_object_or_404(Product, pk=product_id, seller=request.user)
    if request.method == 'POST':
        product.delete()
        messages.success(request, f'“{product.name}” foi removida.')
        return redirect('my_products')
    return render(request, 'products/product_confirm_delete.html', {'product': product})


def product_form(request, product, title, success_message):
    """Cadastro e edição usam o mesmo formulário e o mesmo template."""
    form = ProductForm(request.POST if request.method == 'POST' else None,
                       request.FILES if request.method == 'POST' else None, instance=product)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, success_message)
        return redirect('my_products')
    return render(request, 'products/product_form.html', {'form': form, 'title': title})
