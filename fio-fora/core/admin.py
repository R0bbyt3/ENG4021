from django.contrib import admin

from .models import Product, Defeito, UserProfile, Category, ProductImage, Favorite, Cart, CartItem, Order, OrderItem


class DefeitoInline(admin.StackedInline):
    """Edita o defeito junto da peça, já que toda peça depende de ter um."""

    model = Defeito
    extra = 0
    max_num = 1
    can_delete = False


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """Admin da peça (Product). Tipo/localização/extensão do defeito agora
    vivem no model Defeito (ligado 1-para-1), editado aqui como inline."""

    inlines = [DefeitoInline]
    list_display = [
        'name',
        'brand',
        'categoria',
        'vendedor',
        'price',
        'original_price',
        'tipo_defeito',
        'localizacao_defeito',
        'extensao_defeito',
        'severity_label',
        'suggested_discount',
        'is_active',
        'created_at',
    ]
    list_filter = [
        'is_active',
        'category',
        'defeito__tipo',
        'defeito__localizacao',
        'defeito__extensao',
        'visible_when_worn',
    ]
    search_fields = ['name', 'description', 'brand', 'sku', 'seller__username', 'seller__email']
    list_select_related = ['category', 'seller', 'defeito']
    ordering = ['-created_at']

    @admin.display(description="categoria", ordering="category__name")
    def categoria(self, obj):
        return obj.category

    @admin.display(description="vendedor", ordering="seller__username")
    def vendedor(self, obj):
        return obj.seller

    @admin.display(description="tipo do defeito")
    def tipo_defeito(self, obj):
        return obj.defeito.get_tipo_display() if hasattr(obj, 'defeito') else "—"

    @admin.display(description="localização")
    def localizacao_defeito(self, obj):
        return obj.defeito.get_localizacao_display() if hasattr(obj, 'defeito') else "—"

    @admin.display(description="extensão")
    def extensao_defeito(self, obj):
        return obj.defeito.get_extensao_display() if hasattr(obj, 'defeito') else "—"

    @admin.display(description="gravidade")
    def severity_label(self, obj):
        return obj.severity_label if hasattr(obj, 'defeito') else "—"

    @admin.display(description="desconto sugerido")
    def suggested_discount(self, obj):
        return f"{obj.suggested_discount}%" if hasattr(obj, 'defeito') else "—"


@admin.register(Defeito)
class DefeitoAdmin(admin.ModelAdmin):
    """Admin próprio do defeito, para consultar e buscar sem passar pela peça."""

    list_display = ['product', 'tipo', 'localizacao', 'extensao', 'severity_label']
    list_filter = ['tipo', 'localizacao', 'extensao']
    search_fields = ['product__name', 'product__brand', 'product__sku']
    list_select_related = ['product']
    ordering = ['product__name']

    @admin.display(description="gravidade")
    def severity_label(self, obj):
        return obj.severity_label


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """Admin de usuários, usado também para gerenciar marcas/lojas (role=brand)."""

    list_display = ["user", "role", "store_name", "legal_name", "location", "phone"]
    list_filter = ["role", "segment"]
    search_fields = ["user__username", "user__email", "store_name", "legal_name", "document"]
    list_select_related = ["user"]


admin.site.register([Category, ProductImage, Favorite, Cart, CartItem, Order, OrderItem])