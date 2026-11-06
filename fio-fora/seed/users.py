"""Bloco 1: contas de exemplo (comprador, vendedor, marca e equipe).

Todas entram com a mesma senha, listada no seed/README.md.
"""
from django.contrib.auth import get_user_model
from django.utils import timezone

from accounts.models import UserProfile

PASSWORD = 'fiofora123'

# Os compradores e a Julia vêm das personas do projeto.
USERS = [
    {'email': 'rafael@fiofora.com', 'name': 'Rafael Moreira', 'role': 'buyer',
     'phone': '(11) 98888-1001'},
    {'email': 'gabriel@fiofora.com', 'name': 'Gabriel Nunes', 'role': 'buyer',
     'phone': '(21) 98888-1002'},
    {'email': 'julia@fiofora.com', 'name': 'Julia Prado', 'role': 'seller',
     'phone': '(11) 98888-2001', 'store_name': 'Brechó Segunda Volta',
     'document': '12345678909', 'location': 'São Paulo, SP'},
    {'email': 'diego@fiofora.com', 'name': 'Diego Souza', 'role': 'seller',
     'phone': '(21) 98888-2002', 'store_name': 'Reuso Carioca',
     'document': '98765432100', 'location': 'Rio de Janeiro, RJ'},
    {'email': 'fabio@fiofora.com', 'name': 'Fábio Rocha', 'role': 'brand',
     'phone': '(11) 3333-3001', 'store_name': 'Ateliê Circular',
     'document': '12345678000190', 'location': 'São Paulo, SP',
     'legal_name': 'Ateliê Circular Confecções Ltda.', 'segment': 'moda',
     'social': '@ateliecircular'},
    {'email': 'gabriela@fiofora.com', 'name': 'Gabriela Melo', 'role': 'brand',
     'phone': '(21) 3333-3002', 'store_name': 'Fios do Rio',
     'document': '98765432000110', 'location': 'Rio de Janeiro, RJ',
     'legal_name': 'Fios do Rio Moda Ltda.', 'segment': 'moda',
     'social': 'fiosdorio.com.br'},
]

ADMIN = {'email': 'admin@fiofora.com', 'name': 'Equipe FioFora'}


def create_users():
    """Cria as contas e devolve um dicionário {e-mail: usuário}."""
    users = {}
    for data in USERS:
        user = get_or_create_user(data['email'], data['name'])
        profile = {key: value for key, value in data.items() if key not in ('email', 'name')}
        UserProfile.objects.get_or_create(user=user, defaults={**profile, 'terms_accepted_at': timezone.now()})
        users[data['email']] = user

    # A equipe não tem perfil: entra no /admin/ e na lista de usuários.
    users[ADMIN['email']] = get_or_create_user(ADMIN['email'], ADMIN['name'], is_staff=True, is_superuser=True)
    return users


def get_or_create_user(email, name, **extra):
    # O cadastro do site usa o e-mail como username; aqui seguimos o mesmo padrão.
    user, created = get_user_model().objects.get_or_create(
        username=email, defaults={'email': email, 'first_name': name, **extra})
    if created:
        user.set_password(PASSWORD)
        user.save()
    return user
