# notifications — avisos

Avisos dentro do site, mostrados no sininho do cabeçalho.

[← Voltar para a documentação principal](../README.md)

## Páginas

| URL | Página |
|---|---|
| `/avisos/` | Lista de avisos da pessoa logada, do mais novo para o mais antigo |

Exige login e vale para qualquer tipo de conta. Cada pessoa vê só os próprios
avisos.

> **[PRINT]** Cabeçalho com o sininho mostrando o número de avisos não lidos.

> **[PRINT]** Página de avisos com um aviso novo destacado.

## Model

**`Notification`**: um aviso para um usuário.

- `text`: o que aconteceu, gravado pronto na hora do evento.
- `url`: a página para onde o aviso leva.
- `created_at`: quando aconteceu.
- `read_at`: vazio enquanto a pessoa não viu o aviso.

## Regras

- O sininho aparece para quem está logado, com o número de avisos não lidos.
- Abrir `/avisos/` marca como lidos só os avisos daquela página (20 por
    página). Os da página 2 continuam novos até a pessoa abrir a página 2.
- Os avisos novos aparecem destacados na lista na primeira vez que são vistos.
- Quem cria os avisos são os outros apps, chamando `notify()`. Hoje:

| Evento | Quem recebe | Leva para |
|---|---|---|
| Compra finalizada | Cada vendedor ou marca do pedido (um aviso por pedido, mesmo com várias peças) | Minhas vendas |
| Comprador cancela o pedido | Cada vendedor ou marca do pedido | Minhas vendas |
| Vendedor confirma o pagamento, marca como enviado ou confirma a entrega | O comprador (a entrega avisa que já dá para avaliar) | Detalhe do pedido |
| Comprador clica em “Recebi a peça” | A loja das peças | Minhas vendas |
| Comprador avalia uma peça (só a avaliação nova) | A loja da peça | Página da peça |

- O aviso é criado dentro da mesma transação da ação que o gerou (compra,
    cancelamento, mudança de status): se a ação falhar, o aviso não existe.

## Como criar um aviso em outro app

```python
from notifications.services import notify

notify(user, 'Texto curto do que aconteceu.', reverse('nome_da_url'))
```

## Arquivos principais

| Arquivo | O que tem |
|---|---|
| `models.py` | `Notification` |
| `services.py` | `notify()`, `unread_count()` e `mark_read()` |
| `context_processors.py` | Coloca `unread_notifications` em todos os templates (número do sininho) |
| `views.py` | Lista de avisos |
| `templates/notifications/list.html` | Página de avisos |
