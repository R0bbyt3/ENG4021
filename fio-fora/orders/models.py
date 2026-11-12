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
        CANCELLED = "cancelled", "Cancelado"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders")
    reference = models.CharField(max_length=40, unique=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    # Cópia do endereço e do frete no momento da compra: mudar o perfil depois não altera o pedido.
    shipping_cost = models.DecimalField("frete", max_digits=8, decimal_places=2, default=Decimal("0.00"),
                                        validators=[MinValueValidator(Decimal("0.00"))])
    shipping_cep = models.CharField("CEP", max_length=8, blank=True)
    shipping_street = models.CharField("rua", max_length=150, blank=True)
    shipping_number = models.CharField("número", max_length=10, blank=True)
    shipping_complement = models.CharField("complemento", max_length=80, blank=True)
    shipping_district = models.CharField("bairro", max_length=100, blank=True)
    shipping_location = models.CharField("cidade e estado", max_length=120, blank=True)

    @property
    def subtotal(self):
        return sum((item.unit_price * item.quantity for item in self.items.all()), Decimal("0.00"))

    @property
    def total(self):
        return self.subtotal + self.shipping_cost

    @property
    def shipping_address_lines(self):
        """O endereço em duas linhas para mostrar na tela e no e-mail (vazio em pedidos antigos)."""
        if not self.shipping_street:
            return []
        street = f"{self.shipping_street}, {self.shipping_number}"
        if self.shipping_complement:
            street += f" - {self.shipping_complement}"
        cep = f"{self.shipping_cep[:5]}-{self.shipping_cep[5:]}" if len(self.shipping_cep) == 8 else self.shipping_cep
        return [street, f"{self.shipping_district} · {self.shipping_location} · CEP {cep}"]

    class Meta:
        verbose_name = "pedido"
        verbose_name_plural = "pedidos"
        constraints = [
            models.CheckConstraint(condition=models.Q(status__in=["pending", "paid", "shipped", "cancelled"]), name="order_valid_status"),
            models.CheckConstraint(condition=models.Q(shipping_cost__gte=0), name="order_shipping_not_negative"),
        ]

    def __str__(self):
        return self.reference


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, related_name="order_items", null=True, blank=True)
    # Cópia do nome/preço no momento da compra preserva o histórico.
    product_name = models.CharField(max_length=120)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])

    @property
    def subtotal(self):
        return self.unit_price * self.quantity

    class Meta:
        verbose_name = "item do pedido"
        verbose_name_plural = "itens do pedido"
        constraints = [
            models.CheckConstraint(condition=models.Q(quantity__gte=1), name="order_quantity_positive"),
            models.CheckConstraint(condition=models.Q(unit_price__gt=0), name="order_unit_price_positive"),
        ]
