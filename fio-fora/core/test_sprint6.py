from decimal import Decimal
from itertools import product as combinations
from unittest.mock import PropertyMock, patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from .seller_forms import ProductRegistrationForm
from .models import Product, UserProfile


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
            'defect_location': '3', 'defect_extent': '2', 'stock': '1', 'is_active': 'on'}
        values.update(overrides)
        return values

    def test_create_assigns_logged_seller_and_ignores_forged_price_and_owner(self):
        self.client.force_login(self.seller)
        response = self.client.post(reverse('seller_product_create'), self.data(
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
        self.assertNotContains(response, '/editar/')
        self.assertNotContains(response, '/remover/')
        self.assertNotContains(response, 'Peça de outro vendedor')

    def test_invalid_or_empty_posts_never_create_products(self):
        self.client.force_login(self.seller)
        count = Product.objects.count()
        for data in [{}, self.data(original_price=''), self.data(original_price='0'),
                     self.data(original_price='-2'), self.data(defect_type='4'),
                     self.data(stock='0'), self.data(defect_measure_cm='-1'),
                     self.data(name=''), self.data(original_price='NaN')]:
            with self.subTest(data=data):
                response = self.client.post(reverse('seller_product_create'), data)
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context['form'].errors)
                self.assertEqual(Product.objects.count(), count)

    def test_anonymous_and_buyers_cannot_enter_seller_area(self):
        routes = [('seller_product_create', []), ('my_products', [])]
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
        self.assertRedirects(self.client.post(reverse('seller_product_create'), self.data()), reverse('my_products'))
        self.assertEqual(Product.objects.get(name='Camisa de linho').seller, self.brand)
        no_profile = get_user_model().objects.create_user('no-profile')
        self.client.force_login(no_profile)
        self.assertEqual(self.client.get(reverse('my_products')).status_code, 403)



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
                form = ProductRegistrationForm(data)
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
        self.assertEqual(client.post(reverse('seller_product_create'), self.data()).status_code, 403)
        self.assertEqual(client.post(reverse('discount_simulator'), self.data()).status_code, 403)
