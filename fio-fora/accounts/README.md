# accounts — contas e permissões

Login, cadastro, perfil, recuperação de senha, permissões e lista de usuários.

[← Voltar para a documentação principal](../README.md)

## Páginas

| URL | Página |
|---|---|
| `/` | Login (por e-mail) |
| `/cadastro/` | Escolha do tipo de conta |
| `/cadastro/comprador/`, `/cadastro/vendedor/`, `/cadastro/marca/` | Formulário de cadastro |
| `/conta/` | Perfil do usuário logado |
| `/recuperar-senha/` | Pedido de nova senha por e-mail |
| `/usuarios/` | Lista de usuários (só equipe) |
| `/logout/` | Sair |

> **[PRINT]** Tela de login.

> **[PRINT]** Tela "Como você quer usar o FioFora?" com as três opções de conta.

## Model

**`UserProfile`**: dados extras do usuário, ligado 1-para-1 ao `User` do Django.

- `role`: tipo de conta (`buyer`, `seller` ou `brand`).
- Dados de contato e de loja: `phone`, `store_name`, `document`, `location`,
    `legal_name`, `segment`, `social`.

## Arquivos principais

| Arquivo | O que tem |
|---|---|
| `forms.py` | Login por e-mail, cadastro de cada tipo de conta e perfil |
| `fields.py` | Campos brasileiros: CPF, CNPJ, telefone, estado, cidade e site/Instagram |
| `views.py` | Login, cadastro, perfil, recuperação de senha e lista de usuários |
| `decorators.py` | `buyer_required`, `seller_required`, `is_buyer`, `is_seller` |
| `context_processors.py` | Coloca `is_buyer` e `is_seller` em todos os templates |
| `backends.py` | Permite entrar com o e-mail no lugar do nome de usuário |
| `templates/accounts/auth_base.html` | Layout das telas de entrada (imagem à esquerda, formulário à direita) |

## Regras

- O cadastro cria o `User` e o `UserProfile` juntos.
- O e-mail também vira o nome de usuário.
- Vendedor exige CPF; marca exige CNPJ. Os dois têm os dígitos verificadores conferidos.
- O link de recuperação de senha vale por 60 minutos. Em desenvolvimento, o
    e-mail aparece no terminal onde o `runserver` está rodando.

## Campos brasileiros (`fields.py`)

O app é só para o Brasil. Cada campo mostra o formato esperado, abre o teclado
certo no celular, formata enquanto a pessoa digita (`static/js/masks.js`) e é
conferido de novo no servidor. No banco ficam só os números; a formatação volta
na hora de mostrar.

| Campo | Aceita | Guarda | Mostra |
|---|---|---|---|
| `CPFField` | `123.456.789-09` ou só números; confere os 2 dígitos verificadores | `12345678909` | `123.456.789-09` |
| `CNPJField` | Numérico ou com letras (novo, desde 2026); confere os 2 dígitos verificadores | `12ABC34501DE35` | `12.ABC.345/01DE-35` |
| `PhoneField` | Celular (11 números, começa com 9) ou fixo (10 números); DDD sem zero; tira o `+55` | `21999998888` | `(21) 99999-8888` |
| `CityField` + `StateField` | Cidade escrita e estado escolhido na lista das 27 UFs | `Rio de Janeiro, RJ` em `location` | Os dois campos separados |
| `SocialField` | `@perfil` ou site; link do Instagram vira `@perfil` | `@sualoja` | Igual |

Para usar em outro formulário: `phone = PhoneField(required=False)`.

## Como proteger uma view

```python
from accounts.decorators import seller_required

@seller_required
def minha_view(request):
    ...
```

No template, use `{% if is_seller %}` ou `{% if is_buyer %}`.

> **[PRINT]** Página "Minha conta" de um vendedor, com a seção "Loja e localização".

> **[PRINT]** Lista de usuários (`/usuarios/`) com algum filtro aplicado.
