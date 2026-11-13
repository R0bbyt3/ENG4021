import os
import shutil
import tempfile
from decimal import Decimal
from io import BytesIO
from itertools import product as combinations
from unittest.mock import PropertyMock, patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError
from django.db.models import ProtectedError
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from PIL import Image

from accounts.models import UserProfile
from cart.models import Cart, CartItem
from favorites.models import Favorite
from orders.models import Order, OrderItem
from reviews.models import Review

from . import services
from .forms import DiscountSimulationForm, ProductForm
from .models import (Category, Defeito, Product, ProductImage, severity_breakdown,
                     severidade)


# As fotos dos testes vão para uma pasta temporária, não para media/ do projeto.
MEDIA_DE_TESTE = tempfile.mkdtemp()


def tearDownModule():
    shutil.rmtree(MEDIA_DE_TESTE, ignore_errors=True)


def foto(largura=900, altura=1200, formato='JPEG', nome=None):
    """Gera um arquivo de imagem de verdade, em memória, para os testes de upload."""
    buffer = BytesIO()
    Image.new('RGB', (largura, altura), (150, 140, 120)).save(buffer, formato)
    extensao = {'JPEG': 'jpg', 'PNG': 'png', 'WEBP': 'webp', 'GIF': 'gif'}[formato]
    buffer.seek(0)
    return SimpleUploadedFile(nome or f'foto.{extensao}', buffer.read(), f'image/{extensao}')


@override_settings(MEDIA_ROOT=MEDIA_DE_TESTE)
class SellerWorkflowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.seller = get_user_model().objects.create_user(
            'seller@example.com', email='seller@example.com', password='Strong-test-524!'
        )
        UserProfile.objects.create(user=cls.seller, role='seller')
        cls.other = get_user_model().objects.create_user('other@example.com')
        UserProfile.objects.create(user=cls.other, role='seller')
        cls.buyer = get_user_model().objects.create_user('buyer@example.com')
        UserProfile.objects.create(user=cls.buyer, role='buyer')
        cls.brand = get_user_model().objects.create_user('brand@example.com')
        UserProfile.objects.create(user=cls.brand, role='brand')
        cls.piece = Product.objects.create(name='Peça privada', description='Detalhes',
            price=Decimal('85'), original_price=Decimal('100'), seller=cls.seller)
        cls.other_piece = Product.objects.create(name='Peça de outro vendedor', description='Detalhes',
            price=Decimal('50'), original_price=Decimal('100'), seller=cls.other)

    def data(self, **overrides):
        values = {'name': 'Camisa de linho', 'description': 'Pequena mancha na barra',
            'brand': 'Circular', 'original_price': '100.00', 'defect_type': '1',
            'defect_location': '3', 'defect_extent': '2', 'stock': '1', 'is_active': 'on',
            'defect_photo': foto()}
        values.update(overrides)
        return values

    def test_create_assigns_logged_seller_and_ignores_forged_price_and_owner(self):
        self.client.force_login(self.seller)
        response = self.client.post(reverse('product_create'), self.data(
            seller=self.other.pk, price='0.01', sku='FORGED'))
        self.assertRedirects(response, reverse('my_products'))
        saved = Product.objects.get(name='Camisa de linho')
        self.assertEqual(saved.seller, self.seller)
        self.assertEqual(saved.price, Decimal('70.00'))
        self.assertEqual(saved.price, saved.suggested_price)
        self.assertEqual(saved.severity_label, 'Moderada')
        self.assertIsNone(saved.sku)
        response = self.client.get(reverse('my_products'))
        self.assertContains(response, 'Camisa de linho')
        self.assertContains(response, reverse('product_update', args=[saved.pk]))
        self.assertNotContains(response, 'Peça de outro vendedor')

    def test_size_is_saved_in_uppercase_without_spaces(self):
        self.client.force_login(self.seller)
        self.client.post(reverse('product_create'), self.data(size=' gg '))
        self.assertEqual(Product.objects.get(name='Camisa de linho').size, 'GG')

    def test_invalid_or_empty_posts_never_create_products(self):
        self.client.force_login(self.seller)
        count = Product.objects.count()
        for data in [{}, self.data(original_price=''), self.data(original_price='0'),
                     self.data(original_price='-2'), self.data(defect_type='4'),
                     self.data(stock='0'), self.data(defect_measure_cm='-1'),
                     self.data(name=''), self.data(original_price='NaN')]:
            with self.subTest(data=data):
                response = self.client.post(reverse('product_create'), data)
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context['form'].errors)
                self.assertEqual(Product.objects.count(), count)

    def test_anonymous_and_buyers_cannot_enter_seller_area(self):
        routes = [('product_create', []), ('my_products', [])]
        for name, args in routes:
            url = reverse(name, args=args)
            self.assertEqual(self.client.get(url).status_code, 302)
            self.assertEqual(self.client.post(url, self.data()).status_code, 302)
        self.client.force_login(self.buyer)
        for name, args in routes:
            self.assertEqual(self.client.get(reverse(name, args=args)).status_code, 403)
            self.assertEqual(self.client.post(reverse(name, args=args), self.data()).status_code, 403)

    def test_brands_can_create_and_accounts_without_profiles_cannot(self):
        self.client.force_login(self.brand)
        self.assertRedirects(self.client.post(reverse('product_create'), self.data()), reverse('my_products'))
        self.assertEqual(Product.objects.get(name='Camisa de linho').seller, self.brand)
        no_profile = get_user_model().objects.create_user('no-profile')
        self.client.force_login(no_profile)
        self.assertEqual(self.client.get(reverse('my_products')).status_code, 403)

    def test_edit_recalculates_price_and_updates_the_same_defect(self):
        self.client.force_login(self.seller)
        self.client.post(reverse('product_create'), self.data())
        saved = Product.objects.get(name='Camisa de linho')
        url = reverse('product_update', args=[saved.pk])
        self.assertContains(self.client.get(url), 'value="Camisa de linho"')
        response = self.client.post(url, self.data(name='Camisa editada', defect_type='3', defect_location='3', defect_extent='3'))
        self.assertRedirects(response, reverse('my_products'))
        saved.refresh_from_db()
        self.assertEqual(saved.name, 'Camisa editada')
        self.assertEqual(saved.severity_label, 'Alta')
        self.assertEqual(saved.price, saved.suggested_price)
        self.assertEqual(Defeito.objects.filter(product=saved).count(), 1)

    def test_delete_asks_for_confirmation_and_removes_the_piece(self):
        self.client.force_login(self.seller)
        url = reverse('product_delete', args=[self.piece.pk])
        self.assertContains(self.client.get(url), 'Remover peça?')
        self.assertRedirects(self.client.post(url), reverse('my_products'))
        self.assertFalse(Product.objects.filter(pk=self.piece.pk).exists())

    def test_only_the_owner_can_edit_or_delete(self):
        for name in ['product_update', 'product_delete']:
            url = reverse(name, args=[self.other_piece.pk])
            self.assertEqual(self.client.get(url).status_code, 302)  # visitante vai para o login
            self.client.force_login(self.seller)
            self.assertEqual(self.client.get(url).status_code, 404)
            self.assertEqual(self.client.post(url, self.data()).status_code, 404)
            self.client.force_login(self.buyer)
            self.assertEqual(self.client.get(url).status_code, 403)
            self.client.logout()
        self.assertTrue(Product.objects.filter(pk=self.other_piece.pk).exists())

    def test_list_includes_inactive_and_paginates_only_own_pieces(self):
        self.client.force_login(self.seller)
        self.piece.is_active = False
        self.piece.save()
        response = self.client.get(reverse('my_products'))
        self.assertContains(response, 'Inativa')
        self.assertContains(response, 'Peça privada')
        self.assertNotContains(response, 'Peça de outro vendedor')
        Product.objects.bulk_create([Product(name=f'Minha peça {i}', description='Teste',
            price=10, seller=self.seller) for i in range(13)])
        response = self.client.get(reverse('my_products'), {'page': '2'})
        self.assertEqual(response.context['page_obj'].paginator.count, 14)
        self.assertEqual(len(response.context['page_obj']), 2)
        self.assertEqual(self.client.get(reverse('my_products'), {'page': 'invalid'}).status_code, 200)

    def test_empty_list_has_call_to_action(self):
        self.client.force_login(self.brand)
        self.assertContains(self.client.get(reverse('my_products')), 'Cadastrar primeira peça')

    def test_simulator_matches_model_and_saved_price_for_all_27_scores(self):
        self.client.force_login(self.seller)
        count = Product.objects.count()
        for scores in combinations(range(1, 4), repeat=3):
            data = self.data(defect_type=str(scores[0]), defect_location=str(scores[1]),
                defect_extent=str(scores[2]), original_price='123.45')
            with self.subTest(scores=scores):
                response = self.client.post(reverse('discount_simulator'), data)
                result = response.context['result']
                form = ProductForm(data, {'defect_photo': foto()})
                self.assertTrue(form.is_valid(), form.errors)
                piece = form.save(commit=False)
                self.assertEqual(result['severity'], piece.severity)
                self.assertEqual(result['severity_label'], piece.severity_label)
                self.assertEqual(result['discount'], piece.suggested_discount)
                self.assertEqual(result['final_price'], piece.price)
                self.assertEqual(piece.price, piece.suggested_price)
        self.assertEqual(Product.objects.count(), count)

    def test_preview_uses_model_properties_instead_of_copying_formula(self):
        with patch.object(Product, 'suggested_discount', new_callable=PropertyMock, return_value=40):
            response = self.client.post(reverse('discount_simulator'), self.data())
            self.assertEqual(response.context['result']['discount'], 40)
            self.assertEqual(response.context['result']['final_price'], Decimal('60'))

    def test_public_simulator_validates_inputs_and_does_not_write(self):
        self.assertEqual(self.client.get(reverse('discount_simulator')).status_code, 200)
        for data in [{}, self.data(original_price='-1'), self.data(defect_extent='9')]:
            response = self.client.post(reverse('discount_simulator'), data)
            self.assertIsNone(response.context['result'])
            self.assertTrue(response.context['form'].errors)
        response = self.client.post(reverse('discount_simulator'), self.data(
            original_price='0.01', defect_type='3', defect_location='3', defect_extent='3'))
        self.assertEqual(response.context['result']['final_price'], Decimal('0.01'))

    def test_csrf_is_required_for_create_and_simulate(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.seller)
        self.assertEqual(client.post(reverse('product_create'), self.data()).status_code, 403)
        self.assertEqual(client.post(reverse('discount_simulator'), self.data()).status_code, 403)


