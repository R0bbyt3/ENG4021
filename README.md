# ENG4021

## Moda com Pequenos Defeitos, Preço Justo

Projeto da disciplina **ENG4021 — Projeto de Software**.

A proposta é criar uma plataforma para divulgar peças de roupa com pequenos
defeitos de fabricação, explicando o defeito e o desconto aplicado de forma
transparente.

## 1. Organização geral do projeto

Este repositório reúne os materiais desenvolvidos ao longo das sprints e o
aplicativo web principal. A organização geral é:

```text
ENG4021/
├── README.md                 # Documentação geral do projeto
├── Sprint 0/                 # Materiais e exercícios da Sprint 0
├── Sprint 1/                 # Materiais e exercícios da Sprint 1
├── Sprint 2/                 # Materiais e exercícios da Sprint 2
├── ...                       # Próximas sprints
└── fio-fora/                 # Repositório específico do aplicativo Django
```

### Guia de organização

- Todo arquivo, exercício, código ou documentação referente a uma sprint deve
    ficar dentro da pasta correspondente: `Sprint 0`, `Sprint 1`, `Sprint 2` e
    assim por diante.
- A pasta de uma sprint deve reunir apenas os materiais daquela etapa, para
    que seja possível acompanhar a evolução do projeto sem misturar versões ou
    atividades diferentes.
- A pasta `fio-fora` contém o projeto codado do aplicativo e sua própria
    estrutura Django. A explicação técnica dessa parte está documentada a partir
    da seção seguinte.
- Este `README.md` apresenta primeiro a organização geral do repositório e,
    depois, a instalação, a arquitetura e o estado atual do aplicativo.

## 2. Repositório específico do aplicativo: `fio-fora`

Esta é a parte do projeto que já foi implementada em código. O aplicativo é uma
plataforma Django para exibir produtos com pequenos defeitos de fabricação,
informar o defeito e apresentar um preço reduzido de forma transparente. Os
arquivos do sistema ficam dentro de `fio-fora/`; as pastas de sprint não
fazem parte da estrutura interna do aplicativo.

### 2.1 Instalação

### Instalar o Python

Se necessário, antes de instalar o projeto, instale o Python no seu computador. Baixe sempre
o instalador no site oficial: <https://www.python.org/downloads/>.

#### Windows

1. Acesse o site do Python e baixe a versão para Windows.
2. Execute o instalador baixado.
3. Na primeira tela, marque **Add python.exe to PATH**.
4. Clique em **Install Now** e aguarde a conclusão.
5. Abra o PowerShell e confirme a instalação:

```powershell
python --version
```

Se aparecer a versão do Python, a instalação está pronta.

#### macOS

1. Acesse o site do Python e baixe o instalador para macOS (`.pkg`).
2. Abra o arquivo baixado e siga as etapas do instalador.
3. Ao terminar, abra o Terminal e confirme a instalação:

```bash
python3 --version
```

Se aparecer a versão do Python, a instalação está pronta.

#### Fedora Linux

1. Abra o Terminal.
2. Instale o Python e o `pip` usando o gerenciador de pacotes do Fedora:

```bash
sudo dnf install python3 python3-pip
```

3. Confirme a instalação:

```bash
python3 --version
```

Se aparecer a versão do Python, a instalação está pronta.

### Inicializar e rodar o projeto

Se você está na pasta `ENG4021`, entre na pasta do projeto:

```bash
cd fio-fora
```

Depois, use os comandos do seu sistema abaixo.

#### Codespace, Linux e macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m django --version
python manage.py migrate
python manage.py check
python manage.py runserver
```

#### Windows (PowerShell)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m django --version
python manage.py migrate
python manage.py check
python manage.py runserver
```

O comando `python manage.py migrate` cria as tabelas internas que o Django
precisa para funcionar, como as tabelas de usuários, sessões e administração.

Depois, acesse <http://127.0.0.1:8000/> no navegador. Para parar o servidor,
use `Ctrl+C`.

## 2.2 Tecnologias utilizadas

- Python
- Django
- HTML e CSS

## 2.3 Padrões de projeto

