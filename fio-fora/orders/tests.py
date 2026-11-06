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
