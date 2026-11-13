from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserProfile
from products.models import Product

from .models import Cart, CartItem
from .services import MAX_INSTALLMENTS, SHIPPING_COST, max_installments, purchase_summary


class CartTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.buyer = User.objects.create_user('buyer@example.com', email='buyer@example.com')
        UserProfile.objects.create(user=cls.buyer, role='buyer')
        cls.other_buyer = User.objects.create_user('other-buyer@example.com')
        UserProfile.objects.create(user=cls.other_buyer, role='buyer')
        cls.seller = User.objects.create_user('seller@example.com')
        UserProfile.objects.create(user=cls.seller, role='seller')
        cls.shirt = Product.objects.create(name='Camisa de linho', description='Mancha pequena na barra',
                                           price=Decimal('85.00'), original_price=Decimal('100.00'),
                                           stock=3, seller=cls.seller)
        cls.jeans = Product.objects.create(name='Calça jeans', description='Fio puxado',
                                           price=Decimal('120.50'), stock=5, seller=cls.seller)

    def add(self, product, quantity='1', **extra):
        return self.client.post(reverse('cart_add', args=[product.pk]), {'quantity': quantity, **extra})

    def quantity_of(self, product, user=None):
        item = CartItem.objects.filter(cart__user=user or self.buyer, product=product).first()
        return item.quantity if item else None


