from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase

from cart.models import Cart, CartItem
from favorites.models import Favorite
from products.models import Defeito, Product

from .models import Order, OrderItem


class OrderHistoryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        buyer = get_user_model().objects.create_user("comprador")
        product = Product.objects.create(name="Vestido floral", description="Botão faltando.",
                                         original_price=Decimal("160.00"), price=Decimal("104.00"))
        Defeito.objects.create(product=product, tipo=2, localizacao=3, extensao=1)
        order = Order.objects.create(user=buyer, reference="FF-TESTE-001")
        OrderItem.objects.create(order=order, product=product, product_name=product.name,
                                 unit_price=product.price, quantity=1)
        Favorite.objects.create(user=buyer, product=product)
        CartItem.objects.create(cart=Cart.objects.create(user=buyer), product=product)

    def test_financial_history_and_database_integrity(self):
        order = Order.objects.get(reference="FF-TESTE-001")
        self.assertEqual(order.total, Decimal("104.00"))
        product = order.items.get().product
        product.name = "Novo nome"
        product.price = Decimal("99.00")
        product.save()
        self.assertEqual(order.items.get().product_name, "Vestido floral")
        self.assertEqual(order.total, Decimal("104.00"))
        with self.assertRaises(IntegrityError), transaction.atomic():
            Favorite.objects.create(user_id=Favorite.objects.first().user_id, product_id=Favorite.objects.first().product_id)
        with self.assertRaises(IntegrityError), transaction.atomic():
            CartItem.objects.filter(pk=CartItem.objects.first().pk).update(quantity=0)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Defeito.objects.filter(product=product).update(tipo=4)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Product.objects.filter(pk=product.pk).update(price=Decimal("0.00"))


class OrderConfirmationEmailTests(TestCase):
    def setUp(self):
        from accounts.models import UserProfile
        self.buyer = get_user_model().objects.create_user('comprador', 'ana@example.com', 'senha-segura-1')
        UserProfile.objects.create(user=self.buyer, role='buyer')
        seller = get_user_model().objects.create_user('vendedor', 'loja@example.com', 'senha-segura-1')
        UserProfile.objects.create(user=seller, role='seller')
        self.product = Product.objects.create(seller=seller, name='Vestido floral', description='Botão faltando.',
                                              original_price=Decimal('160.00'), price=Decimal('104.00'), stock=3)
        Defeito.objects.create(product=self.product, tipo=2, localizacao=3, extensao=1)
        CartItem.objects.create(cart=Cart.objects.create(user=self.buyer), product=self.product, quantity=2)
        self.client.force_login(self.buyer)

    def test_checkout_sends_confirmation_to_the_buyer(self):
        from django.core import mail
        response = self.client.post('/checkout/')
        order = Order.objects.get()
        self.assertRedirects(response, f'/pedidos/{order.pk}/')
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, ['ana@example.com'])
        self.assertIn(order.reference, message.subject)
        for text in [order.reference, 'Vestido floral', '2 x R$', 'Total: R$', f'/pedidos/{order.pk}/', 'protótipo acadêmico']:
            self.assertIn(text, message.body)

    def test_confirmation_has_html_version_with_items_and_link(self):
        from django.core import mail
        self.client.post('/checkout/')
        order = Order.objects.get()
        html, mimetype = mail.outbox[0].alternatives[0]
        self.assertEqual(mimetype, 'text/html')
        for text in [order.reference, 'Vestido floral', 'R$ 208,00', f'/pedidos/{order.pk}/', 'Ver o pedido']:
            self.assertIn(text, html)

    def test_email_failure_keeps_the_order_and_warns(self):
        from unittest import mock
        with mock.patch('orders.services.send_mail', side_effect=OSError('sem rede')):
            response = self.client.post('/checkout/', follow=True)
        self.assertEqual(Order.objects.count(), 1)
        self.assertContains(response, 'Não foi possível enviar o e-mail de confirmação')

    def test_no_email_when_checkout_fails(self):
        from django.core import mail
        CartItem.objects.all().delete()
        self.client.post('/checkout/')
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_buyer_without_email_still_buys_without_sending(self):
        from django.core import mail
        self.buyer.email = ''
        self.buyer.save()
        response = self.client.post('/checkout/', follow=True)
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 0)
        self.assertContains(response, 'Não foi possível enviar o e-mail de confirmação')


class SellerSalesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        from accounts.models import UserProfile

        def make_user(name, role, **fields):
            user = get_user_model().objects.create_user(name, **fields)
            UserProfile.objects.create(user=user, role=role)
            return user

        cls.buyer = make_user('comprador-painel', 'buyer', first_name='Joana')
        cls.seller = make_user('vendedor-painel', 'seller')
        cls.brand = make_user('marca-painel', 'brand')
        cls.outsider = make_user('outra-loja', 'seller')
        cls.order = Order.objects.create(user=cls.buyer, reference='FF-PAINEL', status=Order.Status.PAID)
        cls.other_order = Order.objects.create(user=cls.buyer, reference='FF-OUTRO')

        def add_item(order, seller, name):
            product = Product.objects.create(
                seller=seller, name=name, original_price=Decimal('60.00'),
                price=Decimal('50.00'), stock=3,
            )
            return OrderItem.objects.create(
                order=order, product=product, product_name=name, unit_price=product.price,
            )

        cls.seller_item = add_item(cls.order, cls.seller, 'Peça da primeira loja')
        cls.brand_item = add_item(cls.order, cls.brand, 'Peça da segunda loja')
        cls.other_item = add_item(cls.other_order, cls.outsider, 'Peça do outro pedido')

    def setUp(self):
        self.sales_url = '/minhas-vendas/'
        self.status_url = f'{self.sales_url}{self.order.pk}/status/'

    def test_panel_shows_buyer_and_only_owned_items(self):
        self.client.force_login(self.seller)
        response = self.client.get(self.sales_url)
        for text in ['Minhas vendas', 'FF-PAINEL', 'Joana', 'Peça da primeira loja', 'Marcar como enviado']:
            self.assertContains(response, text)
        for text in ['Peça da segunda loja', 'FF-OUTRO']:
            self.assertNotContains(response, text)

    def test_unrelated_seller_cannot_change_order(self):
        self.client.force_login(self.outsider)
        self.assertEqual(self.client.post(self.status_url, {'status': 'shipped'}).status_code, 404)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.PAID)

    def test_panel_requires_seller_or_brand(self):
        self.assertEqual(self.client.get(self.sales_url).status_code, 302)
        self.client.force_login(self.buyer)
        self.assertEqual(self.client.get(self.sales_url).status_code, 403)
        self.assertEqual(self.client.post(self.status_url, {'status': 'shipped'}).status_code, 403)
        self.client.force_login(self.brand)
        self.assertContains(self.client.get(self.sales_url), 'Peça da segunda loja')

    def test_status_changes_only_by_post_and_cannot_skip_or_go_back(self):
        self.client.force_login(self.seller)
        self.assertEqual(self.client.get(self.status_url).status_code, 405)
        for invalid in ['delivered', 'pending', 'cancelled', 'desconhecido', '']:
            response = self.client.post(self.status_url, {'status': invalid}, follow=True)
            self.assertContains(response, 'Essa mudança de status não está disponível')
        self.seller_item.refresh_from_db()
        self.assertEqual(self.seller_item.sale_status, Order.Status.PAID)

    def test_buyer_sees_each_item_and_general_status_follows_both_sellers(self):
        self.client.force_login(self.seller)
        self.assertRedirects(self.client.post(self.status_url, {'status': 'shipped'}), self.sales_url)
        self.client.post(self.status_url, {'status': 'delivered'})
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.PAID)
        self.brand_item.refresh_from_db()
        self.assertEqual(self.brand_item.sale_status, Order.Status.PAID)

        self.client.force_login(self.buyer)
        response = self.client.get(f'/pedidos/{self.order.pk}/')
        self.assertContains(response, 'Status da peça: Entregue')
        self.assertContains(response, 'Status da peça: Pago')

        self.client.force_login(self.brand)
        for status in [Order.Status.SHIPPED, Order.Status.DELIVERED]:
            self.client.post(self.status_url, {'status': status})
            self.order.refresh_from_db()
            self.assertEqual(self.order.status, status)

    def test_pending_order_can_advance_to_paid(self):
        self.client.force_login(self.outsider)
        self.client.post(f'{self.sales_url}{self.other_order.pk}/status/', {'status': 'paid'})
        self.other_order.refresh_from_db()
        self.assertEqual(self.other_order.status, Order.Status.PAID)
