# reviews — avaliações

Nota de 1 a 5 estrelas e comentário para as peças compradas, mostrados na
página da peça e na página da loja.

[← Voltar para a documentação principal](../README.md)

## Páginas

| URL | Ação |
|---|---|
| `/pedidos/itens/<id>/avaliar/` | Salva a avaliação de um item do pedido (POST, só o comprador dono do pedido) |

O formulário fica dentro do detalhe do pedido (`/pedidos/<id>/`), um por peça.
A nota média e as avaliações aparecem na página da peça e na página da loja.

> **[PRINT]** Detalhe de um pedido entregue com o formulário "Avaliar esta peça".

## Model

**`Review`**: avaliação de um item de pedido.

- `order_item`: um para um com o item, então cada peça comprada tem no máximo
    uma avaliação (o banco garante).
- `rating` (1 a 5) e `comment` (opcional).
- `stars`: a nota em estrelas de texto (★★★★☆).

## Regras

- **Só depois da entrega:** a peça pode ser avaliada quando o status dela é
    "Entregue", seja pelo "Confirmar entrega" do vendedor, seja pelo "Recebi a
    peça" do comprador. Antes disso, o pedido mostra "Você poderá avaliar esta
    peça quando a entrega for confirmada." A regra vale para avaliar e para
    editar.
- Pedido cancelado e peça apagada não podem ser avaliados.
- Em pedidos de várias lojas, cada peça é liberada quando a loja dela entrega.
- Avaliar de novo a mesma peça edita a avaliação, sem duplicar.
- Só o comprador dono do pedido avalia (outra pessoa recebe 404).
- **Aviso à loja:** uma avaliação nova avisa o vendedor ou a marca no sininho
    ("Ana deu 5 estrelas para Vestido floral."), com link para a página da
    peça. Editar a avaliação não gera outro aviso.
- Na página da peça aparecem a nota média, a quantidade e as 10 avaliações mais
    recentes, com só o primeiro nome de quem avaliou.

## Arquivos principais

| Arquivo | O que tem |
|---|---|
| `models.py` | `Review` |
| `forms.py` | `ReviewForm`: nota e comentário |
| `services.py` | `review_block_reason()`: por que uma peça ainda não pode ser avaliada; `attach_review_forms()`, `rating_summary()`, `product_reviews()` e `store_reviews()` |
| `views.py` | `review_save()`: cria ou edita a avaliação e avisa a loja |
| `templates/reviews/includes/item_review.html` | Formulário (ou aviso de espera) de cada peça no detalhe do pedido |
| `templates/reviews/includes/product_reviews.html` | Nota média e avaliações da página da peça |