class AddToCartTests(CartTestCase):
    def test_anonymous_user_is_sent_to_login_and_nothing_is_created(self):
        response = self.add(self.shirt)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response['Location'])
        self.assertEqual(CartItem.objects.count(), 0)
        response = self.client.get(reverse('cart'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response['Location'])

    def test_buyer_adds_piece_and_cart_is_created(self):
        self.client.force_login(self.buyer)
        response = self.add(self.shirt, '2')
        self.assertRedirects(response, reverse('cart'))
        self.assertEqual(self.quantity_of(self.shirt), 2)
        self.assertEqual(Cart.objects.filter(user=self.buyer).count(), 1)

    def test_adding_the_same_piece_accumulates_quantity(self):
        self.client.force_login(self.buyer)
        self.add(self.shirt, '1')
        self.add(self.shirt, '2')
        self.assertEqual(self.quantity_of(self.shirt), 3)
        self.assertEqual(CartItem.objects.filter(cart__user=self.buyer).count(), 1)

    def test_cannot_exceed_stock_including_what_is_already_in_cart(self):
        self.client.force_login(self.buyer)
        self.add(self.shirt, '2')
        response = self.client.post(reverse('cart_add', args=[self.shirt.pk]), {'quantity': '2'}, follow=True)
        self.assertEqual(self.quantity_of(self.shirt), 2)
        self.assertContains(response, 'Só há 3 unidades em estoque')
        self.assertContains(response, 'Você já tem 2 no carrinho')

    def test_inactive_or_sold_out_pieces_cannot_be_added(self):
        self.client.force_login(self.buyer)
        self.shirt.is_active = False
        self.shirt.save()
        self.jeans.stock = 0
        self.jeans.save()
        self.add(self.shirt)
        self.add(self.jeans)
        self.assertEqual(CartItem.objects.count(), 0)

    def test_missing_piece_returns_404(self):
        self.client.force_login(self.buyer)
        self.assertEqual(self.client.post(reverse('cart_add', args=[9999]), {'quantity': '1'}).status_code, 404)

    def test_invalid_quantities_are_rejected(self):
        self.client.force_login(self.buyer)
        for value in ['0', '-1', 'abc', '', '1.5', '100', '99999999999999999999']:
            with self.subTest(quantity=value):
                self.add(self.jeans, value)
                self.assertIsNone(self.quantity_of(self.jeans))

    def test_cannot_buy_own_piece(self):
        self.client.force_login(self.seller)
        # Vendedor nem entra: o carrinho é de comprador.
        self.assertRedirects(self.add(self.shirt), reverse('home'))
        self.assertEqual(CartItem.objects.count(), 0)
        staff = get_user_model().objects.create_user('staff@example.com', is_staff=True)
        own = Product.objects.create(name='Peça da equipe', description='x', price=Decimal('10'), stock=1, seller=staff)
        self.client.force_login(staff)
        self.add(own)
        self.assertEqual(CartItem.objects.count(), 0)

    def test_add_requires_post(self):
        self.client.force_login(self.buyer)
        self.assertEqual(self.client.get(reverse('cart_add', args=[self.shirt.pk])).status_code, 405)

    def test_forged_price_in_request_is_ignored(self):
        self.client.force_login(self.buyer)
        self.add(self.shirt, '1', price='0.01', unit_price='0.01', total='0.01')
        response = self.client.get(reverse('cart'))
        self.assertEqual(response.context['total'], Decimal('85.00'))


class UpdateAndRemoveTests(CartTestCase):
    def setUp(self):
        self.client.force_login(self.buyer)
        self.add(self.shirt, '1')
        self.add(self.jeans, '2')
        self.shirt_item = CartItem.objects.get(cart__user=self.buyer, product=self.shirt)
        self.jeans_item = CartItem.objects.get(cart__user=self.buyer, product=self.jeans)

    def update(self, item, quantity):
        return self.client.post(reverse('cart_update_item', args=[item.pk]), {'quantity': quantity})

    def test_update_changes_quantity_and_total_is_computed_by_server(self):
        response = self.update(self.shirt_item, '3')
        self.assertRedirects(response, reverse('cart'))
        self.assertEqual(self.quantity_of(self.shirt), 3)
        page = self.client.get(reverse('cart'))
        # 3 × 85,00 + 2 × 120,50
        self.assertEqual(page.context['total'], Decimal('496.00'))
        self.assertEqual(page.context['pieces'], 5)

    def test_update_rejects_invalid_or_excessive_quantities(self):
        for value in ['0', '-2', 'x', '', '4', '100']:
            with self.subTest(quantity=value):
                self.update(self.shirt_item, value)
                self.assertEqual(self.quantity_of(self.shirt), 1)

    def test_update_is_rejected_when_piece_became_inactive(self):
        self.shirt.is_active = False
        self.shirt.save()
        self.update(self.shirt_item, '2')
        self.assertEqual(self.quantity_of(self.shirt), 1)

    def test_remove_deletes_only_that_item(self):
        response = self.client.post(reverse('cart_remove_item', args=[self.shirt_item.pk]))
        self.assertRedirects(response, reverse('cart'))
        self.assertIsNone(self.quantity_of(self.shirt))
        self.assertEqual(self.quantity_of(self.jeans), 2)

    def test_cannot_change_or_remove_another_buyers_item(self):
        self.client.force_login(self.other_buyer)
        self.assertEqual(self.update(self.shirt_item, '3').status_code, 404)
        self.assertEqual(self.client.post(reverse('cart_remove_item', args=[self.shirt_item.pk])).status_code, 404)
        self.assertEqual(self.quantity_of(self.shirt), 1)

    def test_update_and_remove_require_post_and_login(self):
        self.assertEqual(self.client.get(reverse('cart_update_item', args=[self.shirt_item.pk])).status_code, 405)
        self.assertEqual(self.client.get(reverse('cart_remove_item', args=[self.shirt_item.pk])).status_code, 405)
        self.client.logout()
        response = self.update(self.shirt_item, '2')
        self.assertIn(reverse('login'), response['Location'])
        self.assertEqual(self.quantity_of(self.shirt), 1)


class CartPageTests(CartTestCase):
    def test_empty_cart_shows_empty_state(self):
        self.client.force_login(self.buyer)
        response = self.client.get(reverse('cart'))
        self.assertContains(response, 'Seu carrinho está vazio')
        self.assertEqual(response.context['total'], Decimal('0.00'))

    def test_page_shows_items_subtotals_and_total_from_database(self):
        self.client.force_login(self.buyer)
        self.add(self.shirt, '2')
        self.add(self.jeans, '1')
        response = self.client.get(reverse('cart'))
        self.assertContains(response, 'Camisa de linho')
        self.assertContains(response, 'Mancha pequena na barra')
        self.assertContains(response, '170,00')   # subtotal da camisa (2 × 85)
        self.assertContains(response, '290,50')   # total
        self.assertEqual(response.context['total'], Decimal('290.50'))

    def test_price_change_in_database_is_reflected_in_cart(self):
        self.client.force_login(self.buyer)
        self.add(self.shirt, '1')
        self.shirt.price = Decimal('60.00')
        self.shirt.save()
        self.assertEqual(self.client.get(reverse('cart')).context['total'], Decimal('60.00'))

    def test_unavailable_items_are_flagged_and_left_out_of_total(self):
        self.client.force_login(self.buyer)
        self.add(self.shirt, '2')
        self.add(self.jeans, '1')
        self.shirt.stock = 1          # estoque caiu abaixo do que está no carrinho
        self.shirt.save()
        response = self.client.get(reverse('cart'))
        self.assertTrue(response.context['has_unavailable'])
        self.assertContains(response, 'Só há 1 unidade em estoque')
        self.assertEqual(response.context['total'], Decimal('120.50'))
        self.assertEqual(response.context['pieces'], 1)

    def test_each_buyer_sees_only_their_own_cart(self):
        self.client.force_login(self.buyer)
        self.add(self.shirt)
        self.client.force_login(self.other_buyer)
        response = self.client.get(reverse('cart'))
        self.assertContains(response, 'Seu carrinho está vazio')

    def test_product_page_offers_add_to_cart_to_logged_buyers(self):
        # O botão fica na página da peça; o card da vitrine só leva até ela.
        url = reverse('product_detail', args=[self.shirt.pk])
        self.client.force_login(self.buyer)
        response = self.client.get(url)
        self.assertContains(response, reverse('cart_add', args=[self.shirt.pk]))
        self.assertContains(response, 'Adicionar ao carrinho')
        self.assertNotContains(self.client.get(reverse('home')), reverse('cart_add', args=[self.shirt.pk]))
        self.client.logout()
        response = self.client.get(url)
        self.assertContains(response, 'Entrar para comprar')
        self.assertNotContains(response, reverse('cart_add', args=[self.shirt.pk]))


class ShippingAndInstallmentsTests(CartTestCase):
    def test_shipping_is_fixed_and_added_to_the_total(self):
        summary = purchase_summary(Decimal('85.00'))
        self.assertEqual(summary['shipping'], SHIPPING_COST)
        self.assertEqual(summary['total'], Decimal('104.90'))
        self.assertEqual(purchase_summary(Decimal('500.00'))['shipping'], SHIPPING_COST)

    def test_no_pieces_means_no_shipping(self):
        summary = purchase_summary(Decimal('0.00'))
        self.assertEqual(summary['shipping'], Decimal('0.00'))
        self.assertEqual(summary['total'], Decimal('0.00'))

    def test_installments_respect_the_minimum_and_the_maximum(self):
        for total, expected in [('10.00', 1), ('29.99', 1), ('30.00', 1), ('60.00', 2), ('89.99', 2),
                                ('119.90', 3), ('180.00', 6), ('5000.00', MAX_INSTALLMENTS)]:
            with self.subTest(total=total):
                self.assertEqual(max_installments(Decimal(total)), expected)

    def test_installment_value_is_the_total_divided_without_interest(self):
        summary = purchase_summary(Decimal('85.00'))  # total 104,90 em 3x
        self.assertEqual(summary['installments'], 3)
        self.assertEqual(summary['installment_value'], Decimal('34.97'))

    def test_cart_shows_shipping_total_and_installments(self):
        self.client.force_login(self.buyer)
        self.add(self.shirt)
        response = self.client.get(reverse('cart'))
        self.assertEqual(response.context['payment']['total'], Decimal('104.90'))
        self.assertContains(response, 'R$ 19,90')
        self.assertContains(response, 'R$ 104,90')
        self.assertContains(response, 'Em até <strong>3x de R$ 34,97</strong> sem juros', html=True)

    def test_unavailable_items_do_not_count_for_shipping_or_total(self):
        self.client.force_login(self.buyer)
        self.add(self.jeans)
        Product.objects.filter(pk=self.jeans.pk).update(is_active=False)
        payment = self.client.get(reverse('cart')).context['payment']
        self.assertEqual(payment['shipping'], Decimal('0.00'))
        self.assertEqual(payment['total'], Decimal('0.00'))

    def test_product_page_shows_shipping_and_installments(self):
        response = self.client.get(reverse('product_detail', args=[self.shirt.pk]))
        self.assertContains(response, 'Frete fixo de')
        self.assertContains(response, 'R$ 19,90')
        self.assertContains(response, '3x de R$ 34,97')
