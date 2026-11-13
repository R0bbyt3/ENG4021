from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4

from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models, transaction
from django.db.models import ExpressionWrapper, F


PESO_TIPO = Decimal("0.45")
PESO_LOCALIZACAO = Decimal("0.35")
PESO_EXTENSAO = Decimal("0.20")
LIMITE_LEVE = Decimal("1.70")
LIMITE_MODERADA = Decimal("2.30")
FAIXAS_SEVERIDADE = [("leve", "Leve"), ("moderada", "Moderada"), ("alta", "Alta")]


def severidade(tipo, localizacao, extensao):
    """Fórmula única de severidade (S = 0,45×Tipo + 0,35×Localização + 0,20×Extensão).

    Compartilhada pelo model Defeito e por qualquer simulação que ainda não
    tenha uma peça salva, para nunca existir uma segunda cópia da fórmula.
    """
    return PESO_TIPO * tipo + PESO_LOCALIZACAO * localizacao + PESO_EXTENSAO * extensao


def classificar_severidade(score):
    return "Leve" if score <= LIMITE_LEVE else "Moderada" if score <= LIMITE_MODERADA else "Alta"


def desconto_sugerido(score):
    raw = Decimal("15") + (score - 1) / 2 * Decimal("35")
    return int((raw / 5).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * 5)


class Category(models.Model):
    name = models.CharField("nome", max_length=80, unique=True)
    slug = models.SlugField(unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "categoria"
        verbose_name_plural = "categorias"

    def __str__(self):
        return self.name


class ProductQuerySet(models.QuerySet):
    def with_severity_band(self, band):
        """Filtra no banco pela faixa de severidade ("leve", "moderada" ou "alta").

        Usa os mesmos pesos e limites de severidade(), em centésimos inteiros,
        para não haver erro de arredondamento. Peças sem defeito ficam de fora.
        """
        score = ExpressionWrapper(
            F("defeito__tipo") * int(PESO_TIPO * 100)
            + F("defeito__localizacao") * int(PESO_LOCALIZACAO * 100)
            + F("defeito__extensao") * int(PESO_EXTENSAO * 100),
            output_field=models.IntegerField(),
        )
        products = self.annotate(severity_cents=score)
        leve, moderada = int(LIMITE_LEVE * 100), int(LIMITE_MODERADA * 100)
        if band == "leve":
            return products.filter(severity_cents__lte=leve)
        if band == "moderada":
            return products.filter(severity_cents__gt=leve, severity_cents__lte=moderada)
        if band == "alta":
            return products.filter(severity_cents__gt=moderada)
        raise ValueError(f"Faixa de severidade desconhecida: {band!r}")


class Product(models.Model):
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
    defect_measure_cm = models.DecimalField("medida do defeito (cm)", max_digits=6, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)])
    visible_when_worn = models.BooleanField("visível com a peça vestida", default=False)

    objects = ProductQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "produto"
        verbose_name_plural = "produtos"
        constraints = [
            models.CheckConstraint(condition=models.Q(price__gt=0), name="product_price_positive"),
            models.CheckConstraint(condition=models.Q(original_price__isnull=True) | models.Q(original_price__gte=models.F("price")), name="product_original_gte_price"),
            models.CheckConstraint(condition=models.Q(defect_measure_cm__isnull=True) | models.Q(defect_measure_cm__gte=0), name="product_nonnegative_measure"),
        ]

    @property
    def severity(self):
        # Tipo, localização e extensão agora vivem no model Defeito (ligado 1-para-1 à peça).
        return self.defeito.severity

    @property
    def severity_label(self):
        return classificar_severidade(self.severity)

    @property
    def suggested_discount(self):
        return desconto_sugerido(self.severity)

    @property
    def severity_band(self):
        return self.severity_label.lower()

    @property
    def defect_label(self):
        """Texto do selo do card. "Defeito" é masculino: leve, moderado, alto."""
        return {"leve": "Defeito leve", "moderada": "Defeito moderado", "alta": "Defeito alto"}[self.severity_band]

    @property
    def discount_percent(self):
        """Desconto real do anúncio, comparando o preço final com o original."""
        if not self.original_price or self.original_price <= self.price:
            return None
        return int(((1 - self.price / self.original_price) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    @property
    def suggested_price(self):
        if self.original_price is None:
            return None
        return (self.original_price * (1 - Decimal(self.suggested_discount) / 100)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @property
    def cover_image(self):
        """Foto que representa a peça no card.

        É a que o vendedor marcou como principal; enquanto ele não escolher
        nenhuma, vale a primeira foto que ele enviou.
        """
        gallery = [image for image in self.images.all() if not image.is_defect]
        chosen = next((image for image in gallery if image.is_cover), None)
        return chosen or (gallery[0] if gallery else None)

    @property
    def defect_image(self):
        """Foto do defeito. Sem ela a peça não deveria ir para a vitrine."""
        return next((i for i in self.images.all() if i.is_defect), None)

    def __str__(self):
        return self.name


class Defeito(models.Model):
    """Defeito de fabricação de uma peça: tipo, localização e extensão.

    Antes esses três critérios eram campos soltos em Product. Agora formam
    seu próprio model, ligado 1-para-1 à peça, o que deixa claro que o
    defeito é uma entidade própria (com sua nota de severidade) e não só um
    detalhe a mais do cadastro de produto.
    """

    TIPO_CHOICES = [(1, "Estético"), (2, "Funcional reparável"), (3, "Funcional não reparável")]
    LOCALIZACAO_CHOICES = [(1, "Escondido"), (2, "Semivisível"), (3, "Visível")]
    EXTENSAO_CHOICES = [(1, "Pequena"), (2, "Média"), (3, "Grande")]

    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name="defeito", verbose_name="peça")
    tipo = models.PositiveSmallIntegerField("tipo do defeito", choices=TIPO_CHOICES, default=1, validators=[MinValueValidator(1), MaxValueValidator(3)])
    localizacao = models.PositiveSmallIntegerField("localização", choices=LOCALIZACAO_CHOICES, default=1, validators=[MinValueValidator(1), MaxValueValidator(3)])
    extensao = models.PositiveSmallIntegerField("extensão", choices=EXTENSAO_CHOICES, default=1, validators=[MinValueValidator(1), MaxValueValidator(3)])

    class Meta:
        verbose_name = "defeito"
        verbose_name_plural = "defeitos"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(tipo__range=(1, 3)) & models.Q(localizacao__range=(1, 3)) & models.Q(extensao__range=(1, 3)),
                name="defeito_valid_scores",
            ),
        ]

    def __str__(self):
        return f"Defeito de {self.product.name}"

    @property
    def severity(self):
        return severidade(self.tipo, self.localizacao, self.extensao)

    @property
    def severity_label(self):
        return classificar_severidade(self.severity)

    @property
    def is_repairable(self):
        return self.tipo != 3


