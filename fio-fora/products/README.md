# products — catálogo e área do vendedor

Vitrine, página da peça, cadastro de peças pelo vendedor e simulador de desconto.

[← Voltar para a documentação principal](../README.md)

## Páginas

| URL | Página | Quem acessa |
|---|---|---|
| `/vitrine/` | Vitrine com filtros combináveis, busca e ordenação | Todos |
| `/sobre/` | Proposta, critérios, origem dos pesos e caráter acadêmico | Todos |
| `/termos/` e `/privacidade/` | Termos de uso e política de privacidade | Todos |
| `/marcas/` | Aba “Marcas”: quem tem peça na vitrine | Todos |
| `/marcas/<id>/` | Página pública de uma loja ou marca | Todos |
| `/produtos/<id>/` | Página da peça | Todos |
| `/simulador/` | Simulador de desconto, com os valores de uma peça em `?tipo=&local=&extensao=&preco=` | Todos |
| `/minhas-pecas/` | Peças do vendedor logado | Vendedor e marca |
| `/produtos/novo/` | Cadastrar peça | Vendedor e marca |
| `/produtos/<id>/editar/` | Editar peça | Dono da peça |
| `/produtos/<id>/remover/` | Remover peça | Dono da peça |

![Filtros combinados](../../Sprint%208/prints-membro1/filtros-combinados.png)

![Busca e ordenação selecionadas](../../Sprint%208/prints-membro1/busca-ordenacao1.png)

![Produtos ordenados por desconto](../../Sprint%208/prints-membro1/busca-ordenacao2.png)

![Política de troca e devolução](../../Sprint%208/prints-membro1/politica-trocas.png)

## Models

| Model | Guarda |
|---|---|
| `Product` | Peça: nome, descrição, preço original, preço final, estoque, vendedor, categoria |
| `Defeito` | Tipo, localização e extensão do defeito (de 1 a 3 cada), ligado 1-para-1 à peça |
| `Category` | Categoria da peça |
| `ProductImage` | Uma foto enviada da peça e se ela mostra o defeito |

## Severidade e desconto

Tudo é calculado em `models.py`, numa fórmula única:

```text
Severidade = 0,45 × Tipo + 0,35 × Localização + 0,20 × Extensão
```

| Faixa | Severidade |
|---|---|
| Leve | até 1,70 |
| Moderada | até 2,30 |
| Alta | acima de 2,30 |

O desconto vai de 15% (severidade 1) a 50% (severidade 3), arredondado de 5 em
5. O preço final é sempre calculado; o vendedor informa só o preço original.

### Simulador ligado à peça

A página da peça tem o link **“Entender o desconto”**, que abre o simulador já
preenchido com o defeito daquela peça:

```text
/simulador/?tipo=2&local=3&extensao=1&preco=200.00
```

Os nomes na URL são em português, como todo caminho do site;
`DiscountSimulationForm.QUERY_PARAMS` faz a tradução para os campos do
formulário, `query_for()` monta o link e `from_query()` monta o formulário. Com
parâmetros válidos o resultado já vem calculado; faltando ou errando algum, a
tela pede a correção em vez de calcular.

O resultado mostra a conta aberta: a fórmula, o peso de cada critério e quanto
cada um somou na nota (`detalhar_severidade()` em `models.py`, que usa as mesmas
constantes da fórmula).

## Arquivos principais

| Arquivo | O que tem |
|---|---|
| `models.py` | Models, fórmula de severidade e o filtro `Product.objects.with_severity_band()` |
| `forms.py` | `ProductForm` (cadastrar e editar) e `DiscountSimulationForm` |
| `views.py` | Vitrine, página da peça, simulador e área do vendedor |
| `templates/products/includes/card_info.html` | Card de peça (vitrine, favoritos e minhas peças): foto com o selo do defeito, marca, nome, tamanho e preço. O card inteiro leva à página da peça, onde ficam a descrição do defeito e o botão de carrinho |
| `templates/products/includes/price.html` | Preço original, preço final e % de desconto |

Os dados de exemplo (peças, fotos e vendedores) ficam no app [`seed`](../seed/README.md).

> **[PRINT]** Tela "Minhas peças" com os botões Editar e Remover.

> **[PRINT]** Simulador de desconto com um resultado calculado.

> **[PRINT]** Simulador aberto pelo link da peça, com a fórmula e o que cada critério somou na nota.

## Fotos da peça

As fotos são arquivos enviados pelo vendedor (`ImageField`), guardados em
`MEDIA_ROOT/products/<id da peça>/` com nome sorteado. O nome do arquivo
original não entra no caminho para não vazar informação do vendedor.

A **foto do defeito é obrigatória**: sem ela o cadastro não é aceito. Na
galeria e nas miniaturas ela aparece primeiro, porque é a imagem que explica o
desconto. Peça sem foto da peça continua aparecendo, com um espaço no lugar da
capa.

Antes de salvar, `services.py` confere cada arquivo abrindo a imagem com o
Pillow (e não pela extensão, que o navegador escreve):

