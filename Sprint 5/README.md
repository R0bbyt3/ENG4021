# FioFora — Sprint 5 (Membro 4)

Tarefas cobertas:

| Tarefa | Dificuldade | Onde está |
|---|---|---|
| Criar view e rota para renderizar as telas com conexão ao banco de dados | difícil | `pecas/views.py`, `pecas/urls.py`, `fiofora/urls.py` (lê do banco via `pecas/models.py`) |
| Criar código HTML+CSS da tela desenhada no Figma — página do produto | média | `pecas/templates/pecas/produto.html`, `pecas/templates/pecas/base.html`, `pecas/static/pecas/css/fiofora.css` |

## Como rodar

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py loaddata demo   # dados de teste (3 peças); troque pelos dados reais do Membro 1
python manage.py runserver
```

- Vitrine: http://127.0.0.1:8000/
- Página do produto: http://127.0.0.1:8000/pecas/1/
- Admin (cadastrar peças): crie um usuário com `python manage.py createsuperuser` e acesse /admin/

## Testes

```bash
python manage.py test
```

## Observações

- `pecas/models.py` traz `Vendedor` e `Peca` só para a view ter o que ler. Quando o Membro 1 entregar as tabelas da modelagem oficial, ajuste os nomes dos campos em `models.py` e nos templates.
- Severidade e desconto são calculados no modelo (`S = 0,45×Tipo + 0,35×Local + 0,20×Extensão`, desconto de 15% a 50% arredondado de 5 em 5), não digitados.
- Fotos ainda são placeholders. Upload de imagem entra em outra sprint.
