# FioFora - Sprint 5 - Pessoa 1 (Gabriel) - Versão 2

Entrega referente às três tarefas de 60 XP: criar tabelas, popular o banco e implementar HTML + CSS para listar usuários.

## O que foi entregue

1. Modelagem relacional e migração `0002`, mantendo a migração `0001` e os campos do produto existentes.
2. Comando `popular_banco` com dados fictícios, executado em uma transação e repetível sem duplicação. Nenhum usuário administrativo ou senha compartilhada é criado.
3. Página `/usuarios/` com busca por nome, usuário, e-mail e loja, filtro por perfil e situação, paginação de 10 contas, estado vazio e CSS responsivo. View e rota incluídas para tornar a tela demonstrável; o membro 4 pode integrar a solução às demais telas.
4. Modelos registrados no Django Admin, testes e instruções de integração.

## Instalação e demonstração

O pacote contém `moda-defeitos/` completo, a pasta `Sprint 5/` e um patch das mudanças. Os arquivos de outras sprints não foram repetidos.

Se você já tem o repositório, copie os arquivos do pacote para as pastas de mesmo nome. Antes, salve/commite seu trabalho atual e faça uma cópia do banco caso ele já tenha dados. Não copie sobre alterações posteriores da equipe sem comparar os arquivos.

Entre na pasta do aplicativo:

```bash
cd moda-defeitos
python -m venv .venv
```

Ative o ambiente:

- Windows (PowerShell): `.venv\Scripts\Activate.ps1`
- Linux/Codespaces/macOS: `source .venv/bin/activate`

Se `python` não existir no Linux/macOS, use `python3` para criar o ambiente.

```bash
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py popular_banco
python manage.py createsuperuser
python manage.py check
python manage.py test core
python manage.py runserver
```

No `createsuperuser`, escolha seu usuário, e-mail e senha. Abra `http://127.0.0.1:8000/admin/`, faça login e depois abra `http://127.0.0.1:8000/usuarios/`.

O login original da FioFora ainda é uma demonstração: ele não autentica sessões. Para esta entrega, o acesso administrativo usa o login funcional do Django Admin. O membro responsável pelo login poderá conectar a autenticação da tela própria depois.

O pacote não inclui `db.sqlite3`, ambiente virtual nem credenciais. `migrate` cria as tabelas e `popular_banco` preenche o banco local. As contas `demo_*` têm senha inutilizável e não podem fazer login.

## Modelagem definida para esta sprint

A modelagem é uma proposta implementada a partir das funcionalidades da FioFora e dos documentos do repositório. Não é uma modelagem previamente aprovada pelo grupo. Os documentos da Sprint 2 descreviam um protótipo estático sem banco; o backlog da Sprint 5 e o código atual passaram a usar Django. Esta entrega segue a Sprint 5.

| Modelo / tabela | O que armazena | Relações principais |
|---|---|---|
| User / auth_user | Identificação, nome, e-mail, senha com hash, ativo e staff | Modelo padrão do Django |
| UserProfile / core_userprofile | Papel (comprador, vendedor ou marca), telefone e loja | 1 perfil por usuário |
| Category / core_category | Nome e slug da categoria | 1 categoria para várias peças |
| Product / core_product | Peça, vendedor, marca, tamanho, medidas, estoque, preços e critérios de defeito | Vendedor e categoria; campos opcionais para preservar o CRUD anterior |
| ProductImage / core_productimage | Caminho e descrição de imagem; indicação de foto do defeito | Várias imagens para uma peça |
| Favorite / core_favorite | Peças favoritas de cada usuário | Par usuário/peça único |
| Cart / core_cart | Carrinho do usuário | 1 carrinho por usuário |
| CartItem / core_cartitem | Produto e quantidade no carrinho | Par carrinho/peça único |
| Order / core_order | Comprador, referência única, situação e data | Um usuário pode ter vários pedidos |
| OrderItem / core_orderitem | Produto, quantidade e cópias do nome/preço comprado | Vários itens por pedido |

As tabelas auxiliares de autenticação, administração e sessão são criadas pelas migrações do próprio Django.

### Integridade e histórico

