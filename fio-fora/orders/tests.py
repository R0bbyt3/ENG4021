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


class CheckoutTestCase(TestCase):
    """Base dos testes de compra: um comprador, um vendedor e uma peça com 5 unidades."""

    def setUp(self):
        from accounts.models import UserProfile
        User = get_user_model()
        self.buyer = User.objects.create_user('comprador', 'ana@example.com', 'senha-segura-1')
        UserProfile.objects.create(user=self.buyer, role='buyer')
        self.other_buyer = User.objects.create_user('outra', 'bia@example.com', 'senha-segura-1')
        UserProfile.objects.create(user=self.other_buyer, role='buyer')
        self.seller = User.objects.create_user('vendedor', 'loja@example.com', 'senha-segura-1')
        UserProfile.objects.create(user=self.seller, role='seller')
        self.dress = Product.objects.create(seller=self.seller, name='Vestido floral', description='Botão faltando.',
                                            original_price=Decimal('160.00'), price=Decimal('104.00'), stock=5)
        self.shirt = Product.objects.create(seller=self.seller, name='Camisa de linho', description='Mancha na barra.',
                                            original_price=Decimal('100.00'), price=Decimal('85.00'), stock=2)
        self.client.force_login(self.buyer)

    def put_in_cart(self, product, quantity=1, user=None):
        """Coloca a peça direto no carrinho, sem passar pelas regras do carrinho."""
        cart, _ = Cart.objects.get_or_create(user=user or self.buyer)
        return CartItem.objects.create(cart=cart, product=product, quantity=quantity)

    def buy(self, **extra):
        return self.client.post('/checkout/', {**ADDRESS, **extra})

    def stock_of(self, product):
        product.refresh_from_db()
        return product.stock

    def assertNothingWasBought(self, *products_and_stock):
        """Nenhum pedido, estoque como estava e carrinho intacto."""
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(OrderItem.objects.count(), 0)
        for product, stock in products_and_stock:
            self.assertEqual(self.stock_of(product), stock)
        self.assertTrue(CartItem.objects.filter(cart__user=self.buyer).exists())


class CheckoutStockTests(CheckoutTestCase):
    def test_purchase_takes_the_bought_quantity_out_of_stock(self):
        self.put_in_cart(self.dress, 2)
        self.buy()
        self.assertEqual(self.stock_of(self.dress), 3)

    def test_buying_the_last_units_leaves_the_piece_sold_out(self):
        self.put_in_cart(self.shirt, 2)
        self.assertRedirects(self.buy(), f'/pedidos/{Order.objects.get().pk}/')
        self.assertEqual(self.stock_of(self.shirt), 0)
        # Sem estoque, ninguém mais consegue pôr a peça no carrinho.
        self.client.force_login(self.other_buyer)
        self.client.post(f'/carrinho/adicionar/{self.shirt.pk}/', {'quantity': '1'})
        self.assertFalse(CartItem.objects.filter(cart__user=self.other_buyer).exists())

    def test_every_item_is_recorded_with_name_price_and_quantity(self):
        self.put_in_cart(self.dress, 2)
        self.put_in_cart(self.shirt, 1)
        self.buy()
        items = {item.product_name: item for item in Order.objects.get().items.all()}
        self.assertEqual(set(items), {'Vestido floral', 'Camisa de linho'})
        self.assertEqual((items['Vestido floral'].unit_price, items['Vestido floral'].quantity), (Decimal('104.00'), 2))
        self.assertEqual((items['Camisa de linho'].unit_price, items['Camisa de linho'].quantity), (Decimal('85.00'), 1))
        self.assertEqual(Order.objects.get().subtotal, Decimal('293.00'))
        self.assertEqual(Order.objects.get().total, Decimal('312.90'))
        self.assertEqual(self.stock_of(self.dress), 3)
        self.assertEqual(self.stock_of(self.shirt), 1)

    def test_cart_is_emptied_after_the_purchase(self):
        self.put_in_cart(self.dress, 1)
        self.buy()
        self.assertFalse(CartItem.objects.filter(cart__user=self.buyer).exists())

    def test_new_order_starts_pending_with_a_reference(self):
        self.put_in_cart(self.dress)
        self.buy()
        order = Order.objects.get()
        self.assertEqual(order.status, Order.Status.PENDING)
        self.assertEqual(order.user, self.buyer)
        self.assertRegex(order.reference, r'^FF-[0-9A-F]{12}$')

    def test_price_is_the_one_in_the_database_when_buying(self):
        self.put_in_cart(self.dress, 1)
        Product.objects.filter(pk=self.dress.pk).update(price=Decimal('90.00'))
        self.buy()
        self.assertEqual(Order.objects.get().items.get().unit_price, Decimal('90.00'))
        self.assertEqual(Order.objects.get().total, Decimal('109.90'))

    def test_insufficient_stock_blocks_the_purchase(self):
        self.put_in_cart(self.dress, 4)
        Product.objects.filter(pk=self.dress.pk).update(stock=3)
        response = self.client.post('/checkout/', ADDRESS, follow=True)
        self.assertRedirects(response, '/carrinho/')
        self.assertContains(response, 'Não foi possível finalizar “Vestido floral”. Só há 3 unidades em estoque')
        self.assertNothingWasBought((self.dress, 3))

    def test_sold_out_piece_blocks_the_purchase(self):
        self.put_in_cart(self.dress, 1)
        Product.objects.filter(pk=self.dress.pk).update(stock=0)
        response = self.client.post('/checkout/', ADDRESS, follow=True)
        self.assertContains(response, 'Não foi possível finalizar “Vestido floral”. Peça esgotada')
        self.assertNothingWasBought((self.dress, 0))

    def test_one_bad_item_cancels_the_whole_purchase(self):
        self.put_in_cart(self.dress, 1)
        self.put_in_cart(self.shirt, 2)
        Product.objects.filter(pk=self.shirt.pk).update(stock=1)
        self.buy()
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(self.stock_of(self.dress), 5)
        self.assertEqual(self.stock_of(self.shirt), 1)
        self.assertEqual(CartItem.objects.filter(cart__user=self.buyer).count(), 2)

    def test_stock_that_changes_during_the_purchase_rolls_everything_back(self):
        from unittest import mock
        # Simula outra compra que levou o estoque depois da conferência do carrinho.
        self.put_in_cart(self.dress, 1)
        self.put_in_cart(self.shirt, 2)
        Product.objects.filter(pk=self.shirt.pk).update(stock=1)
        with mock.patch('orders.services.unavailable_reason', return_value=None):
            response = self.client.post('/checkout/', ADDRESS, follow=True)
        self.assertContains(response, 'O estoque mudou')
        self.assertNothingWasBought((self.dress, 5), (self.shirt, 1))

    def test_double_submit_buys_only_once(self):
        self.put_in_cart(self.dress, 2)
        self.buy()
        second = self.client.post('/checkout/', ADDRESS, follow=True)
        self.assertRedirects(second, '/carrinho/')
        self.assertContains(second, 'Seu carrinho está vazio')
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(self.stock_of(self.dress), 3)


