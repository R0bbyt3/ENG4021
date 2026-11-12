# orders — checkout e pedidos

Finalização da compra (simulada) e histórico de pedidos.

[← Voltar para a documentação principal](../README.md)

## Páginas

| URL | Página |
|---|---|
| `/checkout/` | Informar o endereço de entrega, revisar o carrinho e confirmar o pedido |
| `/pedidos/` | Histórico de pedidos do comprador |
| `/pedidos/<id>/` | Detalhe de um pedido |

Todas as páginas são só para compradores.

> **[PRINT]** Tela de checkout com o resumo do pedido.

## Models

- **`Order`**: pedido, com código de referência, status (pendente, pago,
    enviado, cancelado), **frete** (`shipping_cost`) e uma **cópia do endereço de
    entrega** (`shipping_cep`, `shipping_street`, `shipping_number`,
    `shipping_complement`, `shipping_district`, `shipping_location`).
    `subtotal` soma as peças e `total` é o subtotal mais o frete.
- **`OrderItem`**: item do pedido, com uma **cópia** do nome e do preço da peça
    no momento da compra.

## Regras

- A compra é demonstrativa: não há pagamento nem entrega.
- O endereço é obrigatório (CEP, rua, número, bairro, cidade e estado; o
    complemento é opcional). Sem ele o pedido não é finalizado e nada é gravado.
    O formulário vem preenchido com o endereço do perfil e a pessoa pode trocá-lo;
    marcando "Salvar como meu endereço padrão", ele passa a ser o do perfil.
- O frete é fixo (R$ 19,90 por pedido) e o parcelamento é sem juros, em até 6
    vezes e com parcela mínima de R$ 30,00. As regras ficam em `cart/services.py`.
- Frete, total e parcelas são calculados no servidor a partir dos preços do
    banco: o navegador envia só o endereço.
- O pedido guarda uma cópia do endereço e do frete: mudar o perfil depois não
    altera pedidos antigos.
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
| `forms.py` | `CheckoutAddressForm`: endereço de entrega do checkout |
| `services.py` | `checkout_cart()`: cria o pedido com endereço e frete e desconta o estoque; `send_order_confirmation()`: e-mail de confirmação |
| `views.py` | Checkout, lista e detalhe dos pedidos |
| `templates/orders/email/` | Assunto, texto e versão HTML do e-mail de confirmação |

> **[PRINT]** Página de detalhe de um pedido confirmado.