O projeto segue a organização natural do Django, baseada no padrão
**Model-Template-View (MTV)**. Em muitos materiais em português, esse mesmo
jeito de organizar o Django aparece como **MVT**. A ideia é a mesma: separar os
dados, a aparência da página e o código que responde às ações do usuário.

Esse padrão é realmente usado no Django. A documentação oficial apresenta
separadamente o model, a view, o template, as URLs e os formulários, e mostra
como eles trabalham juntos. Veja o exemplo oficial em
<https://docs.djangoproject.com/en/6.1/intro/overview/>.

```text
URL → View → Model/Form → Template → HTML + CSS
```

Na Home, a URL chama a `home`, que busca os `Product` e envia a lista para o
template. No cadastro, a URL chama outra view, que usa o `ProductForm`, salva o
produto e redireciona para a Home.

### Estrutura interna de `fio-fora`

```text
fio-fora/
├── manage.py                 # Comandos do Django
├── requirements.txt          # Dependências do projeto
├── README.md                 # Guia do projeto
├── config/                   # Configuração geral do projeto
│   ├── settings.py           # Configurações e apps instalados
│   ├── urls.py               # URLs principais do projeto
│   ├── asgi.py               # Entrada para servidores ASGI
│   └── wsgi.py               # Entrada para servidores WSGI
└── core/                     # Aplicação principal
    ├── models.py             # Modelos e tabelas do sistema
    ├── views.py              # Lógica das páginas e requisições
    ├── urls.py               # URLs específicas da aplicação
    ├── forms.py              # Formulários do Django
    ├── admin.py              # Registro no Django Admin
    ├── tests.py              # Testes da aplicação
    ├── templates/core/       # Páginas HTML
    ├── static/core/          # Arquivos CSS
    └── migrations/           # Histórico das alterações dos modelos
```

### O que cada parte faz usando o produto como exemplo

#### 1. `config/settings.py`: configurações do projeto

Esse arquivo diz ao Django quais recursos o projeto usa. É em `settings.py` que ficam
configurações gerais, como templates, arquivos estáticos e banco de dados.
Não é o lugar para escrever a lógica do produto.

Exemplo: registrar a aplicação `core`:

```python
INSTALLED_APPS = [
    # apps do Django...
    'core',
]
```

#### 2. `config/urls.py` e `core/urls.py`: caminhos das páginas

As URLs dizem o que deve acontecer quando alguém acessa um endereço.
`config/urls.py` é a entrada principal e encaminha as URLs da aplicação para
`core/urls.py`.

Por exemplo, em `core/urls.py`, o caminho `/` chama a view da vitrine e o
caminho `/produtos/novo/` chama a view do cadastro.

```python
path('', views.home, name='home'),
path('produtos/novo/', views.product_create, name='product_create')
```

#### 3. `core/models.py`: os dados do produto

O model é uma classe Python que representa um tipo de dado salvo no banco. No
nosso exemplo, `Product` representa um produto da vitrine:

```python
class Product(models.Model):
    name = models.CharField(max_length=120)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
```

Cada atributo vira um campo do produto. Assim, `name` guarda o nome, `description`
guarda a explicação do defeito, `price` guarda o preço e `is_active` informa se
ele aparece na vitrine. `created_at` registra automaticamente quando o produto
foi criado.

#### 4. `core/forms.py`: formulário para cadastrar o produto

O `ProductForm` usa o model `Product` para montar um formulário HTML. Quando a
pessoa digita o nome, o defeito e o preço, o Django verifica os dados e depois
salva o produto.

Isso evita escrever manualmente toda a validação e mantém o formulário ligado
ao model. Se um campo for adicionado ao model, podemos incluí-lo no formulário
pela lista `fields`.

```python
class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'description', 'price', 'is_active']
```

#### 5. `core/views.py`: o que acontece em cada página

A view é uma função Python que recebe a requisição e devolve uma resposta.
Por exemplo, a view `home` busca os produtos ativos:

```python
products = Product.objects.filter(is_active=True)
return render(request, 'core/home.html', {'products': products})
```

Ela busca os dados no model e envia esses dados para o template. As outras
views fazem o cadastro, a edição e a remoção de produtos.

