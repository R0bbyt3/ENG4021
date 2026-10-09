from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import (UserProfile, Category, Product, ProductImage,
                         Favorite, Cart, CartItem, Order, OrderItem)


class Command(BaseCommand):
    help = "Cria dados fictícios da FioFora sem duplicar nem substituir registros existentes."

    @transaction.atomic
    def handle(self, *args, **options):
        users = []
        records = [
            ("ana", "Ana", "Silva", "buyer", "", True),
            ("bruno", "Bruno", "Costa", "buyer", "", True),
            ("clara", "Clara", "Lima", "buyer", "", False),
            ("diego", "Diego", "Souza", "seller", "Reuso Carioca", True),
            ("elisa", "Elisa", "Santos", "seller", "Segunda Chance", True),
            ("fabio", "Fábio", "Rocha", "brand", "Ateliê Circular", True),
            ("gabi", "Gabriela", "Melo", "brand", "Fios do Rio", True),
            ("hugo", "Hugo", "Alves", "buyer", "", True),
        ]
        for key, first, last, role, store, active in records:
            user, created = get_user_model().objects.get_or_create(
                username=f"demo_{key}", defaults={"first_name": first, "last_name": last,
                "email": f"{key}@example.invalid", "is_active": active})
            if created:
                user.set_unusable_password()
                user.save(update_fields=["password"])
            UserProfile.objects.get_or_create(user=user, defaults={"role": role, "store_name": store})
            users.append(user)
        categories = {}
        for name, slug in [("Camisetas", "camisetas"), ("Calças", "calcas"), ("Vestidos", "vestidos")]:
            categories[slug], _ = Category.objects.get_or_create(slug=slug, defaults={"name": name})
        pieces = [
            ("Camiseta de algodão", "Pequena falha na costura interna.", "camisetas", "M", "100.00", 1, 1, 1, 3),
            ("Calça jeans reta", "Mancha na parte frontal, com 4 cm.", "calcas", "40", "200.00", 1, 3, 2, 4),
            ("Vestido floral", "Botão frontal que precisa de substituição.", "vestidos", "P", "160.00", 2, 3, 1, 5),
            ("Camiseta básica", "Desgaste visível que não admite reparo.", "camisetas", "G", "80.00", 3, 3, 1, 6),
            ("Calça de linho", "Pequena marca na parte interna da barra.", "calcas", "38", "180.00", 1, 1, 1, 3),
            ("Vestido midi", "Costura lateral com falha reparável.", "vestidos", "M", "240.00", 2, 2, 2, 4),
        ]
        products = []
        for index, (name, desc, category, size, original, kind, location, extent, seller) in enumerate(pieces, 1):
            candidate = Product(name=name, description=desc, original_price=Decimal(original),
                                defect_type=kind, defect_location=location, defect_extent=extent)
            product, _ = Product.objects.get_or_create(sku=f"FF-DEMO-{index:03}", defaults={
                "name": name, "description": desc, "price": candidate.suggested_price,
                "original_price": candidate.original_price, "seller": users[seller],
                "category": categories[category], "brand": users[seller].profile.store_name,
                "size": size, "condition": "Nova com defeito", "stock": 5,
                "defect_type": kind, "defect_location": location, "defect_extent": extent,
                "defect_measure_cm": Decimal("4.00") if extent == 2 else Decimal("1.00"),
                "visible_when_worn": location == 3})
            for defect in (False, True):
                path = "core/images/demo-defect.svg" if defect else "core/images/demo-piece.svg"
                ProductImage.objects.get_or_create(product=product, image_path=path, defaults={
                    "alt_text": "Ilustração de exemplo do defeito" if defect else "Ilustração de exemplo de peça",
                    "is_defect": defect})
            products.append(product)
        for product in products[:3]:
            Favorite.objects.get_or_create(user=users[0], product=product)
        cart, _ = Cart.objects.get_or_create(user=users[0])
        for product in products[:2]:
            CartItem.objects.get_or_create(cart=cart, product=product, defaults={"quantity": 1})
        order, _ = Order.objects.get_or_create(reference="FF-DEMO-PEDIDO-001", defaults={"user": users[1]})
        # Itens só são inseridos no pedido novo/vazio para preservar seu histórico.
        if not order.items.exists():
            OrderItem.objects.create(order=order, product=products[2], product_name=products[2].name,
                                     unit_price=products[2].price, quantity=1)
        self.stdout.write(self.style.SUCCESS(
            "Dados fictícios disponíveis: 8 usuários, 3 categorias, 6 peças, 12 fotos/ilustrações, "
            "3 favoritos, 1 carrinho com 2 itens e 1 pedido com 1 item. "
            "Registros existentes foram preservados. Use createsuperuser para acessar a listagem."))