def criar_peca(nome, tipo=1, localizacao=1, extensao=1, **campos):
    campos.setdefault('price', Decimal('80'))
    peca = Product.objects.create(name=nome, description='Fio puxado na barra', **campos)
    Defeito.objects.create(product=peca, tipo=tipo, localizacao=localizacao, extensao=extensao)
    return peca


class FiltroSeveridadeTests(TestCase):
    def setUp(self):
        self.leve = criar_peca('Camisa leve', 1, 1, 1)            # 1,00
        self.moderada = criar_peca('Calça moderada', 2, 2, 2)     # 2,00
        self.alta = criar_peca('Vestido alto', 3, 3, 3)           # 3,00
        self.sem_defeito = Product.objects.create(name='Saia sem ficha', description='x', price=Decimal('50'))

    def nomes(self, faixa=None):
        url = reverse('home') + (f'?faixa={faixa}' if faixa else '')
        return {p.name for p in self.client.get(url).context['products']}

    def test_sem_filtro_mostra_todas_as_pecas_ativas(self):
        self.assertEqual(self.nomes(), {'Camisa leve', 'Calça moderada', 'Vestido alto', 'Saia sem ficha'})

    def test_cada_faixa_mostra_so_as_suas_pecas(self):
        self.assertEqual(self.nomes('leve'), {'Camisa leve'})
        self.assertEqual(self.nomes('moderada'), {'Calça moderada'})
        self.assertEqual(self.nomes('alta'), {'Vestido alto'})

    def test_faixa_desconhecida_mostra_todas(self):
        self.assertEqual(len(self.nomes('qualquer')), 4)

    def test_filtro_no_banco_concorda_com_o_model_em_todas_as_27_notas(self):
        Product.objects.all().delete()
        for tipo, local, extensao in combinations((1, 2, 3), repeat=3):
            criar_peca(f'{tipo}{local}{extensao}', tipo, local, extensao)
        for faixa in ('leve', 'moderada', 'alta'):
            filtradas = Product.objects.with_severity_band(faixa)
            self.assertTrue(filtradas.exists())
            for peca in filtradas:
                self.assertEqual(peca.severity_band, faixa)
        self.assertEqual(sum(Product.objects.with_severity_band(f).count() for f in ('leve', 'moderada', 'alta')), 27)

    def test_limites_entram_na_faixa_de_baixo(self):
        Product.objects.all().delete()
        limite_leve = criar_peca('1,70', 1, 3, 1)       # 0,45 + 1,05 + 0,20 = 1,70 → leve
        logo_acima = criar_peca('1,75', 1, 2, 3)        # 0,45 + 0,70 + 0,60 = 1,75 → moderada
        limite_moderada = criar_peca('2,30', 3, 1, 3)   # 1,35 + 0,35 + 0,60 = 2,30 → moderada
        acima = criar_peca('2,45', 3, 2, 2)             # 1,35 + 0,70 + 0,40 = 2,45 → alta
        self.assertQuerySetEqual(Product.objects.with_severity_band('leve'), [limite_leve])
        self.assertCountEqual(Product.objects.with_severity_band('moderada'), [logo_acima, limite_moderada])
        self.assertQuerySetEqual(Product.objects.with_severity_band('alta'), [acima])

    def test_faixa_vazia_tem_mensagem_e_link_para_todas(self):
        self.alta.delete()
        response = self.client.get(reverse('home') + '?faixa=alta')
        self.assertContains(response, 'Nenhuma peça nessa faixa')
        self.assertContains(response, f'href="{reverse("home")}"')

    def test_chip_ativo_e_card_com_selo_e_link_para_a_peca(self):
        response = self.client.get(reverse('home') + '?faixa=moderada')
        self.assertContains(response, 'aria-current="true"><span class="severity-dot severity-dot--moderada">')
        self.assertContains(response, 'severity-badge--moderada')
        self.assertContains(response, reverse('product_detail', args=[self.moderada.pk]))


