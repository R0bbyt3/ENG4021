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
- Endereço de entrega padrão do comprador: `address_cep`, `address_street`,
    `address_number`, `address_complement`, `address_district`, `address_location`
    (cidade e estado juntos, como em `location`).
- `display_name`: nome público da loja ou marca, usado pela página da marca.
    Quem vende sem nome de loja aparece pelo próprio nome.

## Arquivos principais

| Arquivo | O que tem |
|---|---|
| `forms.py` | Login por e-mail, cadastro de cada tipo de conta e perfil |
| `fields.py` | Campos brasileiros: CPF, CNPJ, telefone, CEP, estado, cidade e site/Instagram |
| `views.py` | Login, cadastro, perfil, recuperação de senha e lista de usuários |
| `decorators.py` | `buyer_required`, `seller_required`, `is_buyer`, `is_seller` |
| `context_processors.py` | Coloca `is_buyer` e `is_seller` em todos os templates |
| `backends.py` | Permite entrar com o e-mail no lugar do nome de usuário |
| `templates/accounts/auth_base.html` | Layout das telas de entrada (imagem à esquerda, formulário à direita) |

## Regras

- O cadastro cria o `User` e o `UserProfile` juntos.
- A caixa "Li e aceito os termos..." tem embaixo os links para os termos de
    uso e a política de privacidade, que abrem em outra aba para a pessoa não
    perder o que já preencheu. O aceite fica salvo em `terms_accepted_at`.
- O e-mail também vira o nome de usuário.
- Vendedor exige CPF; marca exige CNPJ. Os dois têm os dígitos verificadores conferidos.
- O comprador pode guardar um endereço de entrega no perfil (`/conta/`). Ele é
    opcional, mas não pode ficar pela metade. O checkout vem preenchido com ele.
    Vendedores e marcas não têm esse campo.
- O link de recuperação de senha vale por 60 minutos. Em desenvolvimento, o
    e-mail aparece no terminal onde o `runserver` está rodando.
- O e-mail de recuperação tem duas versões, texto e HTML, em
    `templates/accounts/email/`. O assunto é "Recuperação de senha - FioFora".
- Se o servidor de e-mail falhar, o erro aparece no log do servidor (o terminal
    do `runserver`) e a tela continua igual, para não revelar quem tem conta. Por
    isso, ao testar o envio real, olhe o terminal se o e-mail não chegar.

## Envio real de e-mail

Sem configuração, o e-mail só aparece no terminal. Para enviar de verdade
(recuperação de senha e confirmação de pedido), defina estas variáveis de
ambiente **antes** de rodar o servidor. Elas ficam só na sua máquina; nunca
escreva a senha em arquivo do repositório.

| Variável | Para que serve | Exemplo (Gmail) |
|---|---|---|
| `EMAIL_BACKEND` | Liga o envio real | `django.core.mail.backends.smtp.EmailBackend` |
| `EMAIL_HOST` | Servidor SMTP | `smtp.gmail.com` |
| `EMAIL_PORT` | Porta | `587` |
| `EMAIL_USE_TLS` | Conexão segura (`1` liga) | `1` |
| `EMAIL_HOST_USER` | Conta que envia | `sua.conta@gmail.com` |
| `EMAIL_HOST_PASSWORD` | Senha de app da conta (não é a senha normal) | gerada na conta Google |
| `DEFAULT_FROM_EMAIL` | Remetente que aparece | `FioFora <sua.conta@gmail.com>` |
| `EMAIL_TIMEOUT` | Segundos de espera pelo servidor (padrão 10) | `10` |

Para testar a configuração, sem abrir o site:

```bash
python manage.py sendtestemail seu.email@exemplo.com
```

Depois peça uma recuperação de senha em `/recuperar-senha/` com um e-mail
cadastrado e confira a caixa de entrada (e o spam).

> **[PRINT]** E-mail de recuperação de senha recebido na caixa de entrada.

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

## Regra do comprador e do vendedor

Carrinho, favoritos, checkout, pedidos e avaliações são só de **comprador**.
Vendedor e marca podem ver as peças, mas não compram nem favoritam:

- As telas escondem o que daria erro: o botão "Adicionar ao carrinho" vira um
    aviso, o coração de favoritar some e o menu não mostra Carrinho nem Favoritos.
- Se o vendedor abrir uma dessas páginas pelo endereço, `buyer_required` o leva
    de volta à vitrine com uma única mensagem (`BUYER_ONLY_MESSAGE`), em vez de
    uma tela de erro.
- Já as áreas de vendedor (`seller_required`) continuam respondendo 403 para
    comprador.

Os testes por tipo de conta ficam em `BuyerOnlyAreasTests`, no `tests.py`.

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
