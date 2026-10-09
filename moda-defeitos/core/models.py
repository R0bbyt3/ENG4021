from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models


class UserProfile(models.Model):
    class Role(models.TextChoices):
        BUYER = "buyer", "Comprador"
        SELLER = "seller", "Vendedor"
        BRAND = "brand", "Marca"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField("tipo de conta", max_length=10, choices=Role.choices, default=Role.BUYER)
    phone = models.CharField("telefone", max_length=20, blank=True)
    store_name = models.CharField("nome da loja/marca", max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "perfil de usuário"
        verbose_name_plural = "perfis de usuários"
        constraints = [models.CheckConstraint(condition=models.Q(role__in=["buyer", "seller", "brand"]), name="profile_valid_role")]

    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"


class Category(models.Model):
    name = models.CharField("nome", max_length=80, unique=True)
    slug = models.SlugField(unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "categoria"
        verbose_name_plural = "categorias"

    def __str__(self):
        return self.name


class Product(models.Model):
    # Campos originais preservados para manter o CRUD existente funcionando.
    name = models.CharField("nome", max_length=120)
    description = models.TextField("descrição")
    price = models.DecimalField("preço final", max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    is_active = models.BooleanField("produto ativo", default=True)
    created_at = models.DateTimeField("criado em", auto_now_add=True)
    sku = models.CharField(max_length=40, unique=True, null=True, blank=True)
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="products", null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, related_name="products", null=True, blank=True)
    brand = models.CharField("marca", max_length=100, blank=True)
    size = models.CharField("tamanho", max_length=20, blank=True)
    condition = models.CharField("estado da peça", max_length=80, blank=True)
    measurements = models.TextField("medidas", blank=True)
    original_price = models.DecimalField("preço original", max_digits=10, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(Decimal("0.01"))])
    stock = models.PositiveIntegerField("estoque", default=1)
    defect_type = models.PositiveSmallIntegerField("tipo do defeito", choices=[(1, "Estético"), (2, "Funcional reparável"), (3, "Funcional não reparável")], default=1, validators=[MinValueValidator(1), MaxValueValidator(3)])
    defect_location = models.PositiveSmallIntegerField("localização", choices=[(1, "Escondido"), (2, "Semivisível"), (3, "Visível")], default=1, validators=[MinValueValidator(1), MaxValueValidator(3)])
    defect_extent = models.PositiveSmallIntegerField("extensão", choices=[(1, "Pequena"), (2, "Média"), (3, "Grande")], default=1, validators=[MinValueValidator(1), MaxValueValidator(3)])
    defect_measure_cm = models.DecimalField("medida do defeito (cm)", max_digits=6, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)])
    visible_when_worn = models.BooleanField("visível com a peça vestida", default=False)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "produto"
        verbose_name_plural = "produtos"
        constraints = [
            models.CheckConstraint(condition=models.Q(price__gt=0), name="product_price_positive"),
            models.CheckConstraint(condition=models.Q(original_price__isnull=True) | models.Q(original_price__gte=models.F("price")), name="product_original_gte_price"),
            models.CheckConstraint(condition=models.Q(defect_type__range=(1, 3)) & models.Q(defect_location__range=(1, 3)) & models.Q(defect_extent__range=(1, 3)), name="product_valid_defect_scores"),
            models.CheckConstraint(condition=models.Q(defect_measure_cm__isnull=True) | models.Q(defect_measure_cm__gte=0), name="product_nonnegative_measure"),
        ]

    @property
    def severity(self):
        return Decimal("0.45") * self.defect_type + Decimal("0.35") * self.defect_location + Decimal("0.20") * self.defect_extent

    @property
    def severity_label(self):
        return "Leve" if self.severity <= Decimal("1.70") else "Moderada" if self.severity <= Decimal("2.30") else "Alta"

    @property
    def suggested_discount(self):
        raw = Decimal("15") + (self.severity - 1) / 2 * Decimal("35")
        return int((raw / 5).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * 5)

    @property
    def suggested_price(self):
        if self.original_price is None:
            return None
        return (self.original_price * (1 - Decimal(self.suggested_discount) / 100)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def __str__(self):
        return self.name


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image_path = models.CharField("caminho da foto", max_length=255)
    alt_text = models.CharField("descrição da imagem", max_length=160)
    is_defect = models.BooleanField("foto do defeito", default=False)

    class Meta:
        verbose_name = "foto de produto"
        verbose_name_plural = "fotos de produtos"
        constraints = [models.UniqueConstraint(fields=["product", "image_path"], name="unique_product_image")]

    def __str__(self):
        return self.alt_text


class Favorite(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favorites")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="favorites")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "favorito"
        verbose_name_plural = "favoritos"
        constraints = [models.UniqueConstraint(fields=["user", "product"], name="unique_user_favorite")]


class Cart(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cart")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "carrinho"
        verbose_name_plural = "carrinhos"


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="cart_items")
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])

    class Meta:
        verbose_name = "item do carrinho"
        verbose_name_plural = "itens do carrinho"
        constraints = [
            models.UniqueConstraint(fields=["cart", "product"], name="unique_cart_product"),
            models.CheckConstraint(condition=models.Q(quantity__gte=1), name="cart_quantity_positive"),
        ]


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

    @property
    def total(self):
        return sum((item.unit_price * item.quantity for item in self.items.all()), Decimal("0.00"))

    class Meta:
        verbose_name = "pedido"
        verbose_name_plural = "pedidos"
        constraints = [models.CheckConstraint(condition=models.Q(status__in=["pending", "paid", "shipped", "cancelled"]), name="order_valid_status")]

    def __str__(self):
        return self.reference


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, related_name="order_items", null=True, blank=True)
    # Cópia do nome/preço no momento da compra preserva o histórico.
    product_name = models.CharField(max_length=120)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])

    class Meta:
        verbose_name = "item do pedido"
        verbose_name_plural = "itens do pedido"
        constraints = [
            models.CheckConstraint(condition=models.Q(quantity__gte=1), name="order_quantity_positive"),
            models.CheckConstraint(condition=models.Q(unit_price__gt=0), name="order_unit_price_positive"),
        ]