@override_settings(MEDIA_ROOT=MEDIA_DE_TESTE)
class PaginaProdutoTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.vendedor = User.objects.create_user('loja@example.com', password='Strong-test-524!')
        UserProfile.objects.create(user=self.vendedor, role=UserProfile.Role.BRAND,
                                   store_name='Ateliê Linha', location='Rio de Janeiro, RJ')
        self.comprador = User.objects.create_user('ana@example.com', password='Strong-test-524!')
        UserProfile.objects.create(user=self.comprador, role='buyer')
        self.peca = criar_peca('Calça de linho', 2, 2, 2, price=Decimal('130'), original_price=Decimal('200'),
                               seller=self.vendedor, brand='Ateliê Linha', size='38', condition='Nova com defeito',
                               defect_measure_cm=Decimal('4'), visible_when_worn=True)
        ProductImage.objects.create(product=self.peca, image=foto(nome='peca.jpg'), alt_text='Peça inteira')
        ProductImage.objects.create(product=self.peca, image=foto(nome='defeito.jpg'),
                                    alt_text='Close da mancha', is_defect=True)
        self.url = reverse('product_detail', args=[self.peca.pk])

    def test_mostra_ficha_do_defeito_preco_e_vendedor(self):
        response = self.client.get(self.url)
        for texto in ['Calça de linho', 'Severidade 2,00 · Moderada', 'Reparável', 'Funcional reparável',
                      'Semivisível', 'Média', '4,0 cm medidos', 'O defeito aparece quando',
                      'R$ 200,00', 'R$ 130,00', '35% off', 'Tamanho', '38', 'Ateliê Linha',
                      'Rio de Janeiro, RJ', 'Close do defeito', 'alt="Close da mancha"']:
            self.assertContains(response, texto)

    def test_defeito_nao_reparavel_nao_mostra_selo(self):
        self.peca.defeito.tipo = 3
        self.peca.defeito.save()
        self.assertNotContains(self.client.get(self.url), 'repair-badge')

    def test_peca_sem_fotos_nem_defeito_ainda_abre(self):
        peca = Product.objects.create(name='Blusa simples', description='Botão solto', price=Decimal('40'))
        response = self.client.get(reverse('product_detail', args=[peca.pk]))
        self.assertContains(response, 'Sem fotos desta peça ainda')
        self.assertNotContains(response, 'severity-badge')
        self.assertNotContains(response, '% off')

    def test_peca_inativa_ou_inexistente_da_404(self):
        self.peca.is_active = False
        self.peca.save()
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.assertEqual(self.client.get(reverse('product_detail', args=[9999])).status_code, 404)

    def test_visitante_ve_convite_para_entrar(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'Entrar para comprar')
        self.assertNotContains(response, reverse('cart_add', args=[self.peca.pk]))

    def test_comprador_adiciona_ao_carrinho_e_favorita_voltando_para_a_peca(self):
        self.client.force_login(self.comprador)
        self.assertContains(self.client.get(self.url), reverse('cart_add', args=[self.peca.pk]))
        response = self.client.post(reverse('favorite_add', args=[self.peca.pk]), {'next': self.url})
        self.assertRedirects(response, self.url)
        self.assertTrue(Favorite.objects.filter(user=self.comprador, product=self.peca).exists())
        self.assertContains(self.client.get(self.url), 'Favoritada')

    def test_peca_esgotada_nao_oferece_carrinho(self):
        self.peca.stock = 0
        self.peca.save()
        self.client.force_login(self.comprador)
        response = self.client.get(self.url)
        self.assertContains(response, 'Peça esgotada')
        self.assertNotContains(response, reverse('cart_add', args=[self.peca.pk]))


class ProductCardTests(TestCase):
    """Card da vitrine: só foto, selo, marca, nome, tamanho e preço."""

    def test_card_is_short_and_links_to_the_product(self):
        product = Product.objects.create(name='Saia midi', description='Texto longo que só aparece na página da peça.',
                                         size='M', price=Decimal('70.00'), original_price=Decimal('100.00'))
        Defeito.objects.create(product=product, tipo=2, localizacao=2, extensao=2)
        response = self.client.get(reverse('home'))
        for text in ['Defeito moderado', 'Tam. M', 'R$ 70,00', 'R$ 100,00', '-30%',
                     reverse('product_detail', args=[product.pk])]:
            self.assertContains(response, text)
        self.assertNotContains(response, 'Texto longo')

    def test_sold_out_piece_shows_overlay(self):
        Product.objects.create(name='Saia midi', description='-', price=Decimal('70.00'), stock=0)
        self.assertContains(self.client.get(reverse('home')), 'Esgotada')

    def test_defect_label_uses_masculine_form(self):
        for scores, label in [((1, 1, 1), 'Defeito leve'), ((2, 2, 2), 'Defeito moderado'), ((3, 3, 3), 'Defeito alto')]:
            product = Product()
            product.defeito = Defeito(tipo=scores[0], localizacao=scores[1], extensao=scores[2])
            self.assertEqual(product.defect_label, label)


class DiscountScenarioTests(TestCase):
    def test_discount_reference_scenarios(self):
        for scores, severity, discount in [((1,1,1), "1.00", 15), ((1,3,2), "1.90", 30), ((2,3,1), "2.15", 35), ((3,3,1), "2.60", 45)]:
            product = Product(original_price=Decimal("100.00"))
            product.defeito = Defeito(tipo=scores[0], localizacao=scores[1], extensao=scores[2])
            self.assertEqual(product.severity, Decimal(severity))
            self.assertEqual(product.suggested_discount, discount)
            self.assertEqual(product.suggested_price, Decimal(100-discount))


@override_settings(MEDIA_ROOT=MEDIA_DE_TESTE)
class OnDeleteTests(TestCase):
    """Comportamento de exclusão (on_delete) definido nos models."""

    def setUp(self):
        User = get_user_model()
        self.seller = User.objects.create_user("vendedor", password="x")
        self.buyer = User.objects.create_user("comprador", password="x")
        self.category = Category.objects.create(name="Vestidos")
        self.product = Product.objects.create(
            name="Vestido", description="d", price=Decimal("80"), original_price=Decimal("100"),
            seller=self.seller, category=self.category,
        )
        Defeito.objects.create(product=self.product, tipo=1, localizacao=1, extensao=1)

    def test_apagar_peca_apaga_defeito_imagens_favoritos_e_itens_do_carrinho(self):
        ProductImage.objects.create(product=self.product, image=foto(), alt_text="foto")
        Favorite.objects.create(user=self.buyer, product=self.product)
        cart = Cart.objects.create(user=self.buyer)
        CartItem.objects.create(cart=cart, product=self.product)
        self.product.delete()
        self.assertEqual(Defeito.objects.count(), 0)
        self.assertEqual(ProductImage.objects.count(), 0)
        self.assertEqual(Favorite.objects.count(), 0)
        self.assertEqual(CartItem.objects.count(), 0)
        self.assertTrue(Cart.objects.filter(pk=cart.pk).exists())

    def test_apagar_peca_mantem_historico_do_pedido(self):
        order = Order.objects.create(user=self.buyer, reference="FF-1")
        item = OrderItem.objects.create(order=order, product=self.product, product_name="Vestido", unit_price=Decimal("80"))
        self.product.delete()
        item.refresh_from_db()
        self.assertIsNone(item.product)
        self.assertEqual(item.product_name, "Vestido")
        self.assertEqual(order.total, Decimal("80.00"))

    def test_apagar_categoria_mantem_a_peca_sem_categoria(self):
        self.category.delete()
        self.product.refresh_from_db()
        self.assertIsNone(self.product.category)

    def test_nao_apaga_vendedor_que_tem_pecas(self):
        with self.assertRaises(ProtectedError):
            self.seller.delete()

    def test_nao_apaga_usuario_que_tem_pedidos(self):
        Order.objects.create(user=self.buyer, reference="FF-2")
        with self.assertRaises(ProtectedError):
            self.buyer.delete()

    def test_apagar_usuario_sem_pecas_nem_pedidos_apaga_perfil_carrinho_e_favoritos(self):
        UserProfile.objects.create(user=self.buyer, role="buyer")
        Cart.objects.create(user=self.buyer)
        Favorite.objects.create(user=self.buyer, product=self.product)
        self.buyer.delete()
        self.assertEqual(UserProfile.objects.count(), 0)
        self.assertEqual(Cart.objects.count(), 0)
        self.assertEqual(Favorite.objects.count(), 0)
        self.assertTrue(Product.objects.filter(pk=self.product.pk).exists())

    def test_apagar_pedido_apaga_seus_itens(self):
        order = Order.objects.create(user=self.buyer, reference="FF-3")
        OrderItem.objects.create(order=order, product=self.product, product_name="Vestido", unit_price=Decimal("80"))
        order.delete()
        self.assertEqual(OrderItem.objects.count(), 0)