class CheckoutBlockedCartTests(CheckoutTestCase):
    def test_empty_cart_cannot_check_out(self):
        for response in [self.client.get('/checkout/', follow=True),
                         self.client.post('/checkout/', ADDRESS, follow=True)]:
            self.assertRedirects(response, '/carrinho/')
            self.assertContains(response, 'Seu carrinho está vazio')
        self.assertEqual(Order.objects.count(), 0)

    def test_cart_that_exists_but_has_no_items_cannot_check_out(self):
        Cart.objects.create(user=self.buyer)
        response = self.client.post('/checkout/', ADDRESS, follow=True)
        self.assertContains(response, 'Seu carrinho está vazio')
        self.assertEqual(Order.objects.count(), 0)

    def test_buyer_cannot_buy_their_own_piece(self):
        own = Product.objects.create(seller=self.buyer, name='Minha blusa', description='Fio puxado.',
                                     original_price=Decimal('60.00'), price=Decimal('40.00'), stock=3)
        self.put_in_cart(own, 1)
        response = self.client.post('/checkout/', ADDRESS, follow=True)
        self.assertContains(response, 'Você não pode comprar a sua própria peça')
        self.assertNothingWasBought((own, 3))

    def test_own_piece_blocks_the_whole_cart(self):
        own = Product.objects.create(seller=self.buyer, name='Minha blusa', description='Fio puxado.',
                                     original_price=Decimal('60.00'), price=Decimal('40.00'), stock=3)
        self.put_in_cart(self.dress, 1)
        self.put_in_cart(own, 1)
        self.buy()
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(self.stock_of(self.dress), 5)

    def test_inactive_piece_blocks_the_purchase(self):
        self.put_in_cart(self.dress, 1)
        Product.objects.filter(pk=self.dress.pk).update(is_active=False)
        response = self.client.post('/checkout/', ADDRESS, follow=True)
        self.assertContains(response, 'Não foi possível finalizar “Vestido floral”. Esta peça não está mais à venda')
        self.assertNothingWasBought((self.dress, 5))

    def test_checkout_page_blocks_the_button_when_an_item_is_unavailable(self):
        self.put_in_cart(self.dress, 1)
        Product.objects.filter(pk=self.dress.pk).update(is_active=False)
        response = self.client.get('/checkout/')
        self.assertTrue(response.context['has_unavailable'])
        self.assertContains(response, 'Ajuste os itens indisponíveis')
        self.assertContains(response, 'disabled>Finalizar pedido simulado')

    def test_unavailable_item_does_not_count_in_the_checkout_total(self):
        self.put_in_cart(self.dress, 1)
        self.put_in_cart(self.shirt, 1)
        Product.objects.filter(pk=self.shirt.pk).update(is_active=False)
        payment = self.client.get('/checkout/').context['payment']
        self.assertEqual(payment['subtotal'], Decimal('104.00'))
        self.assertEqual(payment['total'], Decimal('123.90'))


