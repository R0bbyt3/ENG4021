from django.contrib import admin

from .models import Peca, Vendedor


@admin.register(Vendedor)
class VendedorAdmin(admin.ModelAdmin):
    list_display = ("nome", "nota", "total_avaliacoes")
    search_fields = ("nome",)


@admin.register(Peca)
class PecaAdmin(admin.ModelAdmin):
    list_display = ("nome", "vendedor", "preco_original", "tipo_defeito", "localizacao_defeito", "extensao_defeito")
    list_filter = ("vendedor", "tipo_defeito", "localizacao_defeito", "extensao_defeito")
    search_fields = ("nome", "vendedor__nome")