@override_settings(MEDIA_ROOT=MEDIA_DE_TESTE)
class FotosDaPecaTests(TestCase):
    """Envio das fotos no cadastro e exibição na galeria."""

    @classmethod
    def setUpTestData(cls):
        cls.vendedor = get_user_model().objects.create_user(
            'foto@example.com', email='foto@example.com', password='Strong-test-524!')
        UserProfile.objects.create(user=cls.vendedor, role='seller')

    def setUp(self):
        self.client.login(username='foto@example.com', password='Strong-test-524!')

    def dados(self, **ajustes):
        valores = {'name': 'Camisa com mancha', 'description': 'Mancha na barra',
                   'brand': 'Circular', 'original_price': '200.00', 'defect_type': '2',
                   'defect_location': '3', 'defect_extent': '2', 'stock': '1',
                   'is_active': 'on', 'defect_photo': foto(nome='defeito.jpg')}
        valores.update(ajustes)
        return valores

    def cadastrar(self, **ajustes):
        return self.client.post(reverse('product_create'), self.dados(**ajustes))

    # ---------------- cadastro ----------------

    def test_cadastro_grava_as_fotos_e_marca_a_do_defeito(self):
        self.assertRedirects(self.cadastrar(photos=[foto(), foto()]), reverse('my_products'))
        peca = Product.objects.get(name='Camisa com mancha')
        self.assertEqual(peca.images.count(), 3)
        self.assertEqual(peca.images.filter(is_defect=True).count(), 1)
        self.assertIsNotNone(peca.cover_image)
        self.assertIsNotNone(peca.defect_image)

    def test_cadastro_sem_foto_do_defeito_e_recusado(self):
        dados = self.dados()
        dados.pop('defect_photo')
        response = self.client.post(reverse('product_create'), dados)
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context['form'], 'defect_photo',
                             'Envie a foto do defeito: sem ela a peça não pode ser publicada.')
        self.assertFalse(Product.objects.filter(name='Camisa com mancha').exists())

    def test_cadastro_so_com_a_foto_do_defeito_funciona(self):
        self.assertRedirects(self.cadastrar(), reverse('my_products'))
        peca = Product.objects.get(name='Camisa com mancha')
        self.assertEqual(peca.images.count(), 1)
        self.assertIsNone(peca.cover_image)

    # ---------------- arquivos recusados ----------------

    def test_arquivo_que_nao_e_imagem_e_recusado(self):
        falso = SimpleUploadedFile('virus.jpg', b'isto nao e uma imagem', 'image/jpeg')
        response = self.cadastrar(photos=[falso])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ProductImage.objects.count(), 0)

    def test_formato_fora_da_lista_e_recusado(self):
        with self.assertRaises(ValidationError):
            services.validate_image(foto(800, 800, 'GIF'))

    def test_arquivo_acima_do_limite_e_recusado(self):
        grande = foto(700, 700)
        grande.size = services.MAX_BYTES + 1
        with self.assertRaisesMessage(ValidationError, 'limite'):
            services.validate_image(grande)

    def test_imagem_pequena_demais_e_recusada(self):
        with self.assertRaisesMessage(ValidationError, str(services.MIN_SIDE)):
            services.validate_image(foto(300, 300))

    def test_fotos_demais_sao_recusadas(self):
        demais = [foto(nome=f'f{i}.jpg') for i in range(services.MAX_PHOTOS + 1)]
        response = self.cadastrar(photos=demais)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ProductImage.objects.count(), 0)

    def test_erros_de_varias_fotos_vem_juntos(self):
        with self.assertRaises(ValidationError) as erro:
            services.validate_images([foto(200, 200), foto(300, 300)])
        self.assertEqual(len(erro.exception.messages), 2)

    # ---------------- preparo da imagem ----------------

    def test_imagem_grande_e_reduzida(self):
        preparada = services.validate_image(foto(3000, 4000))
        with Image.open(preparada) as imagem:
            self.assertLessEqual(max(imagem.size), services.MAX_SIDE)

    def test_metadados_sao_descartados(self):
        """Foto de celular carrega GPS; isso não pode ir para a internet."""
        buffer = BytesIO()
        Image.new('RGB', (900, 900), (90, 90, 90)).save(buffer, 'JPEG', exif=Image.Exif().tobytes())
        buffer.seek(0)
        preparada = services.validate_image(
            SimpleUploadedFile('celular.jpg', buffer.read(), 'image/jpeg'))
        with Image.open(preparada) as imagem:
            self.assertFalse(imagem.getexif())

    def test_nome_enviado_nao_entra_no_caminho(self):
        self.cadastrar(photos=[foto(nome='minha_casa_familia.jpg')])
        peca = Product.objects.get(name='Camisa com mancha')
        self.assertNotIn('minha_casa_familia', peca.cover_image.image.name)
        self.assertIn(f'products/{peca.pk}/', peca.cover_image.image.name)

    # ---------------- edição ----------------

    def test_editar_sem_nova_foto_mantem_a_do_defeito(self):
        self.cadastrar()
        peca = Product.objects.get(name='Camisa com mancha')
        antiga = peca.defect_image.image.name
        dados = self.dados(name='Camisa editada')
        dados.pop('defect_photo')
        self.assertRedirects(
            self.client.post(reverse('product_update', args=[peca.pk]), dados),
            reverse('my_products'))
        peca.refresh_from_db()
        self.assertEqual(peca.name, 'Camisa editada')
        self.assertEqual(peca.defect_image.image.name, antiga)

    def test_nova_foto_do_defeito_substitui_a_antiga(self):
        self.cadastrar()
        peca = Product.objects.get(name='Camisa com mancha')
        antiga = peca.defect_image.image.name
        self.client.post(reverse('product_update', args=[peca.pk]),
                         self.dados(defect_photo=foto(nome='nova.jpg')))
        self.assertEqual(peca.images.filter(is_defect=True).count(), 1)
        self.assertNotEqual(peca.defect_image.image.name, antiga)

    # ---------------- arquivo no disco ----------------

    def test_apagar_a_foto_apaga_o_arquivo(self):
        self.cadastrar()
        imagem = Product.objects.get(name='Camisa com mancha').defect_image
        caminho = imagem.image.path
        self.assertTrue(os.path.exists(caminho))
        imagem.delete()
        self.assertFalse(os.path.exists(caminho))

    # ---------------- galeria ----------------

    def test_galeria_mostra_a_foto_do_defeito_primeiro(self):
        self.cadastrar(photos=[foto(), foto()])
        peca = Product.objects.get(name='Camisa com mancha')
        self.assertTrue(peca.images.first().is_defect)

    def test_pagina_da_peca_usa_o_arquivo_enviado(self):
        self.cadastrar(photos=[foto()])
        peca = Product.objects.get(name='Camisa com mancha')
        response = self.client.get(reverse('product_detail', args=[peca.pk]))
        self.assertContains(response, peca.defect_image.image.url)
        self.assertContains(response, 'Close do defeito')

    def test_card_mostra_a_capa_e_o_aviso_de_peca_sem_foto(self):
        self.cadastrar(photos=[foto()])
        com_foto = Product.objects.get(name='Camisa com mancha')
        sem_foto = criar_peca('Saia sem foto', seller=self.vendedor, original_price=Decimal('100'))
        response = self.client.get(reverse('my_products'))
        self.assertContains(response, com_foto.cover_image.image.url)
        self.assertContains(response, 'Sem foto da peça')
        self.assertEqual(sem_foto.cover_image, None)

    def test_formulario_aceita_envio_de_arquivo(self):
        """Sem enctype multipart o navegador não envia foto nenhuma."""
        response = self.client.get(reverse('product_create'))
        self.assertContains(response, 'enctype="multipart/form-data"')


