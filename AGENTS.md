# AGENTS.md

Guia para agentes de IA que trabalham neste repositório. Siga estas regras
para manter o código no padrão que o projeto já usa. Em caso de dúvida, copie o
padrão de um arquivo vizinho do mesmo app.

## Contexto

- Projeto acadêmico (ENG4021). Aplicativo Django em `fio-fora/`.
- Público dos textos e do código: estudantes. Prefira **soluções simples**:
    views em função, ModelForm, templates com herança e include, CSS puro.
- Não adicione bibliotecas, JavaScript, frameworks de CSS, class-based views
    novas ou abstrações sem necessidade. O único JavaScript é
    `static/js/masks.js`, que formata CPF, CNPJ e telefone enquanto a pessoa digita.
- Pastas `Sprint N/` são só para entregas que **não são código**. Nunca coloque
    código nelas.

## Estrutura

```text
fio-fora/
├── config/        # só configuração (settings.py, urls.py)
├── templates/     # base.html e components/ compartilhados
├── static/        # css/, icons/, fonts/, images/ compartilhados
├── accounts/      # contas, UserProfile, permissões
├── products/      # Product, Defeito, vitrine, área do vendedor, simulador
├── cart/          # carrinho
├── orders/        # checkout e pedidos
├── favorites/     # favoritos
├── reviews/       # avaliações das peças compradas
└── seed/          # dados de exemplo (comando popular_banco)
```

Todo app tem: `models.py`, `views.py`, `urls.py`, `admin.py`, `tests.py`,
`migrations/`, `templates/<app>/`, `static/<app>/css/` e um `README.md`.
A exceção é o `seed/`, que não tem páginas nem models: só o comando
`popular_banco`, um arquivo por bloco de dados, as fotos em `images/`,
`tests.py` e `README.md`.

### Onde colocar cada coisa

| Coisa | Lugar |
|---|---|
| Nova funcionalidade de uma área existente | No app dessa área |
| Área nova e independente | Novo app, com a mesma estrutura dos outros |
| Regra de negócio usada por mais de um app | `<app>/services.py` |
| Verificação de permissão | `accounts/decorators.py` |
| Campo de dado brasileiro (CPF, CNPJ, telefone, UF) | `accounts/fields.py` |
| Dados de exemplo (contas, peças, fotos, pedidos) | `seed/`, no bloco do assunto |
| HTML usado por várias áreas | `templates/components/` |
| HTML de um app usado em outras páginas | `<app>/templates/<app>/includes/` |
| CSS usado por todas as páginas | `static/css/` (e importar em `site.css`) |
| CSS de um app | `<app>/static/<app>/css/<app>.css` |

**Não recrie um app `core`** nem arquivos como `seller_views.py`: cada área tem
o próprio `views.py`.

## Idioma e nomes

- **Código** (variáveis, funções, classes, campos, nomes de URL): inglês.
    Exceções já existentes do domínio: `Defeito`, `severidade()`,
    `classificar_severidade()`, `desconto_sugerido()`, `FAIXAS_SEVERIDADE`.
    Não renomeie essas.
- **Texto para o usuário** (templates, mensagens, labels, `verbose_name`): português.
- **Caminhos de URL**: português (`/minhas-pecas/`, `/carrinho/`).
- **Nomes de URL**: inglês, sem namespace e sem sufixo `_page`
    (`home`, `product_detail`, `cart`, `account`).
- **Comentários e docstrings**: português, curtos, explicando o porquê.

## Python

### Views

- Use views em função, `render`, `redirect` e `get_object_or_404`.
- Proteja com os decorators de `accounts/decorators.py`:

```python
from accounts.decorators import buyer_required, seller_required

@seller_required
def product_update(request, product_id):
    product = get_object_or_404(Product, pk=product_id, seller=request.user)
    ...
```

- Filtre pelo dono (`seller=request.user`, `user=request.user`) para que um
    usuário não veja nem altere dados de outro (resposta 404).
