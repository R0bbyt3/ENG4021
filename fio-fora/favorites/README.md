# favorites — favoritos

Peças que o usuário guardou para ver depois.

[← Voltar para a documentação principal](../README.md)

## Páginas

| URL | Ação |
|---|---|
| `/favoritos/` | Lista de favoritos |
| `/favoritos/adicionar/<id>/` | Favoritar (POST) |
| `/favoritos/remover/<id>/` | Desfavoritar (POST) |

Só para contas de comprador. Vendedor e marca não veem o coração nem o link
no menu; se abrirem uma dessas páginas, voltam para a vitrine com uma mensagem.
Depois de favoritar, o comprador volta para a página onde estava.

> **[PRINT]** Página de favoritos com algumas peças.

## Model

**`Favorite`**: usuário + peça. A mesma peça não é favoritada duas vezes.

## Arquivos principais

| Arquivo | O que tem |
|---|---|
| `models.py` | `Favorite` e `mark_favorites()`, que marca nas peças se cada uma é favorita do usuário |
| `views.py` | Lista, adicionar e remover |
| `templates/favorites/includes/favorite_button.html` | Botão "Favoritar / Favoritada" da página da peça. Com `compact=True` vira só o coração, sobre a foto do card na vitrine e nos favoritos |

> **[PRINT]** Card da vitrine com o botão "Favoritada" ativo.