class CatalogControlsTests(TestCase):
    """Busca, filtros e ordenação funcionam juntos sem perder favoritos."""

    @classmethod
    def setUpTestData(cls):
        cls.shirts = Category.objects.create(name='Camisetas', slug='camisetas')
        cls.trousers = Category.objects.create(name='Calças', slug='calcas')
        cls.empty_category = Category.objects.create(name='Sem peças', slug='sem-pecas')
        cls.first = criar_peca('Camisa de linho', 1, 3, 2, brand='Linha & Cia', size='M',
            category=cls.shirts, original_price=Decimal('100'), price=Decimal('70'))
        cls.second = criar_peca('Camiseta básica', 1, 1, 1, brand='Circular', size='P',
            category=cls.shirts, original_price=Decimal('200'), price=Decimal('170'))
        cls.third = criar_peca('Calça jeans', 3, 3, 3, brand='Linha & Cia', size='M',
            category=cls.trousers, original_price=Decimal('100'), price=Decimal('50'))
        cls.no_original = Product.objects.create(name='Saia sem preço original', description='Detalhes', price=Decimal('20'))
        cls.inactive = criar_peca('Peça oculta', brand='Só inativa', size='XXG', category=cls.empty_category, is_active=False)

    def results(self, **params):
        response = self.client.get(reverse('home'), params)
        self.assertEqual(response.status_code, 200)
        return response, [product.pk for product in response.context['products']]

    def test_individual_filters_and_full_combination(self):
        cases = [({'marca': 'Linha & Cia'}, [self.first, self.third]),
                 ({'categoria': 'camisetas'}, [self.first, self.second]),
                 ({'tamanho': 'P'}, [self.second]), ({'faixa': 'moderada'}, [self.first]),
                 ({'marca': 'Linha & Cia', 'categoria': 'camisetas', 'tamanho': 'M',
                   'faixa': 'moderada', 'q': 'linho'}, [self.first]),
                 ({'marca': 'Circular', 'tamanho': 'M'}, [])]
        for params, expected in cases:
            with self.subTest(params=params):
                response, ids = self.results(**params)
                self.assertCountEqual(ids, [product.pk for product in expected])
                self.assertEqual(response.context['result_count'], len(expected))
                self.assertNotIn(self.inactive.pk, ids)

    def test_options_come_from_whole_active_catalog_without_blanks_or_duplicates(self):
        response, _ = self.results(marca='Circular', tamanho='P')
        self.assertEqual(response.context['brands'], ['Circular', 'Linha & Cia'])
        self.assertEqual(response.context['sizes'], ['M', 'P'])
        self.assertCountEqual(response.context['categories'], [self.shirts, self.trousers])
        self.assertNotContains(response, 'Só inativa')
        self.assertNotContains(response, 'XXG')

    def test_search_matches_name_and_brand_without_case_and_trims_spaces(self):
        for query, expected in [('  LINHO ', [self.first]), ('circular', [self.second]),
                                ('Linha & Cia', [self.first, self.third])]:
            with self.subTest(query=query):
                _, ids = self.results(q=query)
                self.assertCountEqual(ids, [product.pk for product in expected])

    def test_unknown_filters_show_zero_and_clear_link_returns_all(self):
        for params in [{'marca': 'Inexistente'}, {'categoria': '999999999999999999999999999'},
                       {'tamanho': 'ZZ'}, {'q': 'Nada parecido'}]:
            with self.subTest(params=params):
                response, ids = self.results(**params)
                self.assertEqual(ids, [])
                self.assertContains(response, '0 peças')
                self.assertContains(response, 'Limpar filtros')
                self.assertContains(response, f'href="{reverse("home")}"')
        self.assertEqual(len(self.results()[1]), 4)

    def test_price_and_default_recent_order(self):
        self.assertEqual(self.results(ordem='preco')[1],
                         [self.no_original.pk, self.third.pk, self.first.pk, self.second.pk])
        self.assertEqual(self.results()[1],
                         [self.no_original.pk, self.third.pk, self.second.pk, self.first.pk])

    def test_discount_order_uses_actual_card_discount_instead_of_severity(self):
        self.first.price = Decimal('40')
        self.first.save()
        self.assertEqual(self.results(ordem='desconto')[1],
                         [self.first.pk, self.third.pk, self.second.pk, self.no_original.pk])

    def test_discount_ties_use_lower_price_and_missing_discount_is_last(self):
        tie = criar_peca('Outra promoção', original_price=Decimal('60'), price=Decimal('30'))
        full = criar_peca('Sem desconto', original_price=Decimal('40'), price=Decimal('40'))
        ids = self.results(ordem='desconto')[1]
        self.assertEqual(ids[:2], [tie.pk, self.third.pk])
        self.assertEqual(ids[-2:], [self.no_original.pk, full.pk])

    def test_controls_preserve_selected_filters_search_and_order(self):
        response, ids = self.results(marca='Linha & Cia', categoria='camisetas', tamanho='M',
                                    faixa='moderada', q='linho', ordem='desconto')
        self.assertEqual(ids, [self.first.pk])
        for text in ['name="faixa" value="moderada"', 'value="desconto" selected',
                     'value="camisetas" selected', 'value="Linha &amp; Cia" selected',
                     'name="q" id="catalog-query" value="linho"']:
            self.assertContains(response, text)

    def test_severity_links_preserve_other_controls_and_encode_special_characters(self):
        from urllib.parse import parse_qs
        params = {'marca': 'Linha & Cia', 'categoria': 'camisetas', 'tamanho': 'M',
                  'faixa': 'moderada', 'q': 'camisa & linho', 'ordem': 'preco'}
        response, _ = self.results(**params)
        for link in response.context['band_links']:
            expected = {key: [value] for key, value in params.items() if key != 'faixa'}
            if link['value']:
                expected['faixa'] = [link['value']]
            self.assertEqual(parse_qs(link['query']), expected)

    def test_unknown_order_and_severity_are_ignored_safely(self):
        response, ids = self.results(ordem='-seller__password', faixa='inexistente')
        self.assertEqual(ids, self.results()[1])
        self.assertEqual(response.context['ordering'], '')
        self.assertEqual(response.context['active_band'], '')

    def test_values_are_escaped(self):
        response, _ = self.results(q='<script>alert(1)</script>', marca='"><img src=x onerror=1>')
        self.assertNotContains(response, '<script>alert(1)</script>')
        self.assertNotContains(response, '<img src=x onerror=1>')
        self.assertContains(response, '&lt;script&gt;')

    def test_empty_catalog_renders_controls_and_count(self):
        Product.objects.all().delete()
        response, ids = self.results()
        self.assertEqual(ids, [])
        for text in ['A vitrine está vazia', '0 peças', 'Todas as marcas']:
            self.assertContains(response, text)

    def test_favorites_and_cart_still_work_after_filtering(self):
        buyer = get_user_model().objects.create_user('catalog-buyer@example.com')
        UserProfile.objects.create(user=buyer, role='buyer')
        Favorite.objects.create(user=buyer, product=self.first)
        self.client.force_login(buyer)
        response, _ = self.results(marca='Linha & Cia', ordem='preco')
        saved = next(product for product in response.context['products'] if product.pk == self.first.pk)
        self.assertTrue(saved.is_favorite)
        self.assertContains(response, reverse('favorite_remove', args=[self.first.pk]))
        self.assertContains(response, reverse('product_detail', args=[self.first.pk]))