| Regra | Valor |
|---|---|
| Formatos aceitos | JPG, PNG, WebP |
| Tamanho máximo | 5 MB por arquivo |
| Lado menor | pelo menos 600 px |
| Fotos da peça | até 6, além da foto do defeito |

A imagem aprovada é girada pelo EXIF, reduzida a 2000 px no maior lado e tem
os metadados descartados — foto de celular carrega a coordenada de GPS de onde
foi tirada.

> **[PRINT]** Formulário de cadastro com os campos de foto da peça e foto do defeito.

> **[PRINT]** Galeria da página da peça, com a foto do defeito em destaque.

### Gerenciar as fotos depois de cadastrar

A tela de edição lista as fotos já enviadas e deixa o vendedor **remover** uma
foto e **escolher qual é a principal** (a que aparece no card da vitrine).
Adicionar novas continua sendo pelo campo “Fotos da peça” do formulário.

| Ação | URL (POST) |
|---|---|
| Tornar principal | `/produtos/<id>/fotos/<foto>/principal/` |
| Remover | `/produtos/<id>/fotos/<foto>/remover/` |

- A principal é guardada em `ProductImage.is_cover`. O banco garante **uma por
  peça** (`unique_product_cover`), e `make_cover()` desmarca a anterior e marca
  a nova na mesma transação.
- Enquanto o vendedor não escolhe, vale a primeira foto enviada. Remover a
  principal passa a capa para a próxima sozinho.
- A **foto do defeito não pode ser removida** pela lista: sem ela o cadastro
  não aceitaria a peça. Para trocá-la, envie outra no campo “Foto do defeito”.
  Por isso a peça nunca fica sem nenhuma foto.
- Só o dono mexe: a foto é buscada por `product__seller=request.user`, então a
  foto de outra pessoa (ou de outra peça) responde 404.
- A lista fica **fora** do formulário de edição porque HTML não permite um
  formulário dentro de outro: cada botão é um POST próprio.

> **[PRINT]** Lista de fotos na edição, com a principal marcada e os botões de remover.

## Busca, filtros e ordenação da vitrine

Os controles funcionam por GET e podem ser compartilhados na URL:

| Parâmetro | Exemplo | Comportamento |
|---|---|---|
| `marca` | `Circular` | Nome exato da marca |
| `categoria` | `camisetas` | Slug da categoria |
| `tamanho` | `M` | Tamanho exato cadastrado |
| `faixa` | `leve`, `moderada`, `alta` | Faixa calculada pelo model |
| `q` | `linho` | Trecho do nome da peça ou marca, sem diferenciar maiúsculas |
| `ordem` | `preco` | Menor preço final primeiro |
| `ordem` | `desconto` | Maior percentual de desconto exibido no card primeiro |

Exemplo: `/vitrine/?categoria=camisetas&tamanho=M&faixa=moderada&q=linho&ordem=preco`.

- Aplicar o formulário mantém a faixa selecionada; clicar nas faixas mantém
  busca, marca, categoria, tamanho e ordenação. "Todas" remove só a faixa.
- "Limpar filtros" volta à vitrine sem busca, filtros ou ordenação.
- Opções de marca, categoria e tamanho vêm de todas as peças ativas, sem
  valores vazios ou repetidos. Peças inativas não entram nos resultados.
- O contador mostra o número de peças que corresponde à combinação. Uma
  combinação sem resultado oferece a ação de limpar os filtros.
- Sem ordenação explícita, aparecem primeiro as peças mais recentes.
- "Maior desconto" reutiliza `Product.discount_percent`, que é o desconto
  real do anúncio, e não o desconto sugerido. Empates usam menor preço e
  depois ID decrescente. Peças sem desconto contam como 0%.
- Para manter o cálculo no model sem duplicar a fórmula, a ordenação é feita
  em memória sobre o catálogo filtrado.

### Abas de categoria e paginação

As categorias com peça ativa aparecem como abas no topo da vitrine, antes da
caixa de busca. Cada aba é um link que **mantém** busca, marca, tamanho, faixa
e ordem, trocando só a categoria; “Todas” remove só a categoria. É o mesmo
mecanismo dos atalhos de severidade (`shortcut_links()` em `views.py`), por
isso os dois não se atrapalham. Categoria sem peça ativa não vira aba, e a
barra some se nenhuma peça tiver categoria.

A vitrine mostra **12 peças por página** com `components/pagination.html`. O
contador continua mostrando o total da busca inteira, não o da página. Os
links de página levam junto todos os controles (`filters_query`), então a
página 2 é a página 2 da mesma busca. Trocar de categoria ou de faixa recomeça
da primeira página, porque o resultado é outro.

> **[PRINT]** Vitrine com as abas de categoria e a paginação no rodapé.

## Marcas e lojas

`/marcas/` (`store_list`) é a aba **Marcas** do menu: lista, em ordem
alfabética, quem tem pelo menos uma peça ativa, com cidade e quantidade de
peças. Loja sem peça na vitrine não aparece — uma lista de lojas vazias não
ajuda ninguém a comprar.

