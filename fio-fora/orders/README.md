# orders — checkout e pedidos

Finalização da compra (simulada) e histórico de pedidos.

[← Voltar para a documentação principal](../README.md)

## Páginas

| URL | Página |
|---|---|
| `/checkout/` | Informar o endereço de entrega, revisar o carrinho e confirmar o pedido |
| `/pedidos/` | Histórico de pedidos do comprador |
| `/pedidos/<id>/` | Detalhe de um pedido |
| `/pedidos/<id>/cancelar/` | Ação POST para cancelar um pedido próprio ainda não enviado |
| `/minhas-vendas/` | Painel de pedidos com peças do vendedor ou da marca logada |

Checkout e histórico são áreas do comprador. Cada vendedor ou marca vê apenas
os próprios itens em Minhas vendas; tentar alterar um pedido sem itens próprios
retorna 404.

> **[PRINT]** Tela de checkout com o resumo do pedido.

## Models

- **`Order`**: pedido, com código de referência, status (pendente, pago,
    enviado, entregue, cancelado), **frete** (`shipping_cost`) e uma **cópia do
    endereço de entrega** (`shipping_cep`, `shipping_street`, `shipping_number`,
    `shipping_complement`, `shipping_district`, `shipping_location`).
    `subtotal` soma as peças e `total` é o subtotal mais o frete.
- **`OrderItem`**: item do pedido, com uma **cópia** do nome e do preço da peça
    no momento da compra. O status do item acompanha o do pedido até que o
    vendedor atualize a venda.

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
- O histórico do comprador conserva o nome e o preço mesmo se a peça for
    alterada ou apagada. O painel do vendedor usa o vínculo com a peça cadastrada.
- O vendedor pode avançar os status das próprias peças na ordem: pendente,
    pago, enviado e entregue. Em pedidos de várias lojas, o status geral indica
    a etapa alcançada por todas; o comprador também vê o status de cada item.
- O comprador pode cancelar um pedido próprio pendente ou pago até o
    primeiro envio. O pedido fica cancelado e as peças ainda cadastradas
    voltam ao estoque uma única vez, na mesma transação.
- **Aviso ao vendedor:** a compra e o cancelamento criam um aviso no sininho
    de cada vendedor ou marca do pedido (um por pedido, mesmo com várias
    peças), levando para Minhas vendas. O aviso entra na mesma transação: se a
    compra falha, ninguém é avisado. Veja o app [`notifications`](../notifications/README.md).

## Testes

`python manage.py test orders` cobre, em `tests.py`:

- **Estoque**: desconta a quantidade comprada, deixa a peça esgotada, bloqueia
    estoque insuficiente ou zerado, e cancela a compra inteira se um item falha.
- **Carrinho bloqueado**: carrinho vazio, peça própria, peça inativa e item
    indisponível (botão desabilitado).
- **Endereço e frete**: obrigatoriedade de cada campo, CEP inválido, frete e
    total calculados no servidor, endereço do perfil e cópia no pedido.
- **Acesso**: visitante vai para o login, vendedor volta para a vitrine com
    uma mensagem, e o pedido de outra pessoa dá 404.
- **E-mail de confirmação** com endereço e frete.

## Arquivos principais

| Arquivo | O que tem |
|---|---|
| `forms.py` | `CheckoutAddressForm`: endereço de entrega do checkout |
| `services.py` | `checkout_cart()`: cria o pedido com endereço e frete e desconta o estoque; `send_order_confirmation()`: e-mail de confirmação; `advance_sale()`: avança os itens do vendedor; `cancel_order()`: cancela e repõe o estoque; `items_by_seller()`: agrupa os itens por loja para os avisos |
| `views.py` | Checkout, lista e detalhe dos pedidos e painel de vendas |
| `templates/orders/email/` | Assunto, texto e versão HTML do e-mail de confirmação |

> **[PRINT]** Página de detalhe de um pedido confirmado.
