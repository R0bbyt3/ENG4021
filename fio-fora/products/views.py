from decimal import Decimal
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import seller_required
from accounts.models import UserProfile
from cart.services import purchase_summary
from favorites.models import mark_favorites
from reviews.services import product_reviews, rating_summary, store_reviews

from .forms import DiscountSimulationForm, ProductForm
from .models import (
    FAIXAS_SEVERIDADE, LIMITE_LEVE, LIMITE_MODERADA, PESO_EXTENSAO, PESO_LOCALIZACAO, PESO_TIPO,
    Category, Defeito, Product, desconto_sugerido,
)


def faq(request):
    """Perguntas frequentes: página pública, só texto (sem consulta ao banco)."""
    return render(request, 'products/faq.html')


def careers(request):
    """Trabalhe conosco: página pública e só de texto; as vagas são fictícias."""
    openings = [
        {'name': 'Curadoria de peças',
         'text': 'Conferir fotos e descrições dos anúncios para que o defeito esteja sempre claro.'},
        {'name': 'Atendimento',
         'text': 'Ajudar compradores e vendedores com dúvidas sobre pedidos, trocas e cadastro.'},
        {'name': 'Desenvolvimento',
         'text': 'Criar e melhorar as telas e as regras do site, com testes e documentação.'},
        {'name': 'Comunicação',
         'text': 'Escrever e mostrar a proposta da FioFora para quem ainda não conhece.'},
    ]
    return render(request, 'products/careers.html', {'openings': openings})


def contact(request):
    """Contato: página pública e só de texto, sem formulário nem e-mail inventado."""
    return render(request, 'products/contact.html')


def terms(request):
    """Termos de uso: página pública e só de texto, com regras de exemplo do protótipo."""
    return render(request, 'products/terms.html')


def privacy(request):
    """Política de privacidade: página pública e só de texto, sem consulta ao banco."""
    return render(request, 'products/privacy.html')


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

    selected = {'marca': brand, 'categoria': category, 'tamanho': size, 'q': query,
                'ordem': ordering, 'faixa': band}

    def shortcut_links(key, options):
        """Atalhos de um filtro que preservam os outros controles.

        O número da página fica de fora de propósito: trocar de categoria ou de
        faixa muda o resultado, então a leitura recomeça da primeira página.
        """
        links = []
        for value, label in options:
            params = {name: chosen for name, chosen in selected.items() if chosen and name != key}
            if value:
                params[key] = value
            links.append({'value': value, 'label': label, 'query': urlencode(params)})
        return links

    band_links = shortcut_links('faixa', [('', 'Todas'), *FAIXAS_SEVERIDADE])
    category_links = shortcut_links(
        'categoria', [('', 'Todas'), *[(item.slug, item.name) for item in categories]])
    # A paginação mantém busca, filtros e ordem; só o page muda de uma página para outra.
    filters_query = urlencode({name: chosen for name, chosen in selected.items() if chosen})
    page = Paginator(products, 12).get_page(request.GET.get('page'))

    return render(request, 'products/home.html', {
        'products': list(page),
        'page_obj': page,
        'filters_query': filters_query,
        'result_count': page.paginator.count,
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
        'category_links': category_links,
        'active_band': band,
    })


def store_list(request):
    """Aba “Marcas”: quem tem peça na vitrine, em ordem alfabética.

    Só aparece quem tem pelo menos uma peça ativa — uma lista de lojas vazias
    não ajuda ninguém a comprar.
    """
    stores = (get_user_model().objects
              .filter(products__is_active=True, profile__isnull=False)
              .annotate(product_count=Count('products', filter=Q(products__is_active=True), distinct=True))
              .select_related('profile')
              .order_by('profile__store_name', 'first_name', 'username'))
    return render(request, 'products/store_list.html', {'stores': stores})


def store_detail(request, seller_id):
    """Página pública de uma loja ou marca, com a nota da loja e as peças dela."""
    # Só contas de vendedor ou marca têm página: a de um comprador mostraria o
    # nome e a cidade dele para qualquer pessoa.
    seller = get_object_or_404(get_user_model().objects.select_related('profile'), pk=seller_id,
                               profile__role__in=[UserProfile.Role.SELLER, UserProfile.Role.BRAND])
    # Só peças ativas: a página é pública e espelha o que está na vitrine.
    products = (Product.objects.filter(seller=seller, is_active=True)
                .select_related('defeito', 'category').prefetch_related('images')
                .order_by('-created_at', '-pk'))
    products = mark_favorites(products, request.user)
    page = Paginator(products, 12).get_page(request.GET.get('page'))
    return render(request, 'products/store_detail.html', {
        'seller': seller,
        'page_obj': page,
        'rating': rating_summary(store_reviews(seller)),
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
    # Faixas e descontos vêm das mesmas constantes do model, para a página nunca desatualizar.
    return render(request, 'products/about.html', {
        'criteria': criteria,
        'limit_light': LIMITE_LEVE,
        'limit_moderate': LIMITE_MODERADA,
        'discount_min': desconto_sugerido(Decimal(1)),
        'discount_max': desconto_sugerido(Decimal(3)),
    })


def product_detail(request, product_id):
    products = (Product.objects.filter(is_active=True)
                .select_related('defeito', 'category', 'seller__profile').prefetch_related('images'))
    product = get_object_or_404(mark_favorites(products, request.user), id=product_id)
    reviews = product_reviews(product)
    return render(request, 'products/detail.html', {
        'product': product,
        'payment': purchase_summary(product.price),
        'rating': rating_summary(reviews),
        'reviews': reviews[:10],  # só as mais recentes
        'store_rating': rating_summary(store_reviews(product.seller)) if product.seller else None,
        # Leva os dados do defeito para o simulador já preenchido.
        'simulator_query': DiscountSimulationForm.query_for(product),
    })


def discount_simulator(request):
    """Simulador de desconto, com ou sem os valores de uma peça na URL."""
    if request.method == 'POST':
        form = DiscountSimulationForm(request.POST)
    else:
        form = DiscountSimulationForm.from_query(request.GET)
    result = form.preview() if form.is_bound and form.is_valid() else None
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
