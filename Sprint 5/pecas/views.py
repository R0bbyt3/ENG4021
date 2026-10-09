from django.shortcuts import get_object_or_404, render

from .models import Peca


def lista_pecas(request):
    """Vitrine: lê as peças do banco de dados e renderiza a tela de listagem."""
    pecas = Peca.objects.select_related("vendedor")
    return render(request, "pecas/lista.html", {"pecas": pecas})


def produto(request, pk):
    """Página do produto: busca uma peça no banco pelo id (404 se não existir)."""
    peca = get_object_or_404(Peca.objects.select_related("vendedor"), pk=pk)
    return render(request, "pecas/produto.html", {"peca": peca})
