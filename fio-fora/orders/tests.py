from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase

from cart.models import Cart, CartItem
from favorites.models import Favorite
from products.models import Defeito, Product

from .models import Order, OrderItem

# Endereço válido, como o navegador envia no checkout.
ADDRESS = {
    'cep': '20040-020', 'street': 'Rua da Assembleia', 'number': '10', 'complement': 'sala 2',
    'district': 'Centro', 'address_city': 'Rio de Janeiro', 'address_state': 'RJ',
}


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
        response = self.client.post('/checkout/', ADDRESS)
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
        self.client.post('/checkout/', ADDRESS)
        order = Order.objects.get()
        html, mimetype = mail.outbox[0].alternatives[0]
        self.assertEqual(mimetype, 'text/html')
        for text in [order.reference, 'Vestido floral', 'R$ 208,00', f'/pedidos/{order.pk}/', 'Ver o pedido']:
            self.assertIn(text, html)

    def test_email_failure_keeps_the_order_and_warns(self):
        from unittest import mock
        with mock.patch('orders.services.send_mail', side_effect=OSError('sem rede')):
            response = self.client.post('/checkout/', ADDRESS, follow=True)
        self.assertEqual(Order.objects.count(), 1)
        self.assertContains(response, 'Não foi possível enviar o e-mail de confirmação')

    def test_no_email_when_checkout_fails(self):
        from django.core import mail
        CartItem.objects.all().delete()
        self.client.post('/checkout/', ADDRESS)
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_buyer_without_email_still_buys_without_sending(self):
        from django.core import mail
        self.buyer.email = ''
        self.buyer.save()
        response = self.client.post('/checkout/', ADDRESS, follow=True)
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 0)
        self.assertContains(response, 'Não foi possível enviar o e-mail de confirmação')


