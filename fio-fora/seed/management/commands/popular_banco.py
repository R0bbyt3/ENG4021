"""Comando `python manage.py popular_banco`: roda os blocos da seed em ordem.

Pode rodar de novo: o que já existe não é duplicado nem substituído.
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from seed.catalog import create_catalog
from seed.notifications import create_notifications
from seed.purchases import create_purchases
from seed.shopping import create_shopping
from seed.users import PASSWORD, create_users


class Command(BaseCommand):
    help = 'Cria contas, peças com fotos, favoritos, carrinhos, pedidos, avaliações e avisos de exemplo.'

    @transaction.atomic
    def handle(self, *args, **options):
        users = create_users()
        products = create_catalog(users)
        create_shopping(users, products)
        create_purchases(users, products)
        create_notifications(users)
        self.stdout.write(self.style.SUCCESS(
            f'Dados de exemplo prontos. Entre com qualquer conta do seed/README.md; a senha é "{PASSWORD}".'))
