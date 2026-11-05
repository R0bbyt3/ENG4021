# products — catálogo e área do vendedor

Vitrine, página da peça, cadastro de peças pelo vendedor e simulador de desconto.

[← Voltar para a documentação principal](../README.md)

## Páginas

| URL | Página | Quem acessa |
|---|---|---|
| `/vitrine/` | Vitrine com filtros combináveis, busca e ordenação | Todos |
| `/sobre/` | Proposta, critérios, origem dos pesos e caráter acadêmico | Todos |
| `/produtos/<id>/` | Página da peça | Todos |
| `/simulador/` | Simulador de desconto | Todos |
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

## Arquivos principais

| Arquivo | O que tem |
|---|---|
| `models.py` | Models, fórmula de severidade e o filtro `Product.objects.with_severity_band()` |
| `forms.py` | `ProductForm` (cadastrar e editar) e `DiscountSimulationForm` |
| `views.py` | Vitrine, página da peça, simulador e área do vendedor |
| `templates/products/includes/card_info.html` | Informações comuns aos cards de peça |
| `templates/products/includes/price.html` | Preço original, preço final e % de desconto |
| `management/commands/popular_banco.py` | Cria usuários, peças, carrinho e pedido de exemplo |

> **[PRINT]** Tela "Minhas peças" com os botões Editar e Remover.

> **[PRINT]** Simulador de desconto com um resultado calculado.

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
  em memória sobre o catálogo filtrado. Esta vitrine não usa paginação.

## Sobre e política de troca

`/sobre/` é pública e está ligada ao cabeçalho. Mostra o problema do descarte,
a proposta da FioFora, os três critérios e os nove níveis. Os pesos vêm das
constantes de `models.py`; a página referencia o resumo das oito entrevistas
da Sprint 2 e explica o caráter exploratório da pesquisa.

A página de cada peça inclui `includes/return_policy.html`, um bloco visível
sobre trocas e devoluções no **protótipo acadêmico**. O ambiente não realiza
cobrança ou entrega real; o texto não inventa prazos ou uma política de loja.
Condições comerciais e canais de atendimento precisam ser definidos antes
de uma operação real. Não foi criado campo ou migração para políticas por loja.

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