class AboutAndPolicyTests(TestCase):
    def test_public_about_explains_nine_levels_research_and_model_weights(self):
        from .models import PESO_EXTENSAO, PESO_LOCALIZACAO, PESO_TIPO
        response = self.client.get(reverse('about'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item['weight'] for item in response.context['criteria']],
                         [PESO_TIPO, PESO_LOCALIZACAO, PESO_EXTENSAO])
        for text in ['oito entrevistas', 'ENG4021', 'PUC-Rio', 'protótipo acadêmico',
                     'Estético', 'Funcional reparável', 'Funcional não reparável',
                     'Escondido', 'Semivisível', 'Visível', 'Pequena', 'Média', 'Grande',
                     '0,45', '0,35', '0,20', 'S2_ResumoEntrevistas_M.pdf']:
            self.assertContains(response, text)

    def test_about_header_is_active_and_links_to_catalog_and_simulator(self):
        response = self.client.get(reverse('about'))
        self.assertContains(response, f'href="{reverse("about")}" aria-current="page"')
        self.assertContains(response, reverse('home'))
        self.assertContains(response, reverse('discount_simulator'))

    def test_product_detail_has_visible_policy_and_preserves_existing_content(self):
        product = criar_peca('Camisa de teste')
        response = self.client.get(reverse('product_detail', args=[product.pk]))
        for text in ['Política de troca e devolução', 'Não realizamos vendas, cobranças ou entregas reais',
                     'Ficha do defeito', reverse('about'), 'avaliações']:
            self.assertContains(response, text)

    def test_policy_explains_deadline_defect_rule_how_to_ask_and_shipping(self):
        product = criar_peca('Camisa de teste')
        response = self.client.get(reverse('product_detail', args=[product.pk]))
        for text in ['até 7 dias', 'Peça diferente do anúncio', 'Defeito já informado',
                     'Como pedir', 'Meus pedidos', 'Envio e reembolso', 'regras de exemplo do protótipo']:
            self.assertContains(response, text)


class FaqTests(TestCase):
    def test_faq_is_public_and_answers_buyers_and_sellers(self):
        response = self.client.get(reverse('faq'))
        self.assertEqual(response.status_code, 200)
        for text in ['Perguntas frequentes', 'Como compro uma peça?', 'A compra é de verdade?',
                     'Como vendo uma peça?', 'Esqueci minha senha', 'O que é a severidade do defeito?']:
            self.assertContains(response, text)

    def test_faq_links_to_related_pages(self):
        response = self.client.get(reverse('faq'))
        for name in ['home', 'about', 'discount_simulator', 'signup', 'password_reset']:
            self.assertContains(response, f'href="{reverse(name)}"')

    def test_about_and_product_page_link_to_faq(self):
        product = criar_peca('Camisa de teste')
        self.assertContains(self.client.get(reverse('about')), reverse('faq'))
        self.assertContains(self.client.get(reverse('product_detail', args=[product.pk])), reverse('faq'))


class CareersTests(TestCase):
    def test_careers_is_public_and_lists_the_team_areas(self):
        response = self.client.get(reverse('careers'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['openings']), 4)
        for text in ['Trabalhe conosco', 'Curadoria de peças', 'Atendimento', 'Desenvolvimento',
                     'Comunicação', 'não há processo seletivo aberto']:
            self.assertContains(response, text)

    def test_about_and_faq_link_to_careers(self):
        self.assertContains(self.client.get(reverse('about')), reverse('careers'))
        self.assertContains(self.client.get(reverse('faq')), reverse('careers'))


class ContactTests(TestCase):
    def test_contact_is_public_and_points_to_faq_and_repository(self):
        response = self.client.get(reverse('contact'))
        self.assertEqual(response.status_code, 200)
        for text in ['Fale com a', 'Antes de escrever', 'https://github.com/R0bbyt3/ENG4021',
                     'não há atendimento por telefone nem por e-mail']:
            self.assertContains(response, text)
        self.assertContains(response, reverse('faq'))

    def test_faq_and_careers_link_to_contact(self):
        self.assertContains(self.client.get(reverse('faq')), reverse('contact'))
        self.assertContains(self.client.get(reverse('careers')), reverse('contact'))


class TermsAndPrivacyTests(TestCase):
    def test_terms_is_public_and_covers_buyers_and_sellers(self):
        response = self.client.get(reverse('terms'))
        self.assertEqual(response.status_code, 200)
        for text in ['Termos de uso', 'Sua conta', 'Para quem compra', 'Para quem vende',
                     'O que não pode', 'projeto acadêmico']:
            self.assertContains(response, text)
        self.assertContains(response, reverse('privacy'))

    def test_privacy_is_public_and_lists_the_data_kept(self):
        response = self.client.get(reverse('privacy'))
        self.assertEqual(response.status_code, 200)
        for text in ['O que guardamos', 'CPF ou CNPJ', 'Cookies', 'não pede dados de cartão',
                     'Seus direitos']:
            self.assertContains(response, text)
        self.assertContains(response, reverse('terms'))

    def test_contact_links_to_terms_and_privacy(self):
        response = self.client.get(reverse('contact'))
        self.assertContains(response, reverse('terms'))
        self.assertContains(response, reverse('privacy'))


class ErrorPagesTests(TestCase):
    def test_unknown_url_shows_friendly_404(self):
        response = self.client.get('/uma-pagina-que-nao-existe/')
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, 'Página não', status_code=404)
        self.assertContains(response, reverse('home'), status_code=404)
        self.assertContains(response, reverse('faq'), status_code=404)

    def test_missing_product_shows_friendly_404(self):
        response = self.client.get(reverse('product_detail', args=[99999]))
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, 'Erro 404', status_code=404)

    def test_forbidden_area_shows_friendly_403_with_the_reason(self):
        buyer = get_user_model().objects.create_user('comprador-403@example.com')
        UserProfile.objects.create(user=buyer, role='buyer')
        self.client.force_login(buyer)
        response = self.client.get(reverse('my_products'))
        self.assertEqual(response.status_code, 403)
        self.assertContains(response, 'Erro 403', status_code=403)
        self.assertContains(response, 'exclusiva para vendedores e marcas', status_code=403)
        self.assertContains(response, reverse('home'), status_code=403)

    def test_server_error_page_has_no_header_and_links_home(self):
        from django.test import RequestFactory
        from django.views.defaults import server_error
        response = server_error(RequestFactory().get('/'))
        self.assertEqual(response.status_code, 500)
        html = response.content.decode()
        self.assertIn('Algo deu', html)
        self.assertIn(reverse('home'), html)


