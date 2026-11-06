# cart — carrinho

Carrinho do comprador.

[← Voltar para a documentação principal](../README.md)

## Páginas

| URL | Ação |
|---|---|
| `/carrinho/` | Ver o carrinho |
| `/carrinho/adicionar/<id>/` | Adicionar peça (POST, só comprador) |
| `/carrinho/itens/<id>/quantidade/` | Mudar a quantidade (POST) |
| `/carrinho/itens/<id>/remover/` | Remover item (POST) |

> **[PRINT]** Carrinho com dois itens e o resumo com o total.

## Models

- **`Cart`**: um carrinho por usuário.
- **`CartItem`**: peça e quantidade dentro do carrinho.

## Regras

- Só contas de comprador adicionam peças. Ninguém compra a própria peça.
- Estoque e disponibilidade são conferidos no servidor a cada ação.
- Preços e total vêm sempre do banco; o navegador envia só a quantidade.
- Itens indisponíveis continuam visíveis, mas ficam fora do total.
- Quantidade máxima por item: 99.

## Arquivos principais

| Arquivo | O que tem |
|---|---|
| `services.py` | Validação de quantidade e estoque e cálculo do total. Também é usado pelo checkout (`orders`). |
| `views.py` | Ver, adicionar, alterar e remover itens |
| `templates/cart/includes/add_button.html` | Botão "Adicionar ao carrinho", usado na página da peça |

> **[PRINT]** Carrinho com um item indisponível destacado.
