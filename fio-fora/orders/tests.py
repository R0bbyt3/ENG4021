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