class FooterTests(TestCase):
    def test_footer_links_to_info_pages_on_the_shop_and_on_error_pages(self):
        pages = [self.client.get(reverse('home')), self.client.get('/uma-pagina-que-nao-existe/')]
        for response in pages:
            for name in ['about', 'careers', 'contact', 'faq', 'discount_simulator',
                         'password_reset', 'terms', 'privacy']:
                self.assertContains(response, f'href="{reverse(name)}"', status_code=response.status_code)

    def test_login_and_signup_pages_also_have_the_footer(self):
        urls = [reverse('login'), reverse('signup'), reverse('register', args=['comprador']),
                reverse('password_reset')]
        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertContains(response, 'class="site-footer"')
                self.assertContains(response, f'href="{reverse("faq")}"')

    def test_footer_is_visible_when_logged_in(self):
        user = get_user_model().objects.create_user('comprador@example.com', 'comprador@example.com', 'Senha-forte-524!')
        self.client.force_login(user)
        self.assertContains(self.client.get(reverse('about')), 'Informações legais')


class SimuladorLigadoAPecaTests(TestCase):
    """Link “Entender o desconto” na peça e a conta aberta no simulador."""

    def setUp(self):
        self.peca = criar_peca('Calça com mancha', tipo=2, localizacao=3, extensao=1,
                               original_price=Decimal('200.00'), price=Decimal('130.00'))

    def link(self, peca=None):
        return reverse('discount_simulator') + '?' + DiscountSimulationForm.query_for(peca or self.peca)

    def test_pagina_da_peca_tem_link_com_os_valores_do_defeito(self):
        response = self.client.get(reverse('product_detail', args=[self.peca.pk]))
        self.assertContains(response, 'Entender o desconto')
        self.assertContains(response, 'tipo=2&amp;local=3&amp;extensao=1&amp;preco=200.00')

    def test_peca_sem_defeito_nao_mostra_o_link(self):
        sem_ficha = Product.objects.create(name='Saia sem ficha', description='x', price=Decimal('50'))
        response = self.client.get(reverse('product_detail', args=[sem_ficha.pk]))
        self.assertNotContains(response, 'Entender o desconto')

    def test_link_cai_para_o_preco_final_quando_nao_ha_preco_original(self):
        sem_original = criar_peca('Blusa', tipo=1, localizacao=1, extensao=1, price=Decimal('45.00'))
        self.assertIn('preco=45.00', DiscountSimulationForm.query_for(sem_original))

    def test_link_abre_o_simulador_ja_calculado(self):
        response = self.client.get(self.link())
        resultado = response.context['result']
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['form'].data['defect_location'], '3')
        self.assertEqual(resultado['severity'], self.peca.severity)
        self.assertEqual(resultado['discount'], self.peca.suggested_discount)
        self.assertEqual(resultado['final_price'], self.peca.suggested_price)

    def test_resultado_mostra_a_formula_os_pesos_e_o_que_cada_criterio_somou(self):
        response = self.client.get(self.link())
        self.assertContains(response, '0,45 × tipo do defeito')
        self.assertContains(response, '0,35 × localização')
        self.assertContains(response, '0,20 × extensão')
        # 0,45×2 = 0,90 | 0,35×3 = 1,05 | 0,20×1 = 0,20 | nota = 2,15
        for soma in ('0,90', '1,05', '0,20', '2,15'):
            self.assertContains(response, soma)
        self.assertContains(response, 'Funcional reparável')
        self.assertContains(response, 'Visível')

    def test_a_soma_dos_criterios_e_a_propria_nota_nas_27_combinacoes(self):
        for tipo, local, extensao in combinations((1, 2, 3), repeat=3):
            with self.subTest(notas=(tipo, local, extensao)):
                linhas = severity_breakdown(tipo, local, extensao)
                self.assertEqual(sum(linha['points'] for linha in linhas),
                                 severidade(tipo, local, extensao))
                self.assertEqual([linha['score'] for linha in linhas], [tipo, local, extensao])

    def test_simulador_sem_parametros_abre_vazio_e_sem_erro(self):
        response = self.client.get(reverse('discount_simulator'))
        self.assertIsNone(response.context['result'])
        self.assertFalse(response.context['form'].is_bound)
        self.assertNotContains(response, 'form-errors')

    def test_parametro_invalido_na_url_pede_correcao_em_vez_de_calcular(self):
        response = self.client.get(reverse('discount_simulator') + '?tipo=9&local=1&extensao=1&preco=10')
        self.assertIsNone(response.context['result'])
        self.assertIn('defect_type', response.context['form'].errors)

    def test_url_pela_metade_mantem_o_que_veio_e_pede_o_resto(self):
        response = self.client.get(reverse('discount_simulator') + '?tipo=3')
        formulario = response.context['form']
        self.assertIsNone(response.context['result'])
        self.assertEqual(formulario.data['defect_type'], '3')
        self.assertIn('original_price', formulario.errors)

    def test_simulador_continua_funcionando_por_post(self):
        response = self.client.post(reverse('discount_simulator'), {
            'original_price': '200.00', 'defect_type': '2', 'defect_location': '3', 'defect_extent': '1',
        })
        self.assertEqual(response.context['result']['severity'], Decimal('2.15'))


def loja(username, store_name='', role=UserProfile.Role.SELLER, **campos):
    """Vendedor ou marca com perfil, do jeito que a página pública espera."""
    user = get_user_model().objects.create_user(username, first_name=username.capitalize())
    UserProfile.objects.create(user=user, role=role, store_name=store_name, **campos)
    return user