`/marcas/<id>/` (`store_detail`) é a página pública da loja: nome, cidade,
nota média da loja (as avaliações de todas as peças dela, vindas do `reviews`)
e as peças **ativas**, paginadas de 12 em 12. O card “Vendido por” da página
da peça leva para cá.

- Quem vende sem cadastrar nome de loja aparece pelo próprio nome
  (`UserProfile.display_name`).
- Usuário sem perfil não tem página de loja (404).

> **[PRINT]** Aba Marcas com as lojas que têm peças na vitrine.

> **[PRINT]** Página de uma marca com a nota da loja e as peças dela.

## Marcas e lojas

`/marcas/` (`store_list`) é a aba **Marcas** do menu: lista, em ordem
alfabética, quem tem pelo menos uma peça ativa, com cidade e quantidade de
peças. Loja sem peça na vitrine não aparece — uma lista de lojas vazias não
ajuda ninguém a comprar.

`/marcas/<id>/` (`store_detail`) é a página pública da loja: nome, cidade,
nota média da loja (as avaliações de todas as peças dela, vindas do `reviews`)
e as peças **ativas**, paginadas de 12 em 12. O card “Vendido por” da página
da peça leva para cá.

- Quem vende sem cadastrar nome de loja aparece pelo próprio nome
  (`UserProfile.display_name`).
- Usuário sem perfil não tem página de loja (404).

> **[PRINT]** Aba Marcas com as lojas que têm peças na vitrine.

> **[PRINT]** Página de uma marca com a nota da loja e as peças dela.

## Perguntas frequentes

`/ajuda/` (`faq`) é pública e só tem texto: não consulta o banco. Reúne as
dúvidas de quem compra, de quem vende e de quem tem conta, em quatro grupos
(Comprar, Defeitos e descontos, Vender, Conta). Cada pergunta é um
`<details>`, que abre e fecha sem JavaScript. Os links para a página Sobre e
para a página de cada peça levam até ela.

> **[PRINT]** Página de perguntas frequentes com uma pergunta aberta.

## Trabalhe conosco

`/trabalhe-conosco/` (`careers`) é pública e só tem texto: as quatro áreas da
equipe (Curadoria de peças, Atendimento, Desenvolvimento e Comunicação) vêm de
uma lista na própria view. As áreas são fictícias e a página avisa que não há
processo seletivo aberto. Ela é ligada pela página Sobre e pelas perguntas
frequentes. Não há formulário nem model.

> **[PRINT]** Página Trabalhe conosco com os cards das áreas.

## Contato

`/contato/` (`contact`) é pública e só tem texto: manda a pessoa para as
perguntas frequentes e para a aba "Problemas" do repositório no GitHub, e avisa
que, por ser um projeto acadêmico, não há atendimento por telefone nem por
e-mail. Ela é ligada pelas perguntas frequentes e pela página Trabalhe conosco.
Não há formulário nem model.

> **[PRINT]** Página de contato com os dois caminhos.

## Termos de uso e privacidade

`/termos/` (`terms`) e `/privacidade/` (`privacy`) são públicas e só têm
texto: não consultam o banco. Os termos resumem as regras de conta, de compra,
de venda e o que não pode; a privacidade lista os dados que o site guarda
(os mesmos dos models de conta, pedidos, favoritos e avaliações), para que
servem, que só há cookies de sessão e de segurança, e que não há pagamento.
Ambas avisam que são textos de exemplo de um **protótipo acadêmico**. Uma
liga na outra e as duas são ligadas pela página de contato. Não há model.

> **[PRINT]** Página de termos de uso e página de política de privacidade.

## Sobre e política de troca

`/sobre/` é pública e está ligada ao cabeçalho. Mostra o problema do descarte,
a proposta da FioFora, os três critérios e os nove níveis. Os pesos vêm das
constantes de `models.py`; a página referencia o resumo das oito entrevistas
da Sprint 2 e explica o caráter exploratório da pesquisa.

A página de cada peça inclui `includes/return_policy.html`, um bloco visível
com a política de troca e devolução: prazo de arrependimento (7 dias), troca
quando a peça vem diferente do anúncio, o defeito já informado na ficha como
parte do preço, como pedir a troca, e quem paga o frete e o reembolso. Os
prazos são regras de exemplo do **protótipo acadêmico**: o ambiente não realiza
cobrança ou entrega real e o texto avisa que não é a política de uma loja real.
Não foi criado campo ou migração para políticas por loja.

![Sobre a FioFora](../../Sprint%208/prints-membro1/sobre-criterios1.png)

![Tabela dos critérios](../../Sprint%208/prints-membro1/sobre-criterios2.png)

![Origem dos pesos](../../Sprint%208/prints-membro1/sobre-criterios3.png)

## Verificação

Dentro de `fio-fora/`:

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test products.tests.CatalogControlsTests products.tests.AboutAndPolicyTests
python manage.py test
```

Os testes de catálogo cobrem combinações, busca, ordenação, desempates,
seleção preservada, URLs com caracteres especiais, valores inválidos,
catálogo vazio e integração com favoritos/carrinho. Os testes de conteúdo
cobrem acesso público, critérios e pesos, cabeçalho e política da peça.