def detalhar_severidade(tipo, localizacao, extensao):
    """Quanto cada critério somou na nota, para o simulador explicar a conta.

    Devolve uma linha por critério, com o peso, a opção escolhida e o produto
    peso × nota. A soma das linhas é exatamente o que severidade() devolve:
    os pesos saem das mesmas constantes, sem repetir a fórmula.
    """
    criterios = [
        ("Tipo do defeito", PESO_TIPO, tipo, Defeito.TIPO_CHOICES),
        ("Localização", PESO_LOCALIZACAO, localizacao, Defeito.LOCALIZACAO_CHOICES),
        ("Extensão", PESO_EXTENSAO, extensao, Defeito.EXTENSAO_CHOICES),
    ]
    return [
        {
            "criterio": nome,
            "peso": peso,
            "nota": nota,
            "escolha": dict(opcoes).get(nota, nota),
            "soma": peso * nota,
        }
        for nome, peso, nota, opcoes in criterios
    ]


def product_image_path(instance, filename):
    """Uma pasta por peça, nome sorteado.

    O nome que o vendedor deu ao arquivo não entra no caminho: além de poder
    vazar informação (IMG_casa_joao.jpg), duas peças com "frente.jpg" se
    sobrescreveriam.
    """
    extension = filename.rsplit(".", 1)[-1].lower() or "jpg"
    return f"products/{instance.product_id}/{uuid4().hex}.{extension}"


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField("foto", upload_to=product_image_path)
    alt_text = models.CharField("descrição da imagem", max_length=160)
    is_defect = models.BooleanField("foto do defeito", default=False)
    is_cover = models.BooleanField("foto principal", default=False)
    created_at = models.DateTimeField("enviada em", auto_now_add=True)

    class Meta:
        # A foto do defeito vem primeiro: é ela que explica o desconto.
        # Depois vem a principal, que o vendedor escolheu para a vitrine.
        ordering = ["-is_defect", "-is_cover", "id"]
        verbose_name = "foto de produto"
        verbose_name_plural = "fotos de produtos"
        constraints = [
            models.UniqueConstraint(fields=["product", "image"], name="unique_product_image"),
            # Uma peça tem no máximo uma foto principal, garantido pelo banco.
            models.UniqueConstraint(fields=["product"], condition=models.Q(is_cover=True),
                                    name="unique_product_cover"),
        ]

    def __str__(self):
        return self.alt_text

    @property
    def can_be_removed(self):
        """A foto do defeito não sai pela lista: ela é trocada pelo formulário.

        Sem ela a peça não pode ser publicada, então removê-la deixaria o
        anúncio em um estado que o próprio cadastro recusa.
        """
        return not self.is_defect

    def make_cover(self):
        """Torna esta foto a principal da peça; a anterior deixa de ser.

        As duas gravações ficam na mesma transação por causa da restrição do
        banco: no meio do caminho a peça teria duas fotos principais.
        """
        with transaction.atomic():
            (ProductImage.objects.filter(product_id=self.product_id, is_cover=True)
             .exclude(pk=self.pk).update(is_cover=False))
            ProductImage.objects.filter(pk=self.pk).update(is_cover=True)
        self.is_cover = True

    def delete(self, *args, **kwargs):
        """Apagar o registro apaga o arquivo junto, senão o disco enche de
        imagem órfã que ninguém mais alcança pelo site."""
        image = self.image
        super().delete(*args, **kwargs)
        image.delete(save=False)