class PaginaDaMarcaTests(TestCase):
    """Aba “Marcas” e página pública de uma loja."""

    def setUp(self):
        self.marca = loja('reuso', 'Reuso Carioca', role=UserProfile.Role.BRAND,
                          location='Rio de Janeiro, RJ')
        self.outra = loja('circular', 'Ateliê Circular')
        self.sem_peca = loja('parada', 'Loja Parada')
        self.vestido = criar_peca('Vestido da marca', seller=self.marca)
        self.inativa = criar_peca('Peça fora da vitrine', seller=self.marca, is_active=False)
        self.alheia = criar_peca('Calça da outra', seller=self.outra)

    def test_aba_lista_quem_tem_peca_na_vitrine(self):
        resposta = self.client.get(reverse('store_list'))
        self.assertContains(resposta, 'Reuso Carioca')
        self.assertContains(resposta, 'Ateliê Circular')

    def test_aba_nao_lista_loja_sem_peca_ativa(self):
        criar_peca('Só inativa', seller=self.sem_peca, is_active=False)
        resposta = self.client.get(reverse('store_list'))
        self.assertNotContains(resposta, 'Loja Parada')

    def test_aba_conta_so_as_pecas_ativas(self):
        resposta = self.client.get(reverse('store_list'))
        contagem = {store.pk: store.product_count for store in resposta.context['stores']}
        self.assertEqual(contagem[self.marca.pk], 1)  # a inativa não entra

    def test_pagina_mostra_so_as_pecas_ativas_da_loja(self):
        resposta = self.client.get(reverse('store_detail', args=[self.marca.pk]))
        self.assertContains(resposta, 'Vestido da marca')
        self.assertNotContains(resposta, 'Peça fora da vitrine')
        self.assertNotContains(resposta, 'Calça da outra')

    def test_pagina_mostra_o_nome_e_a_cidade_da_marca(self):
        resposta = self.client.get(reverse('store_detail', args=[self.marca.pk]))
        self.assertContains(resposta, 'Reuso Carioca')
        self.assertContains(resposta, 'Rio de Janeiro, RJ')

    def test_pagina_de_loja_sem_peca_explica_em_vez_de_ficar_vazia(self):
        resposta = self.client.get(reverse('store_detail', args=[self.sem_peca.pk]))
        self.assertContains(resposta, 'não tem peças na vitrine')

    def test_vendedor_sem_nome_de_loja_aparece_pelo_proprio_nome(self):
        anonimo = loja('marina')
        criar_peca('Saia da Marina', seller=anonimo)
        resposta = self.client.get(reverse('store_detail', args=[anonimo.pk]))
        self.assertContains(resposta, 'Marina')

    def test_usuario_sem_perfil_nao_tem_pagina_de_loja(self):
        comum = get_user_model().objects.create_user('sem_perfil')
        self.assertEqual(self.client.get(reverse('store_detail', args=[comum.pk])).status_code, 404)

    def test_pagina_da_peca_linka_para_a_marca(self):
        resposta = self.client.get(reverse('product_detail', args=[self.vestido.pk]))
        self.assertContains(resposta, reverse('store_detail', args=[self.marca.pk]))

    def test_menu_tem_a_aba_marcas(self):
        self.assertContains(self.client.get(reverse('home')), reverse('store_list'))

    def test_nota_da_loja_aparece_quando_ha_avaliacao(self):
        comprador = get_user_model().objects.create_user('cliente', first_name='Cliente')
        pedido = Order.objects.create(user=comprador, reference='FF-MARCA-001')
        item = OrderItem.objects.create(order=pedido, product=self.vestido,
                                        product_name=self.vestido.name,
                                        unit_price=self.vestido.price, quantity=1)
        Review.objects.create(order_item=item, user=comprador, rating=4, comment='Chegou bem.')

        resposta = self.client.get(reverse('store_detail', args=[self.marca.pk]))
        self.assertContains(resposta, '4,0')
        self.assertNotContains(resposta, 'Loja ainda sem avaliações')

    def test_loja_sem_avaliacao_diz_que_nao_tem(self):
        resposta = self.client.get(reverse('store_detail', args=[self.marca.pk]))
        self.assertContains(resposta, 'Loja ainda sem avaliações')


class AbasDeCategoriaEPaginacaoTests(TestCase):
    """Atalhos de categoria no topo da vitrine e paginação que não perde filtros."""

    @classmethod
    def setUpTestData(cls):
        cls.vestidos = Category.objects.create(name='Vestidos', slug='vestidos')
        cls.acessorios = Category.objects.create(name='Acessórios', slug='acessorios')
        cls.vazia = Category.objects.create(name='Sem peças', slug='sem-pecas')
        cls.vestido = criar_peca('Vestido longo', brand='Circular', size='M',
                                 category=cls.vestidos)
        cls.colar = criar_peca('Colar de contas', brand='Circular', size='U',
                               category=cls.acessorios)

    def abas(self, resposta):
        return {item['label']: item['query'] for item in resposta.context['category_links']}

    def test_abas_listam_todas_e_as_categorias_com_peca(self):
        abas = self.abas(self.client.get(reverse('home')))
        self.assertEqual(set(abas), {'Todas', 'Vestidos', 'Acessórios'})

    def test_categoria_sem_peca_ativa_nao_vira_aba(self):
        criar_peca('Peça guardada', category=self.vazia, is_active=False)
        self.assertNotIn('Sem peças', self.abas(self.client.get(reverse('home'))))

    def test_clicar_na_aba_filtra_a_vitrine(self):
        resposta = self.client.get(reverse('home'), {'categoria': 'vestidos'})
        nomes = [peca.name for peca in resposta.context['products']]
        self.assertEqual(nomes, ['Vestido longo'])

    def test_aba_mantem_busca_filtros_e_ordem(self):
        from urllib.parse import parse_qs
        controles = {'marca': 'Circular', 'tamanho': 'M', 'faixa': 'leve',
                     'q': 'vestido & cia', 'ordem': 'preco'}
        resposta = self.client.get(reverse('home'), controles)
        for item in resposta.context['category_links']:
            esperado = {chave: [valor] for chave, valor in controles.items()}
            if item['value']:
                esperado['categoria'] = [item['value']]
            self.assertEqual(parse_qs(item['query']), esperado)

    def test_aba_ativa_fica_marcada(self):
        resposta = self.client.get(reverse('home'), {'categoria': 'vestidos'})
        self.assertContains(resposta, 'category-tab is-active')
        self.assertContains(resposta, 'aria-current="true"')

    def test_vitrine_sem_categoria_nenhuma_nao_mostra_a_barra_de_abas(self):
        Product.objects.all().update(category=None)
        self.assertNotContains(self.client.get(reverse('home')), 'category-tabs')


class PaginacaoDaVitrineTests(TestCase):
    """A vitrine pagina de 12 em 12 sem perder busca, filtros e ordem."""

    @classmethod
    def setUpTestData(cls):
        cls.categoria = Category.objects.create(name='Camisetas', slug='camisetas')
        # 15 peças da mesma categoria: duas páginas.
        for numero in range(15):
            criar_peca(f'Camiseta {numero:02}', brand='Circular', size='M',
                       category=cls.categoria, original_price=Decimal('100'),
                       price=Decimal(100 - numero))
        criar_peca('Calça de outra categoria', brand='Outra', size='G')

    def test_primeira_pagina_traz_doze_pecas_e_o_total_completo(self):
        resposta = self.client.get(reverse('home'))
        self.assertEqual(len(resposta.context['products']), 12)
        self.assertEqual(resposta.context['result_count'], 16)
        self.assertContains(resposta, 'Próxima')

    def test_segunda_pagina_traz_o_resto(self):
        resposta = self.client.get(reverse('home'), {'page': 2})
        self.assertEqual(len(resposta.context['products']), 4)
        self.assertContains(resposta, 'Anterior')

    def test_segunda_pagina_mantem_busca_filtros_e_ordem(self):
        controles = {'categoria': 'camisetas', 'marca': 'Circular', 'tamanho': 'M',
                     'q': 'camiseta', 'ordem': 'preco'}
        resposta = self.client.get(reverse('home'), {**controles, 'page': 2})
        self.assertEqual(resposta.context['result_count'], 15)
        nomes = [peca.name for peca in resposta.context['products']]
        self.assertEqual(nomes, ['Camiseta 02', 'Camiseta 01', 'Camiseta 00'])
        for chave, valor in controles.items():
            self.assertIn(chave, resposta.context['filters_query'])
            self.assertIn(valor.replace(' ', '+'), resposta.context['filters_query'])
        self.assertNotIn('page', resposta.context['filters_query'])

    def test_link_da_proxima_pagina_carrega_os_filtros(self):
        resposta = self.client.get(reverse('home'), {'categoria': 'camisetas', 'ordem': 'preco'})
        self.assertContains(resposta, 'categoria=camisetas')
        self.assertContains(resposta, 'ordem=preco&amp;page=2')

    def test_pagina_invalida_cai_na_ultima(self):
        resposta = self.client.get(reverse('home'), {'page': '99'})
        self.assertEqual(resposta.context['page_obj'].number, 2)

    def test_pagina_que_nao_e_numero_cai_na_primeira(self):
        resposta = self.client.get(reverse('home'), {'page': 'abc'})
        self.assertEqual(resposta.context['page_obj'].number, 1)

    def test_vitrine_curta_nao_mostra_paginacao(self):
        Product.objects.exclude(name='Camiseta 00').delete()
        self.assertNotContains(self.client.get(reverse('home')), 'Paginação')
