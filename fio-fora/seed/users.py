"""Bloco 1: contas de exemplo (comprador, vendedor, marca e equipe).

Todas entram com a mesma senha, listada no seed/README.md.
"""
from django.contrib.auth import get_user_model
from django.utils import timezone

from accounts.models import UserProfile

PASSWORD = 'fiofora123'

# Telefone e documento ficam só com números, como o cadastro do site salva
# (a formatação é feita na hora de mostrar; ver accounts/fields.py).
# Os compradores e a Julia vêm das personas do projeto.
USERS = [
    {'email': 'rafael@fiofora.com', 'name': 'Rafael Moreira', 'role': 'buyer',
     'phone': '11988881001', 'address_cep': '01310100', 'address_street': 'Avenida Paulista',
     'address_number': '1000', 'address_complement': 'apto 52', 'address_district': 'Bela Vista',
     'address_location': 'São Paulo, SP'},
    {'email': 'gabriel@fiofora.com', 'name': 'Gabriel Nunes', 'role': 'buyer',
     'phone': '21988881002', 'address_cep': '22041001', 'address_street': 'Rua Barata Ribeiro',
     'address_number': '200', 'address_district': 'Copacabana', 'address_location': 'Rio de Janeiro, RJ'},
    {'email': 'julia@fiofora.com', 'name': 'Julia Prado', 'role': 'seller',
     'phone': '11988882001', 'store_name': 'Brechó Segunda Volta',
     'document': '12345678909', 'location': 'São Paulo, SP'},
    {'email': 'diego@fiofora.com', 'name': 'Diego Souza', 'role': 'seller',
     'phone': '21988882002', 'store_name': 'Reuso Carioca',
     'document': '98765432100', 'location': 'Rio de Janeiro, RJ'},
    {'email': 'fabio@fiofora.com', 'name': 'Fábio Rocha', 'role': 'brand',
     'phone': '1133333001', 'store_name': 'Ateliê Circular',
     'document': '12345678000195', 'location': 'São Paulo, SP',
     'legal_name': 'Ateliê Circular Confecções Ltda.', 'segment': 'moda',
     'social': '@ateliecircular'},
    {'email': 'gabriela@fiofora.com', 'name': 'Gabriela Melo', 'role': 'brand',
     'phone': '2133333002', 'store_name': 'Fios do Rio',
     'document': '98765432000198', 'location': 'Rio de Janeiro, RJ',
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
