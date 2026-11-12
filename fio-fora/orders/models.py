from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from products.models import Product


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pendente"
        PAID = "paid", "Pago"
        SHIPPED = "shipped", "Enviado"
        DELIVERED = "delivered", "Entregue"
        CANCELLED = "cancelled", "Cancelado"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders")
    reference = models.CharField(max_length=40, unique=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def total(self):
        return sum((item.unit_price * item.quantity for item in self.items.all()), Decimal("0.00"))

    class Meta:
        verbose_name = "pedido"
        verbose_name_plural = "pedidos"
        constraints = [models.CheckConstraint(condition=models.Q(status__in=["pending", "paid", "shipped", "delivered", "cancelled"]), name="order_valid_status")]

    def __str__(self):
        return self.reference


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, related_name="order_items", null=True, blank=True)
    # Cópia do nome/preço no momento da compra preserva o histórico.
    product_name = models.CharField(max_length=120)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    # Sem status próprio, o item acompanha o status já registrado no pedido.
    fulfillment_status = models.CharField(
        max_length=12, null=True, blank=True,
        choices=[(value, label) for value, label in Order.Status.choices if value != Order.Status.CANCELLED],
        verbose_name="status da venda",
    )

    @property
    def sale_status(self):
        if self.order.status == Order.Status.CANCELLED:
            return Order.Status.CANCELLED
        return Order.Status(self.fulfillment_status or self.order.status)

    @property
    def subtotal(self):
        return self.unit_price * self.quantity

    class Meta:
        verbose_name = "item do pedido"
        verbose_name_plural = "itens do pedido"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(fulfillment_status__in=["pending", "paid", "shipped", "delivered"])
                | models.Q(fulfillment_status__isnull=True),
                name="order_item_valid_fulfillment_status",
            ),
            models.CheckConstraint(condition=models.Q(quantity__gte=1), name="order_quantity_positive"),
            models.CheckConstraint(condition=models.Q(unit_price__gt=0), name="order_unit_price_positive"),
        ]