class CheckoutAccessTests(CheckoutTestCase):
    def test_anonymous_visitor_is_sent_to_login(self):
        self.client.logout()
        for url in ['/checkout/', '/pedidos/', '/pedidos/1/']:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 302)
                self.assertIn('/?next=', response['Location'])
        self.assertEqual(self.client.post('/checkout/', ADDRESS).status_code, 302)
        self.assertEqual(Order.objects.count(), 0)

    def test_seller_cannot_use_checkout_or_orders(self):
        self.client.force_login(self.seller)
        self.put_in_cart(self.dress, 1, user=self.seller)
        # Vendedor volta para a vitrine com a explicação, sem tela de erro.
        self.assertRedirects(self.client.get('/checkout/'), '/vitrine/')
        self.assertRedirects(self.client.post('/checkout/', ADDRESS), '/vitrine/')
        self.assertRedirects(self.client.get('/pedidos/'), '/vitrine/')
        self.assertEqual(Order.objects.count(), 0)

    def test_checkout_does_not_accept_other_methods(self):
        self.put_in_cart(self.dress, 1)
        self.assertEqual(self.client.put('/checkout/').status_code, 405)
        self.assertEqual(self.client.delete('/checkout/').status_code, 405)

    def test_checkout_only_uses_the_cart_of_the_logged_buyer(self):
        self.put_in_cart(self.dress, 1, user=self.other_buyer)
        response = self.client.post('/checkout/', ADDRESS, follow=True)
        self.assertContains(response, 'Seu carrinho está vazio')
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(self.stock_of(self.dress), 5)
        self.assertTrue(CartItem.objects.filter(cart__user=self.other_buyer).exists())


class OrderScreensTests(CheckoutTestCase):
    def make_order(self, user, reference, product=None, **extra):
        product = product or self.dress
        order = Order.objects.create(user=user, reference=reference, shipping_cost=Decimal('19.90'), **extra)
        OrderItem.objects.create(order=order, product=product, product_name=product.name,
                                 unit_price=product.price, quantity=1)
        return order

    def test_order_of_another_person_is_a_404(self):
        theirs = self.make_order(self.other_buyer, 'FF-DA-BIA')
        self.assertEqual(self.client.get(f'/pedidos/{theirs.pk}/').status_code, 404)

    def test_missing_order_is_a_404(self):
        self.assertEqual(self.client.get('/pedidos/9999/').status_code, 404)

    def test_buyer_sees_own_order_with_items_address_shipping_and_total(self):
        mine = self.make_order(self.buyer, 'FF-DA-ANA', shipping_cep='20040020', shipping_street='Rua da Assembleia',
                               shipping_number='10', shipping_district='Centro',
                               shipping_location='Rio de Janeiro, RJ')
        response = self.client.get(f'/pedidos/{mine.pk}/')
        self.assertEqual(response.status_code, 200)
        for text in ['FF-DA-ANA', 'Vestido floral', 'Rua da Assembleia, 10', 'CEP 20040-020',
                     'R$ 104,00', 'R$ 19,90', 'R$ 123,90']:
            self.assertContains(response, text)

    def test_old_order_without_address_still_opens(self):
        old = self.make_order(self.buyer, 'FF-ANTIGO')
        response = self.client.get(f'/pedidos/{old.pk}/')
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Endereço de entrega')

    def test_order_list_shows_only_my_orders_with_the_total_including_shipping(self):
        self.make_order(self.buyer, 'FF-DA-ANA')
        self.make_order(self.other_buyer, 'FF-DA-BIA')
        response = self.client.get('/pedidos/')
        self.assertContains(response, 'FF-DA-ANA')
        self.assertContains(response, 'R$ 123,90')
        self.assertNotContains(response, 'FF-DA-BIA')

    def test_new_order_shows_up_in_the_history(self):
        self.put_in_cart(self.dress, 1)
        self.buy()
        self.assertContains(self.client.get('/pedidos/'), Order.objects.get().reference)

    def test_order_list_without_orders_shows_the_empty_state(self):
        self.assertContains(self.client.get('/pedidos/'), 'Você ainda não fez nenhum pedido')

    def test_order_screens_do_not_accept_post(self):
        mine = self.make_order(self.buyer, 'FF-DA-ANA')
        self.assertEqual(self.client.post(f'/pedidos/{mine.pk}/').status_code, 405)
        self.assertEqual(self.client.post('/pedidos/').status_code, 405)

    def test_order_survives_when_the_piece_is_deleted(self):
        mine = self.make_order(self.buyer, 'FF-DA-ANA')
        self.dress.delete()
        response = self.client.get(f'/pedidos/{mine.pk}/')
        self.assertContains(response, 'Vestido floral')
        self.assertContains(response, 'R$ 123,90')


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