No cadastro, a view salva o formulário e volta para a Home:

```python
if form.is_valid():
    form.save()
    return redirect('home')
```

#### 6. `core/templates/core/`: o HTML que a pessoa vê

Os templates são as páginas HTML. Primeiro, o arquivo `base.html` guarda a
estrutura comum do site, como o cabeçalho e o carregamento do CSS.

Os outros templates reaproveitam essa estrutura usando:

```html
{% extends 'core/base.html' %}
```

Assim, não precisamos copiar o mesmo cabeçalho em todas as páginas. Depois, o
`home.html` recebe a lista `products` enviada pela view e mostra cada produto.

Para mostrar os produtos, o template percorre a lista recebida:

```html
{% for product in products %}
    <div class="product-card">
        <h3>{{ product.name }}</h3>
        <p><strong>Defeito:</strong> {{ product.description }}</p>
        <p class="price">R$ {{ product.price }}</p>
    </div>
{% endfor %}
```

#### 7. `core/static/core/style.css`: a aparência da página

O CSS define cores, espaçamento, tamanho dos textos e organização dos cards de
produto. Ele fica separado do Python e do HTML.

No template, `{% load static %}` e `{% static 'core/style.css' %}` informam ao
Django onde encontrar esse arquivo. Para mudar a aparência da vitrine, altere
`core/static/core/style.css`, não `views.py`.

Exemplo de estilo para o preço:

```css
.price {
    color: #914936;
    font-weight: bold;
}
```

#### 8. `core/admin.py`: gerenciamento pelo Admin

Ao registrar `Product` em `admin.py`, o produto pode ser criado, editado e
removido pela página `/admin/`. O Admin é uma forma rápida de cadastrar e
organizar os produtos da vitrine.

```python
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'is_active']
```

#### 9. `core/tests.py`: verificar se o código funciona

Os testes simulam ações sem precisar abrir o navegador. Um teste pode conferir,
por exemplo, se a Home responde com sucesso ou se um produto criado aparece na
vitrine.

```python
def test_home_abre(self):
    response = self.client.get('/')
    self.assertEqual(response.status_code, 200)
```

#### 10. `core/migrations/`: registrar mudanças no banco

Quando alteramos o model, o Django precisa atualizar a estrutura do banco. Não
editamos os arquivos dessa pasta manualmente. Usamos:

```bash
python manage.py makemigrations
python manage.py migrate
```

`makemigrations` registra a mudança e `migrate` aplica a mudança no banco.

`manage.py` reúne os comandos do projeto, como iniciar o servidor, criar
migrations e executar testes. Ele normalmente não precisa ser alterado.

## 2.4 Estado atual das funcionalidades

Neste momento, o projeto já possui uma primeira funcionalidade demonstrável:

- estrutura `config` criada pelo comando oficial `django-admin startproject`;
- aplicação `core` criada pelo comando oficial `python manage.py startapp core`;
- ambiente virtual criado em `.venv`;
- Django registrado em `requirements.txt`;
- app `core` registrado em `INSTALLED_APPS`;
- migrations aplicadas com `python manage.py migrate`;
- vitrine na página inicial (`/`), mostrando os produtos ativos;
- cadastro de produto em `/produtos/novo/`;
- edição de produto em `/produtos/<id>/editar/`;
- remoção de produto em `/produtos/<id>/remover/`;
- gerenciamento dos produtos pelo Django Admin em `/admin/`;
- verificação básica disponível com `python manage.py check`.

O cadastro demonstra o fluxo completo de um CRUD: o produto é definido em
`core/models.py`, preenchido por um `ModelForm`, processado pelas views e
apresentado pelos templates HTML com CSS.

Os models também incluem critérios de severidade, cálculo de desconto e dados
de imagens, categorias, carrinho e pedidos. A integração desses recursos nas
telas ainda está em andamento.

O cadastro de compradores, vendedores e marcas é processado pelo app `accounts`,
com validação dos dados, senha protegida e criação do perfil no banco. Após
atualizar o código, execute `python manage.py migrate` dentro de `fio-fora`.