- Quantidades de itens são maiores ou iguais a 1. Preços são positivos. Preço original informado não pode ser menor que o preço final.
- Critérios de defeito ficam entre 1 e 3; papel e situação do pedido têm valores definidos.
- A exclusão de um usuário que possui peças ou pedidos é protegida para evitar perder referências. Nesse caso, a equipe pode desativar a conta com `is_active=False`.
- A exclusão de uma peça mantém o nome e o preço histórico em seus itens de pedido. Favoritos e itens de carrinho da peça são removidos.
- O usuário administrativo pode existir sem perfil; a listagem mostra “Sem perfil”. Criar perfis de novos cadastros é parte da integração dos formulários da equipe.
- `sku` é opcional e único quando informado; os exemplos usam `FF-DEMO-001` até `FF-DEMO-006`.

### Cálculo de severidade

`S = 0,45 × Tipo + 0,35 × Localização + 0,20 × Extensão`.

Até 1,70: Leve. Acima de 1,70 e até 2,30: Moderada. Acima de 2,30: Alta.

`Desconto = 15 + ((S - 1) / 2) × 35`, arredondado para múltiplo de 5 com empate para cima.

O modelo fornece `severity`, `severity_label`, `suggested_discount` e `suggested_price`. `price` continua representando o preço anunciado para preservar o formulário anterior; a sugestão não sobrescreve automaticamente esse valor. O comando de exemplo calcula o preço sugerido ao inserir a peça.

## Dados fictícios criados

| Dados | Quantidade |
|---|---:|
| Usuários | 8 (4 compradores, 2 vendedores e 2 marcas) |
| Perfis | 8 |
| Categorias | 3 |
| Peças | 6 |
| Imagens de exemplo | 12 (ilustrações SVG, não fotografias de produtos reais) |
| Favoritos | 3 |
| Carrinhos / itens | 1 / 2 |
| Pedidos / itens | 1 / 1 |

Exemplos: Ana Silva (compradora ativa), Clara Lima (compradora inativa), Diego Souza (vendedor) e Fábio Rocha (marca). E-mails usam `example.invalid` e não são endereços de contato reais.

Executar `popular_banco` duas vezes mantém as quantidades e preserva edições já feitas. O comando usa chaves estáveis e `get_or_create`, sem apagar dados e sem alterar contas existentes. Evite usar os nomes reservados `demo_*`, SKUs `FF-DEMO-*` e referência `FF-DEMO-PEDIDO-001` para registros reais.

## Arquivos para integração

- `core/models.py`: modelos e cálculo de desconto.
- `core/migrations/0002_*.py`: criação e atualização de tabelas.
- `core/management/commands/popular_banco.py`: população do banco.
- `core/templates/core/users/list.html`: HTML da listagem.
- `core/static/core/users/list.css`: aparência responsiva.
- `core/static/core/images/demo-*.svg`: ilustrações usadas nos registros de exemplo.
- `core/views.py` e `core/urls.py`: consulta, proteção de acesso e rota `/usuarios/`.
- `core/admin.py`: administração das novas tabelas.
- `core/tests.py`: testes do projeto, incluindo a Sprint 5.
- `config/settings.py`: chave primária padrão `BigAutoField`, compatível com a migração inicial.
- `requirements.txt`: dependências exatas usadas na validação.

A dependência Django foi alterada de 6.1 para 5.2.18, disponível e compatível com o Python 3.11 usado para validar a entrega. As versões de asgiref e sqlparse foram mantidas. A configuração `MAILERS` do projeto original não é utilizada por esta entrega. A equipe pode optar por outra versão, mas deve repetir os testes e a verificação de migrações nesse ambiente.

Para aplicar apenas o patch em uma cópia limpa do commit de origem:

```bash
git apply --check fiofora-pessoa1.patch
git apply fiofora-pessoa1.patch
```

Isso altera arquivos locais. Depois revise `git diff`, teste, adicione as mudanças e faça seu commit. Esta entrega não foi publicada no GitHub.

## Roteiro de apresentação

