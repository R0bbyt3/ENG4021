# orders — checkout e pedidos

Finalização da compra (simulada) e histórico de pedidos.

[← Voltar para a documentação principal](../README.md)

## Páginas

| URL | Página |
|---|---|
| `/checkout/` | Revisar o carrinho e confirmar o pedido |
| `/pedidos/` | Histórico de pedidos do comprador |
| `/pedidos/<id>/` | Detalhe de um pedido |

Todas as páginas são só para compradores.

> **[PRINT]** Tela de checkout com o resumo do pedido.

## Models

- **`Order`**: pedido, com código de referência e status (pendente, pago,
    enviado, cancelado).
- **`OrderItem`**: item do pedido, com uma **cópia** do nome e do preço da peça
    no momento da compra.

## Regras

- A compra é demonstrativa: não há pagamento nem entrega.
- Ao confirmar, o estoque é conferido de novo e descontado, tudo de uma vez
    (se um item falhar, nada é gravado).
- O carrinho é esvaziado depois do pedido.
- Depois de confirmar, o comprador recebe um e-mail com a referência, as peças,
    o total e o link do pedido, em texto e em HTML (`send_order_confirmation()`). Se o envio falhar, o
    pedido continua salvo e a tela avisa. O envio usa a mesma configuração de
    e-mail da recuperação de senha: por padrão aparece no terminal do servidor.
- O histórico não muda se a peça for alterada ou apagada depois.

## Arquivos principais

| Arquivo | O que tem |
|---|---|
| `services.py` | `checkout_cart()`: cria o pedido e desconta o estoque; `send_order_confirmation()`: e-mail de confirmação |
| `views.py` | Checkout, lista e detalhe dos pedidos |
| `templates/orders/email/` | Assunto, texto e versão HTML do e-mail de confirmação |

> **[PRINT]** Página de detalhe de um pedido confirmado.
