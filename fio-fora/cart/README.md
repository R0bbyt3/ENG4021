# cart — carrinho

Carrinho do comprador.

[← Voltar para a documentação principal](../README.md)

## Páginas

| URL | Ação |
|---|---|
| `/carrinho/` | Ver o carrinho |
| `/carrinho/adicionar/<id>/` | Adicionar peça (POST) |
| `/carrinho/itens/<id>/quantidade/` | Mudar a quantidade (POST) |
| `/carrinho/itens/<id>/remover/` | Remover item (POST) |

> **[PRINT]** Carrinho com dois itens e o resumo com o total.

## Models

- **`Cart`**: um carrinho por usuário.
- **`CartItem`**: peça e quantidade dentro do carrinho.

## Regras

- O carrinho inteiro é só de comprador. Vendedor e marca não veem o botão
    "Adicionar ao carrinho" nem o link do carrinho no menu; se abrirem uma
    dessas páginas, voltam para a vitrine com uma mensagem (`buyer_required`).
- Ninguém compra a própria peça.
- Estoque e disponibilidade são conferidos no servidor a cada ação.
- Preços e total vêm sempre do banco; o navegador envia só a quantidade.
- Itens indisponíveis continuam visíveis, mas ficam fora do total.
- O carrinho mostra subtotal, **frete fixo** (R$ 19,90, só quando há peças
    disponíveis), total e em quantas vezes dá para parcelar (sem juros, até 6x,
    parcela mínima de R$ 30,00). A página da peça e o checkout mostram o mesmo.
- Quantidade máxima por item: 99.

## Arquivos principais

| Arquivo | O que tem |
|---|---|
| `services.py` | Validação de quantidade e estoque, cálculo do total, frete (`shipping_for`) e parcelamento (`max_installments`, `purchase_summary`). Também é usado pelo checkout (`orders`) e pela página da peça (`products`). |
| `views.py` | Ver, adicionar, alterar e remover itens |
| `templates/cart/includes/add_button.html` | Botão "Adicionar ao carrinho", usado na página da peça |
| `templates/cart/includes/payment_info.html` | Frete e parcelamento (página da peça e checkout) |

> **[PRINT]** Carrinho com um item indisponível destacado.
