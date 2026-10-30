from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db.models import ProtectedError
from django.test import TestCase

from .models import (
    Cart, CartItem, Category, Defeito, Favorite, Order, OrderItem, Product, ProductImage, UserProfile,
)


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
        ProductImage.objects.create(product=self.product, image_path="a.jpg", alt_text="foto")
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