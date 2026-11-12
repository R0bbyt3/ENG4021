from django.conf import settings
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
    document = models.CharField('CPF ou CNPJ', max_length=14, blank=True)
    location = models.CharField('cidade e estado', max_length=120, blank=True)
    legal_name = models.CharField('razão social', max_length=150, blank=True)
    segment = models.CharField('atividade principal', max_length=20, blank=True)
    social = models.CharField('site ou Instagram', max_length=200, blank=True)
    # Endereço de entrega padrão do comprador (o checkout vem preenchido com ele).
    address_cep = models.CharField('CEP', max_length=8, blank=True)
    address_street = models.CharField('rua', max_length=150, blank=True)
    address_number = models.CharField('número', max_length=10, blank=True)
    address_complement = models.CharField('complemento', max_length=80, blank=True)
    address_district = models.CharField('bairro', max_length=100, blank=True)
    address_location = models.CharField('cidade e estado da entrega', max_length=120, blank=True)
    terms_accepted_at = models.DateTimeField('aceite dos termos', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "perfil de usuário"
        verbose_name_plural = "perfis de usuários"
        constraints = [models.CheckConstraint(condition=models.Q(role__in=["buyer", "seller", "brand"]), name="profile_valid_role")]

    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"
