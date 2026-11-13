from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserProfile

from .services import notify


class NotificationPageTests(TestCase):
    """Página /avisos/ e sininho do cabeçalho."""

    def setUp(self):
        User = get_user_model()
        self.seller = User.objects.create_user('loja@example.com')
        UserProfile.objects.create(user=self.seller, role='seller')
        self.buyer = User.objects.create_user('ana@example.com')
        UserProfile.objects.create(user=self.buyer, role='buyer')

    def unread(self, user):
        self.client.force_login(user)
        return self.client.get(reverse('home')).context['unread_notifications']

    def test_visitor_is_sent_to_login_and_has_no_bell(self):
        response = self.client.get(reverse('notifications'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response['Location'])
        self.assertNotContains(self.client.get(reverse('home')), reverse('notifications'))

    def test_bell_shows_the_unread_count_for_any_account(self):
        notify(self.seller, 'Nova venda.', '/minhas-vendas/')
        notify(self.buyer, 'Peça enviada.', '/pedidos/')
        for user in [self.seller, self.buyer]:
            with self.subTest(user=user.username):
                self.client.force_login(user)
                self.assertContains(self.client.get(reverse('home')), 'class="nav-badge"')
                self.assertEqual(self.unread(user), 1)

    def test_page_lists_only_own_notices_newest_first(self):
        notify(self.seller, 'Primeiro aviso.', '/minhas-vendas/')
        notify(self.seller, 'Segundo aviso.', '/minhas-vendas/')
        notify(self.buyer, 'Aviso de outra pessoa.', '/pedidos/')
        self.client.force_login(self.seller)
        response = self.client.get(reverse('notifications'))
        self.assertEqual([item.text for item in response.context['notifications']],
                         ['Segundo aviso.', 'Primeiro aviso.'])
        self.assertNotContains(response, 'Aviso de outra pessoa.')

    def test_opening_the_page_highlights_new_ones_and_then_marks_them_read(self):
        notify(self.seller, 'Nova venda.', '/minhas-vendas/')
        self.client.force_login(self.seller)
        self.assertContains(self.client.get(reverse('notifications')), 'notification--unread')
        self.assertEqual(self.unread(self.seller), 0)
        self.assertNotContains(self.client.get(reverse('notifications')), 'notification--unread')

    def test_notice_links_to_its_page(self):
        notify(self.seller, 'Nova venda.', '/minhas-vendas/')
        self.client.force_login(self.seller)
        self.assertContains(self.client.get(reverse('notifications')), 'href="/minhas-vendas/"')

    def test_notices_on_a_page_not_opened_stay_unread(self):
        for number in range(21):
            notify(self.seller, f'Aviso {number}.', '/minhas-vendas/')
        self.client.force_login(self.seller)
        self.client.get(reverse('notifications'))
        self.assertEqual(self.unread(self.seller), 1)  # o mais antigo está na página 2
        self.client.force_login(self.seller)
        self.client.get(reverse('notifications') + '?page=2')
        self.assertEqual(self.unread(self.seller), 0)

    def test_empty_page_explains(self):
        self.client.force_login(self.buyer)
        self.assertContains(self.client.get(reverse('notifications')), 'Nenhum aviso por enquanto')
