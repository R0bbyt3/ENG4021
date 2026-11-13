from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserProfile
from orders.models import Order, OrderItem
from products.models import Product

from .models import Review


class ReviewTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()

        def make_user(username, role, **extra):
            user = User.objects.create_user(username, **extra)
            UserProfile.objects.create(user=user, role=role, store_name='Brechó Sol' if role == 'seller' else '')
            return user

        cls.buyer = make_user('buyer@example.com', 'buyer', first_name='Ana Souza')
        cls.other_buyer = make_user('other@example.com', 'buyer', first_name='Beto')
        cls.seller = make_user('seller@example.com', 'seller')
        cls.shirt = Product.objects.create(name='Camisa de linho', description='Mancha pequena', price=Decimal('85.00'), seller=cls.seller)
        cls.jeans = Product.objects.create(name='Calça jeans', description='Fio puxado', price=Decimal('120.00'), seller=cls.seller)
        cls.order = Order.objects.create(user=cls.buyer, reference='FF-TESTE-001')
        cls.shirt_item = OrderItem.objects.create(order=cls.order, product=cls.shirt, product_name=cls.shirt.name, unit_price=cls.shirt.price)
        cls.jeans_item = OrderItem.objects.create(order=cls.order, product=cls.jeans, product_name=cls.jeans.name, unit_price=cls.jeans.price)

    def review(self, item, rating='5', comment='Chegou como no anúncio.'):
        return self.client.post(reverse('review_save', args=[item.pk]), {'rating': rating, 'comment': comment})


class SaveReviewTests(ReviewTestCase):
    def test_buyer_reviews_own_item(self):
        self.client.force_login(self.buyer)
        response = self.review(self.shirt_item, '4')
        self.assertRedirects(response, reverse('order_detail', args=[self.order.pk]))
        review = Review.objects.get()
        self.assertEqual((review.order_item, review.user, review.rating), (self.shirt_item, self.buyer, 4))

    def test_comment_is_optional(self):
        self.client.force_login(self.buyer)
        self.review(self.shirt_item, '3', comment='')
        self.assertEqual(Review.objects.get().comment, '')

    def test_other_user_gets_404_and_nothing_is_saved(self):
        self.client.force_login(self.other_buyer)
        self.assertEqual(self.review(self.shirt_item).status_code, 404)
        self.assertEqual(Review.objects.count(), 0)

    def test_seller_cannot_review(self):
        self.client.force_login(self.seller)
        self.assertRedirects(self.review(self.shirt_item), reverse('home'))
        self.assertEqual(Review.objects.count(), 0)

    def test_anonymous_user_is_sent_to_login(self):
        response = self.review(self.shirt_item)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response['Location'])
        self.assertEqual(Review.objects.count(), 0)

    def test_get_is_not_allowed(self):
        self.client.force_login(self.buyer)
        self.assertEqual(self.client.get(reverse('review_save', args=[self.shirt_item.pk])).status_code, 405)

    def test_second_review_of_same_item_edits_instead_of_duplicating(self):
        self.client.force_login(self.buyer)
        self.review(self.shirt_item, '2', 'Veio com mais defeitos.')
        self.review(self.shirt_item, '5', 'Mudei de ideia, ficou ótima.')
        review = Review.objects.get()
        self.assertEqual((review.rating, review.comment), (5, 'Mudei de ideia, ficou ótima.'))

    def test_database_refuses_second_review_for_the_same_item(self):
        Review.objects.create(order_item=self.shirt_item, user=self.buyer, rating=5)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Review.objects.create(order_item=self.shirt_item, user=self.buyer, rating=4)

    def test_rating_must_be_between_1_and_5(self):
        self.client.force_login(self.buyer)
        for bad in ('0', '6', '', 'x'):
            self.review(self.shirt_item, bad)
        self.assertEqual(Review.objects.count(), 0)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Review.objects.create(order_item=self.shirt_item, user=self.buyer, rating=6)

    def test_cancelled_order_cannot_be_reviewed(self):
        Order.objects.filter(pk=self.order.pk).update(status=Order.Status.CANCELLED)
        self.client.force_login(self.buyer)
        self.review(self.shirt_item)
        self.assertEqual(Review.objects.count(), 0)

    def test_item_whose_piece_was_deleted_cannot_be_reviewed(self):
        OrderItem.objects.filter(pk=self.shirt_item.pk).update(product=None)
        self.client.force_login(self.buyer)
        self.review(self.shirt_item)
        self.assertEqual(Review.objects.count(), 0)

    def test_editing_does_not_change_other_users_review(self):
        other_order = Order.objects.create(user=self.other_buyer, reference='FF-TESTE-002')
        other_item = OrderItem.objects.create(order=other_order, product=self.shirt, product_name='Camisa', unit_price=Decimal('85.00'))
        Review.objects.create(order_item=other_item, user=self.other_buyer, rating=1)
        self.client.force_login(self.buyer)
        self.review(self.shirt_item, '5')
        self.assertEqual(Review.objects.get(order_item=other_item).rating, 1)