1. Mostrar as classes em `models.py`: cada classe define uma tabela e cada atributo define uma coluna ou relação.
2. Executar `migrate`: o Django aplica a migração e cria as tabelas.
3. Executar `popular_banco` e mostrar registros no Admin. Executar novamente para mostrar que não há duplicação.
4. Abrir `/usuarios/` e buscar “Ana”; filtrar por Marca; depois filtrar por Inativo para mostrar Clara.
5. Buscar um nome inexistente para demonstrar o estado vazio; limpar os filtros.
6. Reduzir a janela para mostrar a adaptação da página e a rolagem da tabela no celular.
7. Mostrar o resultado de `python manage.py test core`.

## Limites desta entrega

O banco prepara favoritos, carrinhos e pedidos, mas não implementa checkout, pagamento, reserva de estoque, upload de fotos nem as respectivas telas. Essas funcionalidades não fazem parte das três tarefas da pessoa 1. A criação de peça ainda usa o formulário simples existente; os colegas podem acrescentar os novos campos. Papel vendedor/marca, limite de estoque, foto obrigatória do defeito e política de devolução devem ser validados nos fluxos que os usarem. Não foi implantado um serviço real nem substituída a autenticação dos colegas.

Não apague migrações antigas nem o banco para aplicar esta entrega. Caso o banco já contenha preços não positivos, corrija esses registros antes da migração, porque as novas regras de integridade os rejeitam.

## Fontes da implementação

- Backlog: PDF de divisão da Sprint 5 enviado por Gabriel.
- Código de origem: https://github.com/Percia41/ENG4021 (main, commit 16ad4398aa3f78c87dd25a6f9c71c62764b24a17).
- Regras de produto: `Sprint 2/S2_RequisitosFuncionais_F.pdf`.
- Extensão do usuário padrão: https://docs.djangoproject.com/en/5.2/topics/auth/customizing/#extending-the-existing-user-model
- Comandos de administração: https://docs.djangoproject.com/en/5.2/howto/custom-management-commands/

## Validação concluída

- `python manage.py check`: sem problemas.
- `python manage.py makemigrations --check --dry-run`: nenhuma mudança pendente.
- `python manage.py test core`: 12 testes aprovados.
- Migração de banco da versão anterior com produto existente: dados preservados.
- Templates renderizados pelo Django com dados do banco. O navegador de teste não pôde ser instalado neste ambiente; a revisão visual no desktop e celular deve ser feita ao abrir a página.

## Alterações da versão 2: referências do Lovable

As três demonstrações foram abertas e observadas no navegador. A listagem foi ajustada para acompanhar sua identidade visual: fundo creme, botões e textos de destaque em verde escuro, detalhes em terracota, título com serifa e itálico, campos discretos, cabeçalho com faixa superior e logo horizontal. Os estilos ficam restritos à listagem de usuários.

Referências:

- https://fio-fora-eco-style.lovable.app/: vitrine e simulador; referência para títulos, cores e filtros.
- https://fiofora-favs-cart.lovable.app/#pecas-em-destaque: catálogo, favoritos e carrinho; referência para logo e apresentação dos dados.
- https://fiofora-sprint4.lovable.app/: tela de login; referência para fundo creme, campos e botões.

A página de usuários é uma adaptação criada para a tarefa, não uma cópia de uma tela de listagem existente nesses protótipos. Não foram acrescentados botões de compra, login ou cadastro fictícios à listagem administrativa.

A modelagem e os dados da primeira versão foram mantidos: os designs confirmam campos que já foram previstos, como marca, tamanho, preços, defeito, favoritos e carrinho. A população continua com dados fictícios e a regra de desconto documentada. Alguns preços e nomes de faixas nos protótipos são diferentes dos requisitos escritos; eles não foram usados para substituir as regras do banco.

Nenhuma migração nova é necessária em relação ao primeiro ZIP. Se já instalou a versão 1, copie os arquivos atualizados (principalmente o HTML e o CSS) e atualize a página. Em produção, arquivos estáticos devem ser recolhidos pelo processo de deploy da equipe.

Os três protótipos foram verificados visualmente no navegador. A tela Django local atualizada foi renderizada nos testes, mas ainda precisa de revisão visual final no navegador local.
