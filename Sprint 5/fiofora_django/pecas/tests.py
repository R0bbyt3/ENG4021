from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from .models import Peca, Vendedor


def criar_peca(**extra):
    vendedor = extra.pop("vendedor", None) or Vendedor.objects.create(
        nome="Aroma Studio", nota=Decimal("4.3"), total_avaliacoes=28
    )
    dados = dict(
        vendedor=vendedor,
        nome="Camisa de linho listrada",
        tamanho="M",
        tecido="100% linho",
        cor="areia",
        preco_original=Decimal("189.90"),
        tipo_defeito=1,
        localizacao_defeito=1,
        extensao_defeito=1,
        local_detalhe="forro interno",
        medida_cm=Decimal("1.5"),
        descricao_defeito="Mancha pequena na barra interna.",
    )
    dados.update(extra)
    return Peca.objects.create(**dados)


class CalculoDaPecaTests(TestCase):
    def test_defeito_leve_tem_15_por_cento(self):
        peca = criar_peca()
        self.assertEqual(peca.severidade, Decimal("1.00"))
        self.assertEqual(peca.faixa, "leve")
        self.assertEqual(peca.desconto_percentual, 15)
        self.assertEqual(peca.preco_final, Decimal("161.42"))

    def test_defeito_alto_tem_50_por_cento(self):
        peca = criar_peca(tipo_defeito=3, localizacao_defeito=3, extensao_defeito=3)
        self.assertEqual(peca.severidade, Decimal("3.00"))
        self.assertEqual(peca.faixa, "alta")
        self.assertEqual(peca.desconto_percentual, 50)

    def test_defeito_moderado(self):
        peca = criar_peca(tipo_defeito=2, localizacao_defeito=2, extensao_defeito=2)
        self.assertEqual(peca.severidade, Decimal("2.00"))
        self.assertEqual(peca.faixa, "moderada")
        self.assertEqual(peca.desconto_percentual, 35)  # 32,5% arredonda para 35%


class ViewsTests(TestCase):
    def test_lista_le_pecas_do_banco(self):
        criar_peca(nome="Peça do banco A")
        response = self.client.get(reverse("pecas:lista"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pecas/lista.html")
        self.assertContains(response, "Peça do banco A")

    def test_lista_vazia_mostra_aviso(self):
        response = self.client.get(reverse("pecas:lista"))
        self.assertContains(response, "Nenhuma peça cadastrada")

    def test_produto_mostra_dados_da_peca(self):
        peca = criar_peca()
        response = self.client.get(reverse("pecas:produto", args=[peca.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pecas/produto.html")
        self.assertContains(response, "Camisa de linho listrada")
        self.assertContains(response, "Aroma Studio")
        self.assertContains(response, "15% off")
        self.assertContains(response, "R$ 161,42")
        self.assertContains(response, "Severidade 1,00")

    def test_produto_inexistente_retorna_404(self):
        response = self.client.get(reverse("pecas:produto", args=[999]))
        self.assertEqual(response.status_code, 404)