class CheckoutAddressAndShippingTests(TestCase):
    def setUp(self):
        from accounts.models import UserProfile
        self.buyer = get_user_model().objects.create_user('comprador', 'ana@example.com', 'senha-segura-1')
        self.profile = UserProfile.objects.create(user=self.buyer, role='buyer')
        seller = get_user_model().objects.create_user('vendedor', 'loja@example.com', 'senha-segura-1')
        UserProfile.objects.create(user=seller, role='seller')
        self.product = Product.objects.create(seller=seller, name='Vestido floral', description='Botão faltando.',
                                              original_price=Decimal('160.00'), price=Decimal('104.00'), stock=5)
        CartItem.objects.create(cart=Cart.objects.create(user=self.buyer), product=self.product, quantity=2)
        self.client.force_login(self.buyer)

    def test_order_keeps_address_shipping_and_total(self):
        response = self.client.post('/checkout/', ADDRESS)
        order = Order.objects.get()
        self.assertRedirects(response, f'/pedidos/{order.pk}/')
        self.assertEqual(order.shipping_cost, Decimal('19.90'))
        self.assertEqual(order.subtotal, Decimal('208.00'))
        self.assertEqual(order.total, Decimal('227.90'))
        self.assertEqual((order.shipping_cep, order.shipping_street, order.shipping_number),
                         ('20040020', 'Rua da Assembleia', '10'))
        self.assertEqual((order.shipping_complement, order.shipping_district), ('sala 2', 'Centro'))
        self.assertEqual(order.shipping_location, 'Rio de Janeiro, RJ')

    def test_checkout_without_address_does_not_finalize(self):
        response = self.client.post('/checkout/', {})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Este campo é obrigatório')
        self.assertEqual(Order.objects.count(), 0)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 5)
        self.assertEqual(CartItem.objects.count(), 1)

    def test_each_missing_address_field_blocks_the_order(self):
        for field in ['cep', 'street', 'number', 'district', 'address_city', 'address_state']:
            with self.subTest(field=field):
                response = self.client.post('/checkout/', {**ADDRESS, field: ''})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(Order.objects.count(), 0)

    def test_invalid_cep_blocks_the_order(self):
        response = self.client.post('/checkout/', {**ADDRESS, 'cep': '123'})
        self.assertContains(response, 'CEP inválido')
        self.assertEqual(Order.objects.count(), 0)

    def test_complement_is_optional(self):
        self.client.post('/checkout/', {**ADDRESS, 'complement': ''})
        self.assertEqual(Order.objects.get().shipping_complement, '')

    def test_service_refuses_an_incomplete_address(self):
        from .services import CheckoutError, checkout_cart
        with self.assertRaises(CheckoutError):
            checkout_cart(self.buyer, {})
        with self.assertRaises(CheckoutError):
            checkout_cart(self.buyer, {'cep': '20040020', 'street': 'Rua A'})
        self.assertEqual(Order.objects.count(), 0)

    def test_values_come_from_the_server_not_from_the_post(self):
        self.client.post('/checkout/', {**ADDRESS, 'shipping_cost': '0', 'total': '1.00', 'price': '1.00'})
        order = Order.objects.get()
        self.assertEqual(order.shipping_cost, Decimal('19.90'))
        self.assertEqual(order.total, Decimal('227.90'))

    def test_checkout_page_shows_shipping_total_and_installments(self):
        response = self.client.get('/checkout/')
        self.assertContains(response, 'Endereço de entrega')
        self.assertEqual(response.context['payment']['total'], Decimal('227.90'))
        self.assertContains(response, 'R$ 227,90')
        self.assertContains(response, 'Em até <strong>6x de R$ 37,98</strong> sem juros', html=True)

    def test_checkout_comes_filled_with_the_profile_address(self):
        for key, value in {'cep': '01310100', 'street': 'Avenida Paulista', 'number': '1000',
                           'district': 'Bela Vista', 'location': 'São Paulo, SP'}.items():
            setattr(self.profile, f'address_{key}', value)
        self.profile.save()
        response = self.client.get('/checkout/')
        self.assertContains(response, 'value="01310-100"')
        self.assertContains(response, 'value="Avenida Paulista"')
        self.assertContains(response, '<option value="SP" selected>São Paulo</option>', html=True)

    def test_address_is_saved_to_profile_only_when_asked(self):
        self.client.post('/checkout/', ADDRESS)
        self.assertEqual(self.profile.__class__.objects.get(pk=self.profile.pk).address_street, '')

        CartItem.objects.create(cart=Cart.objects.get(user=self.buyer), product=self.product, quantity=1)
        self.client.post('/checkout/', {**ADDRESS, 'save_to_profile': 'on'})
        profile = self.profile.__class__.objects.get(pk=self.profile.pk)
        self.assertEqual((profile.address_cep, profile.address_street), ('20040020', 'Rua da Assembleia'))
        self.assertEqual(profile.address_location, 'Rio de Janeiro, RJ')

    def test_changing_the_profile_later_does_not_change_the_order(self):
        self.client.post('/checkout/', {**ADDRESS, 'save_to_profile': 'on'})
        self.profile.refresh_from_db()
        self.profile.address_street = 'Outra Rua'
        self.profile.save()
        self.assertEqual(Order.objects.get().shipping_street, 'Rua da Assembleia')

    def test_order_page_and_email_show_address_and_shipping(self):
        from django.core import mail
        response = self.client.post('/checkout/', ADDRESS, follow=True)
        for text in ['Rua da Assembleia, 10 - sala 2', 'Centro · Rio de Janeiro, RJ · CEP 20040-020',
                     'R$ 19,90', 'R$ 227,90']:
            self.assertContains(response, text)
        self.assertIn('Rua da Assembleia, 10 - sala 2', mail.outbox[0].body)
        self.assertIn('Frete: R$ 19,90', mail.outbox[0].body)
        self.assertIn('Total: R$ 227,90', mail.outbox[0].body)


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


class OrderCancellationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        from accounts.models import UserProfile

        cls.buyer = get_user_model().objects.create_user('comprador-cancelamento')
        cls.other_buyer = get_user_model().objects.create_user('outro-comprador')
        for user in [cls.buyer, cls.other_buyer]:
            UserProfile.objects.create(user=user, role='buyer')
        cls.product = Product.objects.create(
            name='Peça cancelável', original_price=Decimal('60.00'),
            price=Decimal('50.00'), stock=3,
        )
        cls.other_product = Product.objects.create(
            name='Outra peça cancelável', original_price=Decimal('80.00'),
            price=Decimal('60.00'), stock=4,
        )
        cls.order = Order.objects.create(
            user=cls.buyer, reference='FF-CANCELAR', status=Order.Status.PAID,
        )
        cls.item = OrderItem.objects.create(
            order=cls.order, product=cls.product, product_name=cls.product.name,
            unit_price=cls.product.price, quantity=2,
        )
        cls.other_item = OrderItem.objects.create(
            order=cls.order, product=cls.other_product, product_name=cls.other_product.name,
            unit_price=cls.other_product.price, quantity=1,
        )

    def setUp(self):
        self.detail_url = f'/pedidos/{self.order.pk}/'
        self.cancel_url = f'{self.detail_url}cancelar/'
        self.client.force_login(self.buyer)

    def assert_order_and_stock(self, status, first_stock=3, second_stock=4):
        self.order.refresh_from_db()
        self.product.refresh_from_db()
        self.other_product.refresh_from_db()
        self.assertEqual(self.order.status, status)
        self.assertEqual(self.product.stock, first_stock)
        self.assertEqual(self.other_product.stock, second_stock)

    def test_cancellation_restores_every_item_only_once(self):
        self.assertContains(self.client.get(self.detail_url), 'Confirmar cancelamento')
        response = self.client.post(self.cancel_url, follow=True)
        self.assertRedirects(response, self.detail_url)
        self.assertContains(response, 'Pedido cancelado.')
        self.assertNotContains(response, 'Confirmar cancelamento')
        self.assert_order_and_stock(Order.Status.CANCELLED, 5, 5)
        self.client.post(self.cancel_url)
        self.assert_order_and_stock(Order.Status.CANCELLED, 5, 5)

    def test_pending_order_can_be_cancelled(self):
        Order.objects.filter(pk=self.order.pk).update(status=Order.Status.PENDING)
        self.client.post(self.cancel_url)
        self.assert_order_and_stock(Order.Status.CANCELLED, 5, 5)

    def test_another_buyer_cannot_cancel(self):
        self.client.force_login(self.other_buyer)
        self.assertEqual(self.client.post(self.cancel_url).status_code, 404)
        self.assert_order_and_stock(Order.Status.PAID)

    def test_cancellation_requires_post(self):
        self.assertEqual(self.client.get(self.cancel_url).status_code, 405)
        self.assert_order_and_stock(Order.Status.PAID)

    def test_shipped_or_delivered_order_cannot_be_cancelled(self):
        for status in [Order.Status.SHIPPED, Order.Status.DELIVERED]:
            with self.subTest(status=status):
                Order.objects.filter(pk=self.order.pk).update(status=status)
                self.assertNotContains(self.client.get(self.detail_url), 'Confirmar cancelamento')
                self.client.post(self.cancel_url)
                self.assert_order_and_stock(status)

    def test_partial_dispatch_blocks_cancellation_and_preserves_stock(self):
        OrderItem.objects.filter(pk=self.other_item.pk).update(fulfillment_status=Order.Status.SHIPPED)
        self.assertNotContains(self.client.get(self.detail_url), 'Confirmar cancelamento')
        response = self.client.post(self.cancel_url, follow=True)
        self.assertContains(response, 'uma peça já foi enviada')
        self.assert_order_and_stock(Order.Status.PAID)

    def test_deleted_product_does_not_prevent_cancellation(self):
        self.product.delete()
        self.client.post(self.cancel_url)
        self.order.refresh_from_db()
        self.other_product.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.CANCELLED)
        self.assertEqual(self.other_product.stock, 5)