class OrderDetailReviewTests(ReviewTestCase):
    def test_form_appears_for_each_item_and_shows_existing_review(self):
        Review.objects.create(order_item=self.shirt_item, user=self.buyer, rating=4)
        self.client.force_login(self.buyer)
        response = self.client.get(reverse('order_detail', args=[self.order.pk]))
        self.assertContains(response, reverse('review_save', args=[self.shirt_item.pk]))
        self.assertContains(response, reverse('review_save', args=[self.jeans_item.pk]))
        self.assertContains(response, 'Editar minha avaliação')
        self.assertContains(response, 'Avaliar esta peça')

    def test_no_form_for_cancelled_order(self):
        Order.objects.filter(pk=self.order.pk).update(status=Order.Status.CANCELLED)
        self.client.force_login(self.buyer)
        response = self.client.get(reverse('order_detail', args=[self.order.pk]))
        self.assertNotContains(response, 'avaliar/')


class ShowReviewsTests(ReviewTestCase):
    def test_empty_state_on_product_page(self):
        response = self.client.get(reverse('product_detail', args=[self.shirt.pk]))
        self.assertContains(response, 'Ainda sem avaliações')
        self.assertContains(response, 'Loja ainda sem avaliações')

    def test_product_average_count_and_comments(self):
        other_order = Order.objects.create(user=self.other_buyer, reference='FF-TESTE-002')
        other_item = OrderItem.objects.create(order=other_order, product=self.shirt, product_name='Camisa', unit_price=Decimal('85.00'))
        Review.objects.create(order_item=self.shirt_item, user=self.buyer, rating=5, comment='Linda!')
        Review.objects.create(order_item=other_item, user=self.other_buyer, rating=4, comment='Boa.')
        response = self.client.get(reverse('product_detail', args=[self.shirt.pk]))
        self.assertEqual(response.context['rating'], {'average': Decimal('4.5'), 'count': 2})
        self.assertContains(response, '4,5')
        self.assertContains(response, '2 avaliações')
        self.assertContains(response, 'Linda!')
        self.assertContains(response, 'Ana')
        self.assertNotContains(response, 'Souza')  # só o primeiro nome é público

    def test_store_rating_covers_all_pieces_of_the_seller(self):
        Review.objects.create(order_item=self.shirt_item, user=self.buyer, rating=5)
        Review.objects.create(order_item=self.jeans_item, user=self.buyer, rating=2)
        response = self.client.get(reverse('product_detail', args=[self.shirt.pk]))
        self.assertEqual(response.context['store_rating'], {'average': Decimal('3.5'), 'count': 2})
        self.assertEqual(response.context['rating'], {'average': Decimal('5.0'), 'count': 1})
        self.assertContains(response, 'na loja')

    def test_page_shows_only_the_ten_most_recent_reviews(self):
        for number in range(12):
            order = Order.objects.create(user=self.other_buyer, reference=f'FF-X-{number}')
            item = OrderItem.objects.create(order=order, product=self.shirt, product_name='Camisa', unit_price=Decimal('85.00'))
            Review.objects.create(order_item=item, user=self.other_buyer, rating=3, comment=f'Comentário {number}')
        response = self.client.get(reverse('product_detail', args=[self.shirt.pk]))
        self.assertEqual(len(response.context['reviews']), 10)
        self.assertEqual(response.context['rating']['count'], 12)
        self.assertContains(response, 'Comentário 11')
        self.assertNotContains(response, 'Comentário 0<')
