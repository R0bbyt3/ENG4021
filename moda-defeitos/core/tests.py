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
