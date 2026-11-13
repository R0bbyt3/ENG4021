# seed — contas e dados de exemplo

Dados prontos para testar e apresentar o FioFora sem cadastrar nada à mão.

[← Voltar para a documentação principal](../README.md)

## Como usar

Dentro de `fio-fora/`, depois do `migrate`:

```bash
python manage.py popular_banco
```

Pode rodar de novo: o que já existe não é duplicado nem substituído. Para
voltar ao estado original, apague o `db.sqlite3` e a pasta `media/` e rode
`migrate` e `popular_banco` de novo.

> Use só no computador de vocês. Todas as contas têm a mesma senha e ela
> está escrita aqui.

## Contas disponíveis

Entre com o **e-mail** e a senha **`fiofora123`**.

| E-mail | Tipo | Quem é |
|---|---|---|
| `rafael@fiofora.com` | Comprador | Rafael Moreira, compra pensando em consumo consciente |
| `gabriel@fiofora.com` | Comprador | Gabriel Nunes, estudante que procura preço baixo |
| `julia@fiofora.com` | Vendedor | Julia Prado, da loja Brechó Segunda Volta (São Paulo) |
| `diego@fiofora.com` | Vendedor | Diego Souza, da loja Reuso Carioca (Rio de Janeiro) |
| `fabio@fiofora.com` | Marca | Fábio Rocha, da marca Ateliê Circular (São Paulo) |
| `gabriela@fiofora.com` | Marca | Gabriela Melo, da marca Fios do Rio (Rio de Janeiro) |
| `admin@fiofora.com` | Equipe | Acessa o `/admin/` e a lista de usuários |

### O que cada conta já tem

**Rafael (comprador)**
- Endereço de entrega salvo em São Paulo (Avenida Paulista), que já vem
    preenchido no checkout.
- 3 favoritos: camiseta de algodão, vestido estampado e calça jeans.
- Carrinho com a camisa de linho e 2 camisetas listradas.
- Pedido **enviado** com o vestido e a camiseta, os dois já avaliados.
- Pedido **pendente** com a calça de alfaiataria, ainda sem avaliação.

**Gabriel (comprador)**
- Endereço de entrega salvo no Rio de Janeiro (Rua Barata Ribeiro), que já
    vem preenchido no checkout.
- 2 favoritos: camiseta listrada e calça de alfaiataria.
- Carrinho com a calça jeans.
- Pedido **pago** com a calça jeans, já avaliada.
- Pedido **cancelado** com a jaqueta jeans, que não pode ser avaliada.

**Julia (vendedor)**: 3 peças. Uma delas, o vestido de malha, está
**esgotada** e mostra o aviso na página da peça. Tem **1 aviso não lido** no
sininho: a venda da calça de alfaiataria.

**Diego (vendedor)**: 3 peças. A camisa social está **pausada**: aparece em
"Minhas peças", mas não na vitrine. Tem 1 aviso já lido: o cancelamento
do pedido da jaqueta jeans.

**Fábio (marca)**: 2 peças. A camiseta tem avaliação, então a loja aparece
com nota média no card "Vendido por" da página da peça.

**Gabriela (marca)**: 2 peças. O vestido estampado tem avaliação nota 5.

**Equipe (admin)**: vê e edita tudo no `/admin/` e filtra as contas em
`/usuarios/`.

## O que é criado

| Dado | Quantidade |
|---|---|
| Contas | 7 (2 compradores, 2 vendedores, 2 marcas e a equipe) |
| Categorias | 6 (camisetas, camisas, calças, vestidos, saias e jaquetas) |
| Peças | 10, com defeitos das três faixas de severidade, 1 esgotada e 1 pausada |
| Fotos | 20 (a peça inteira e o close do defeito, de cada peça) |
| Favoritos | 5 |
| Carrinhos | 2 |
| Endereços de entrega | 2 (um em cada comprador) |
| Pedidos | 4 (pendente, pago, enviado e cancelado), cada um com o frete fixo e uma cópia do endereço do comprador |
| Avaliações | 3 |
| Avisos | 2 (um não lido para a Julia, um lido para o Diego) |

## Arquivos

Cada bloco cuida de uma parte dos dados e é chamado em ordem pelo comando.

| Arquivo | O que cria |
|---|---|
| `management/commands/popular_banco.py` | O comando: só chama os blocos abaixo em ordem |
| `users.py` | Bloco 1: contas e perfis, com o endereço dos compradores (e a senha de todas) |
| `catalog.py` | Bloco 2: categorias, peças, defeitos e fotos |
| `shopping.py` | Bloco 3: favoritos e carrinhos |
| `purchases.py` | Bloco 4: pedidos (com frete e endereço) e avaliações |
| `notifications.py` | Bloco 5: avisos do sininho |
| `images/` | Fotos das peças: `<nome>.jpg` e `<nome>-defeito.jpg` |
| `tests.py` | Confere que o comando roda, não duplica e que as contas entram |

Para trocar uma foto por uma real, substitua o arquivo em `images/` mantendo o
mesmo nome. Para incluir uma peça, acrescente um item em `PRODUCTS`, no
`catalog.py`, e as duas fotos dela em `images/`.
