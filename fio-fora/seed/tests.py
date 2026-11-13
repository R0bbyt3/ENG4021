import shutil
import tempfile
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import UserProfile
from cart.models import Cart, CartItem
from favorites.models import Favorite
from notifications.models import Notification
from orders.models import Order, OrderItem
from products.models import Category, Defeito, Product, ProductImage
from reviews.models import Review

from .catalog import PRODUCTS
from .users import ADMIN, PASSWORD, USERS

# A seed grava fotos de verdade: mande-as para uma pasta temporária.
MEDIA_DE_TESTE = tempfile.mkdtemp()

MODELS = [get_user_model(), UserProfile, Category, Product, Defeito, ProductImage,
          Favorite, Cart, CartItem, Order, OrderItem, Review, Notification]


def tearDownModule():
    shutil.rmtree(MEDIA_DE_TESTE, ignore_errors=True)


@override_settings(MEDIA_ROOT=MEDIA_DE_TESTE)
class PopularBancoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('popular_banco', stdout=StringIO())

    def test_creates_every_block(self):
        self.assertEqual(get_user_model().objects.count(), len(USERS) + 1)
        self.assertEqual(Product.objects.count(), len(PRODUCTS))
        self.assertEqual(ProductImage.objects.count(), 2 * len(PRODUCTS))
        self.assertEqual(Order.objects.count(), 4)
        self.assertEqual(Review.objects.count(), 3)
        self.assertEqual(Notification.objects.count(), 2)
        # Toda peça tem a foto da peça e a do defeito.
        for product in Product.objects.all():
            self.assertIsNotNone(product.cover_image)
            self.assertIsNotNone(product.defect_image)

    def test_running_again_does_not_duplicate_or_overwrite(self):
        counts = [model.objects.count() for model in MODELS]
        product = Product.objects.get(sku='FF-SEED-001')
        product.name = 'Peça editada'
        product.save()
        call_command('popular_banco', stdout=StringIO())
        self.assertEqual(counts, [model.objects.count() for model in MODELS])
        product.refresh_from_db()
        self.assertEqual(product.name, 'Peça editada')

    def test_every_account_logs_in_with_the_documented_password(self):
        for email in [data['email'] for data in USERS] + [ADMIN['email']]:
            with self.subTest(email=email):
                self.assertTrue(self.client.login(email=email, password=PASSWORD))
                self.client.logout()

    def test_roles_and_staff(self):
        roles = {data['email']: data['role'] for data in USERS}
        for profile in UserProfile.objects.select_related('user'):
            self.assertEqual(profile.role, roles[profile.user.email])
        self.assertTrue(get_user_model().objects.get(email=ADMIN['email']).is_staff)

    def test_paused_piece_is_not_in_the_showcase(self):
        response = self.client.get(reverse('home'))
        self.assertContains(response, 'Calça jeans reta')
        self.assertNotContains(response, 'Camisa social azul-clara')

    def test_seller_starts_with_an_unread_notice(self):
        julia = get_user_model().objects.get(email='julia@fiofora.com')
        self.client.force_login(julia)
        self.assertEqual(self.client.get(reverse('home')).context['unread_notifications'], 1)
