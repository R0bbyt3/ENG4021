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