- Ações que mudam dados só por POST (`@require_POST` ou `if request.method == 'POST'`).
- Avise o usuário com `messages.success(...)` / `messages.error(...)`. O
    `base.html` já mostra as mensagens; não escreva laços de mensagens nos templates.
- Para formulários, use `Form(request.POST if request.method == 'POST' else None)`.
    Não use `request.POST or None`: um POST vazio deixaria o formulário sem validar.

### Models

- Regras de cálculo ficam no model (properties) ou em `services.py`, nunca no template ou no form.
- A fórmula de severidade existe **uma vez só**, em `products/models.py`. Reuse
    `severidade()`, `classificar_severidade()` e `desconto_sugerido()`.
- O preço final (`Product.price`) é calculado no servidor; nunca venha do POST.
- Depois de mudar um model: `python manage.py makemigrations`. Nunca edite
    migrations à mão.

### Forms

- Use `ModelForm` quando o form salva um model.
- **Não coloque classes CSS nos widgets** (`attrs={'class': ...}`). O CSS estiliza
    os campos dentro de `.form-field`. Atributos de comportamento
    (`autocomplete`, `min`, `autofocus`, `placeholder`, `inputmode`) podem ser usados.
- Para CPF, CNPJ, telefone, cidade/estado e site/Instagram, use os campos de
    `accounts/fields.py` (`CPFField`, `PhoneField`...) em vez de `CharField`.

## Templates

- Toda página estende `base.html` ou o `base.html` do próprio app
    (`products/base.html`, `orders/base.html`), que só acrescenta o CSS do app.
- Preencha `{% block title %}`, `{% block styles %}` (se precisar de CSS extra)
    e `{% block content %}`.
- Reuse os componentes em vez de copiar HTML:

| Precisa de | Use |
|---|---|
| Campos de formulário | `{% include 'components/form_fields.html' %}` |
| Um campo só | `{% include 'components/field.html' with field=form.nome %}` |
| Paginação | `{% include 'components/pagination.html' %}` (filtros: `with query=...`) |
| Card de peça | `{% include 'products/includes/card_info.html' %}` |
| Preço | `{% include 'products/includes/price.html' %}` |
| Favoritar | `{% include 'favorites/includes/favorite_button.html' with is_favorite=... %}` |
| Adicionar ao carrinho | `{% include 'cart/includes/add_button.html' %}` |

- Para mostrar algo conforme o tipo de conta, use `{% if is_buyer %}` ou
    `{% if is_seller %}`. Não repita a lógica `request.user.profile.role == ...`.
- Links sempre com `{% url 'nome' %}`; arquivos com `{% static '...' %}`.
- Formulários POST sempre com `{% csrf_token %}`.

## CSS

- Cores e raios vêm de `static/css/variables.css` (`var(--green)`, `var(--line)`...).
- Antes de criar uma classe, procure uma que já exista em `static/css/layout.css`
    e `static/css/controls.css`: `.button`, `.button--secondary`, `.button--danger`,
    `.panel`, `.two-columns`, `.page-heading`, `.hero`, `.section-heading`,
    `.empty-state`, `.eyebrow`, `.form-stack`, `.form-actions`, `.field-help`.
- CSS de um app fica no arquivo do app. Não crie um CSS por página.
- Nomes de classe em inglês, com hífen; variações com `--` (`.severity-badge--alta`).

## Testes

- Cada app tem um `tests.py`. Agrupe por assunto, não por sprint.
- Toda mudança de comportamento precisa de teste.
- Antes de terminar, rode dentro de `fio-fora/`:

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

## Documentação

- Ao criar ou mudar páginas, URLs ou regras de um app, atualize o `README.md` desse app.
- Textos para pessoas: curtos, diretos, em português.
- Espaços para imagens usam o formato:
    `> **[PRINT]** descrição do que a imagem deve mostrar.`

## Git

- Mensagens de commit em português, com um título curto e, se preciso, uma
    lista objetiva do que mudou.
- Não adicione coautoria de IA (`Co-Authored-By`) nos commits.
- Não faça commit de `db.sqlite3`, `.venv/` ou `__pycache__/`.
