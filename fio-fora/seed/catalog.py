"""Bloco 2: categorias, peças, defeitos e fotos.

As fotos ficam em seed/images/: <foto>.jpg (a peça) e <foto>-defeito.jpg (o
close do defeito). Para trocar por uma foto real, substitua o arquivo
mantendo o mesmo nome.
"""
from decimal import Decimal
from pathlib import Path

from django.core.files import File

from products.models import Category, Defeito, Product, ProductImage

IMAGES = Path(__file__).resolve().parent / 'images'

CATEGORIES = [
    ('Camisetas', 'camisetas'),
    ('Camisas', 'camisas'),
    ('Calças', 'calcas'),
    ('Vestidos', 'vestidos'),
    ('Saias', 'saias'),
    ('Jaquetas', 'jaquetas'),
]

# defeito = (tipo, localização, extensão), cada um de 1 a 3 (ver products/models.py).
PRODUCTS = [
    {'sku': 'FF-SEED-001', 'seller': 'fabio@fiofora.com', 'category': 'camisetas',
     'name': 'Camiseta de algodão orgânico', 'photo': 'camiseta-algodao',
     'description': 'Camiseta verde-sálvia de algodão orgânico. A costura interna da barra '
                    'tem um trecho solto de 2 cm, que não aparece com a peça vestida.',
     'size': 'M', 'original_price': '120.00', 'defeito': (1, 1, 1), 'measure': '2.00',
     'measurements': 'Busto 100 cm · Comprimento 70 cm'},
    {'sku': 'FF-SEED-002', 'seller': 'fabio@fiofora.com', 'category': 'camisas',
     'name': 'Camisa de linho manga longa', 'photo': 'camisa-linho',
     'description': 'Camisa de linho cru. Falta um botão da frente; o botão reserva vem junto '
                    'e é fácil de pregar.',
     'size': 'G', 'original_price': '260.00', 'defeito': (2, 2, 1), 'measure': '1.00',
     'measurements': 'Busto 112 cm · Comprimento 76 cm'},
    {'sku': 'FF-SEED-003', 'seller': 'gabriela@fiofora.com', 'category': 'vestidos',
     'name': 'Vestido midi estampado', 'photo': 'vestido-estampado',
     'description': 'Vestido midi de viscose com estampa floral. Tem uma mancha clara de '
                    'tingimento na saia, que se confunde com a estampa.',
     'size': 'P', 'original_price': '320.00', 'defeito': (1, 2, 2), 'measure': '5.00',
     'measurements': 'Busto 86 cm · Comprimento 115 cm'},
    {'sku': 'FF-SEED-004', 'seller': 'gabriela@fiofora.com', 'category': 'saias',
     'name': 'Saia plissada terracota', 'photo': 'saia-plissada',
     'description': 'Saia plissada de cintura alta. O zíper lateral emperra no meio do '
                    'caminho; a troca do zíper resolve.',
     'size': 'M', 'original_price': '180.00', 'defeito': (2, 1, 2), 'measure': '4.00',
     'measurements': 'Cintura 70 cm · Comprimento 68 cm'},
    {'sku': 'FF-SEED-005', 'seller': 'diego@fiofora.com', 'category': 'calcas',
     'name': 'Calça jeans reta', 'photo': 'calca-jeans',
     'description': 'Jeans azul médio de corte reto. A lavagem deixou uma área desbotada na '
                    'frente da coxa esquerda.',
     'size': '40', 'original_price': '220.00', 'defeito': (1, 3, 2), 'measure': '8.00',
     'measurements': 'Cintura 80 cm · Comprimento 104 cm'},
    {'sku': 'FF-SEED-006', 'seller': 'diego@fiofora.com', 'category': 'jaquetas',
     'name': 'Jaqueta jeans com bolsos', 'photo': 'jaqueta-jeans',
     'description': 'Jaqueta jeans clássica. O forro interno rasgou perto do bolso e não '
                    'tem conserto; aparece quando a jaqueta está aberta.',
     'size': 'G', 'original_price': '300.00', 'defeito': (3, 2, 2), 'measure': '7.00',
     'measurements': 'Busto 116 cm · Comprimento 66 cm'},
    {'sku': 'FF-SEED-007', 'seller': 'julia@fiofora.com', 'category': 'camisetas',
     'name': 'Camiseta listrada', 'photo': 'camiseta-listrada',
     'description': 'Camiseta navy com listras brancas. Tem um fio puxado nas costas, '
                    'perto da gola.',
     'size': 'P', 'original_price': '70.00', 'defeito': (1, 1, 2), 'measure': '4.00',
     'measurements': 'Busto 92 cm · Comprimento 64 cm'},
    {'sku': 'FF-SEED-008', 'seller': 'julia@fiofora.com', 'category': 'calcas',
     'name': 'Calça de alfaiataria', 'photo': 'calca-alfaiataria',
     'description': 'Calça de alfaiataria grafite. A barra da frente descosturou; '
                    'basta uma costureira refazer.',
     'size': '38', 'original_price': '240.00', 'defeito': (2, 3, 1), 'measure': '6.00',
     'measurements': 'Cintura 72 cm · Comprimento 100 cm'},
    # Esgotada: mostra o aviso "Peça esgotada" na página da peça.
    {'sku': 'FF-SEED-009', 'seller': 'julia@fiofora.com', 'category': 'vestidos',
     'name': 'Vestido de malha vinho', 'photo': 'vestido-malha',
     'description': 'Vestido de malha canelada. Tem um furo pequeno na frente, visível e '
                    'sem conserto invisível.',
     'size': 'M', 'original_price': '150.00', 'defeito': (3, 3, 2), 'measure': '1.50',
     'measurements': 'Busto 88 cm · Comprimento 105 cm', 'stock': 0},
    # Pausada: só aparece em "Minhas peças" do Diego, não na vitrine.
    {'sku': 'FF-SEED-010', 'seller': 'diego@fiofora.com', 'category': 'camisas',
     'name': 'Camisa social azul-clara', 'photo': 'camisa-social',
     'description': 'Camisa social de algodão. A costura da manga abriu 3 cm por dentro.',
     'size': 'M', 'original_price': '160.00', 'defeito': (2, 1, 1), 'measure': '3.00',
     'measurements': 'Busto 104 cm · Comprimento 74 cm', 'is_active': False},
]


