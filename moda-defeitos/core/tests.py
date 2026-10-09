from django.test import TestCase
from django.urls import reverse


class AuthPageTests(TestCase):
    def test_login_is_the_initial_page(self):
        self.assertEqual(reverse('login_page'), '/')
        self.assertEqual(reverse('login'), '/login/')
        self.assertEqual(reverse('home'), '/vitrine/')

    def test_auth_pages_open_successfully(self):
        page_names = [
            'login_page',
            'password_reset_page',
            'account_type_page',
            'buyer_register_page',
            'seller_register_page',
            'brand_register_page',
        ]

        for page_name in page_names:
            with self.subTest(page=page_name):
                response = self.client.get(reverse(page_name))
                self.assertEqual(response.status_code, 200)

    def test_password_is_not_put_in_redirect_url(self):
        for page_name in ['login_page', 'buyer_register_page', 'seller_register_page', 'brand_register_page']:
            with self.subTest(page=page_name):
                response = self.client.post(reverse(page_name), {'password': 'senha-de-teste'})
                self.assertEqual(response.status_code, 302)
                self.assertNotIn('senha-de-teste', response['Location'])

    def test_password_reset_does_not_claim_email_was_sent(self):
        response = self.client.post(reverse('password_reset_page'), {'email': 'teste@exemplo.com'})
        self.assertContains(response, 'nenhum e-mail foi enviado')

    def test_product_form_uses_shared_controls(self):
        response = self.client.get(reverse('product_create'))
        self.assertContains(response, 'class="form-control"', count=3)
        self.assertContains(response, 'class="form-check"')

    def test_shared_base_and_page_specific_styles(self):
        login = self.client.get(reverse('login_page'))
        vitrine = self.client.get(reverse('home'))

        for response in [login, vitrine]:
            self.assertContains(response, 'core/base/site.css')
            self.assertContains(response, 'core/images/logo-mark.png')

        self.assertContains(login, 'core/login/base.css')
        self.assertNotContains(login, 'core/products.css')
        self.assertContains(vitrine, 'core/products.css')


from decimal import Decimal
from io import StringIO
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import IntegrityError, transaction
from .models import (UserProfile, Product, Category, ProductImage, Favorite,
                     Cart, CartItem, Order, OrderItem)


class Sprint5Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("popular_banco", stdout=StringIO())
        cls.staff = get_user_model().objects.create_user("equipe", is_staff=True)

    def test_population_is_repeatable_and_preserves_changes(self):
        models = [get_user_model(), UserProfile, Category, Product, ProductImage,
                  Favorite, Cart, CartItem, Order, OrderItem]
        counts = [model.objects.count() for model in models]
        user = get_user_model().objects.get(username="demo_ana")
        user.first_name = "Nome editado"
        user.save()
        product = Product.objects.get(sku="FF-DEMO-001")
        product.name = "Peça editada"
        product.save()
        call_command("popular_banco", stdout=StringIO())
        self.assertEqual(counts, [model.objects.count() for model in models])
        user.refresh_from_db()
        product.refresh_from_db()
        self.assertEqual(user.first_name, "Nome editado")
        self.assertEqual(product.name, "Peça editada")
        self.assertFalse(user.has_usable_password())

    def test_list_requires_staff(self):
        self.assertEqual(self.client.get(reverse("user_list")).status_code, 302)
        self.client.force_login(get_user_model().objects.get(username="demo_ana"))
        self.assertEqual(self.client.get(reverse("user_list")).status_code, 302)
        self.client.force_login(self.staff)
        response = self.client.get(reverse("user_list"))
        self.assertContains(response, "Ana Silva")
        self.assertNotContains(response, "pbkdf2_")

    def test_search_role_and_status_can_be_combined(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse("user_list"), {"q": "Clara", "role": "buyer", "status": "inactive"})
        self.assertEqual(response.context["total"], 1)
        self.assertContains(response, "Clara Lima")
        self.assertNotContains(response, "Ana Silva")
        response = self.client.get(reverse("user_list"), {"q": "Circular", "role": "brand"})
        self.assertEqual(response.context["total"], 1)
        self.assertContains(response, "Fábio Rocha")
        response = self.client.get(reverse("user_list"), {"q": "nada-inexistente"})
        self.assertContains(response, "Nenhum usuário encontrado")

    def test_pagination_preserves_filters_and_missing_profiles(self):
        for i in range(12):
            get_user_model().objects.create_user(f"extra_{i}", first_name="Equipe teste")
        self.client.force_login(self.staff)
        response = self.client.get(reverse("user_list"), {"q": "Equipe", "role": "unassigned"})
        self.assertEqual(response.context["total"], 13)
        self.assertContains(response, "role=unassigned")
        self.assertContains(response, "Sem perfil")
        self.assertEqual(len(response.context["page_obj"]), 10)
        response = self.client.get(reverse("user_list"), {"q": "Equipe", "role": "unassigned", "page": "2"})
        self.assertEqual(len(response.context["page_obj"]), 3)
        self.assertEqual(self.client.get(reverse("user_list"), {"page": "invalid"}).status_code, 200)

    def test_financial_history_and_database_integrity(self):
        order = Order.objects.get(reference="FF-DEMO-PEDIDO-001")
        self.assertEqual(order.total, Decimal("104.00"))
        product = order.items.get().product
        product.name = "Novo nome"
        product.price = Decimal("99.00")
        product.save()
        self.assertEqual(order.items.get().product_name, "Vestido floral")
        self.assertEqual(order.total, Decimal("104.00"))
        with self.assertRaises(IntegrityError), transaction.atomic():
            Favorite.objects.create(user_id=Favorite.objects.first().user_id, product_id=Favorite.objects.first().product_id)
        with self.assertRaises(IntegrityError), transaction.atomic():
            CartItem.objects.filter(pk=CartItem.objects.first().pk).update(quantity=0)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Product.objects.filter(pk=product.pk).update(defect_type=4)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Product.objects.filter(pk=product.pk).update(price=Decimal("0.00"))

    def test_discount_reference_scenarios(self):
        for scores, severity, discount in [((1,1,1), "1.00", 15), ((1,3,2), "1.90", 30), ((2,3,1), "2.15", 35), ((3,3,1), "2.60", 45)]:
            product = Product(defect_type=scores[0], defect_location=scores[1], defect_extent=scores[2], original_price=Decimal("100.00"))
            self.assertEqual(product.severity, Decimal(severity))
            self.assertEqual(product.suggested_discount, discount)
            self.assertEqual(product.suggested_price, Decimal(100-discount))