def create_catalog(users):
    """Cria categorias e peças e devolve um dicionário {sku: peça}."""
    categories = {}
    for name, slug in CATEGORIES:
        categories[slug], _ = Category.objects.get_or_create(slug=slug, defaults={'name': name})

    products = {}
    for data in PRODUCTS:
        product = create_product(data, users[data['seller']], categories[data['category']])
        add_photos(product, data)
        products[data['sku']] = product
    return products


def create_product(data, seller, category):
    tipo, localizacao, extensao = data['defeito']
    # O preço final vem da fórmula do model, como no cadastro feito pelo site.
    draft = Product(original_price=Decimal(data['original_price']))
    draft.defeito = Defeito(tipo=tipo, localizacao=localizacao, extensao=extensao)

    product, _ = Product.objects.get_or_create(sku=data['sku'], defaults={
        'seller': seller,
        'category': category,
        'brand': seller.profile.store_name,
        'name': data['name'],
        'description': data['description'],
        'size': data['size'],
        'measurements': data['measurements'],
        'condition': 'Nova com defeito',
        'original_price': draft.original_price,
        'price': draft.suggested_price,
        'stock': data.get('stock', 3),
        'is_active': data.get('is_active', True),
        'defect_measure_cm': Decimal(data['measure']),
        'visible_when_worn': localizacao == 3,
    })
    Defeito.objects.get_or_create(product=product, defaults={
        'tipo': tipo, 'localizacao': localizacao, 'extensao': extensao})
    return product


def add_photos(product, data):
    """Uma foto da peça e uma do defeito. Não repete se a peça já tem fotos."""
    if product.images.exists():
        return
    photos = [
        (f"{data['photo']}.jpg", f"{data['name']}: foto da peça inteira", False),
        (f"{data['photo']}-defeito.jpg", f"{data['name']}: close do defeito", True),
    ]
    for filename, alt_text, is_defect in photos:
        with open(IMAGES / filename, 'rb') as file:
            photo = ProductImage(product=product, alt_text=alt_text, is_defect=is_defect)
            photo.image.save(filename, File(file), save=False)
            photo.save()
