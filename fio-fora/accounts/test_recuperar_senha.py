import re
from datetime import datetime, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import PasswordResetTokenGenerator, default_token_generator
from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

OLD_PASSWORD = 'Senha-antiga-524!'
NEW_PASSWORD = 'Senha-nova-9817!'


class RecuperarSenhaTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            'ana@example.com', email='ana@example.com', password=OLD_PASSWORD)

    def pedir_link(self, email='ana@example.com'):
        return self.client.post(reverse('password_reset_page'), {'email': email})

    def link_do_email(self):
        match = re.search(r'https?://\S+', mail.outbox[-1].body)
        self.assertIsNotNone(match)
        return match.group(0).replace('http://testserver', '')

    def test_telas_abrem(self):
        for name in ['password_reset_page', 'password_reset_done', 'password_reset_complete']:
            with self.subTest(page=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)

    def test_pedido_envia_email_com_link_e_validade(self):
        response = self.pedir_link()
        self.assertRedirects(response, reverse('password_reset_done'))
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, ['ana@example.com'])
        self.assertIn('/recuperar-senha/', message.body)
        self.assertIn('60 minutos', message.body)

    def test_email_desconhecido_tem_a_mesma_resposta_e_nao_envia(self):
        response = self.pedir_link('ninguem@example.com')
        self.assertRedirects(response, reverse('password_reset_done'))
        self.assertEqual(len(mail.outbox), 0)

    def test_conta_inativa_nao_recebe_link(self):
        self.user.is_active = False
        self.user.save()
        self.pedir_link()
        self.assertEqual(len(mail.outbox), 0)

    def test_email_invalido_mostra_erro(self):
        response = self.pedir_link('isso-nao-e-email')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)

    def test_fluxo_completo_troca_a_senha(self):
        self.pedir_link()
        page = self.client.get(self.link_do_email(), follow=True)
        self.assertContains(page, 'Crie uma nova senha')
        response = self.client.post(page.redirect_chain[-1][0], {
            'new_password1': NEW_PASSWORD, 'new_password2': NEW_PASSWORD})
        self.assertRedirects(response, reverse('password_reset_complete'))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(NEW_PASSWORD))
        self.assertFalse(self.user.check_password(OLD_PASSWORD))
        self.client.logout()
        login = self.client.post(reverse('login'), {'username': 'ana@example.com', 'password': NEW_PASSWORD})
        self.assertRedirects(login, reverse('home'), fetch_redirect_response=False)

    def test_link_so_pode_ser_usado_uma_vez(self):
        self.pedir_link()
        link = self.link_do_email()
        page = self.client.get(link, follow=True)
        self.client.post(page.redirect_chain[-1][0], {
            'new_password1': NEW_PASSWORD, 'new_password2': NEW_PASSWORD})
        self.assertContains(self.client.get(link, follow=True), 'Este link não vale mais')

    def test_link_expirado_e_recusado(self):
        self.pedir_link()
        link = self.link_do_email()
        depois_do_prazo = datetime.now() + timedelta(hours=2)
        with patch.object(PasswordResetTokenGenerator, '_now', return_value=depois_do_prazo):
            self.assertContains(self.client.get(link, follow=True), 'Este link não vale mais')

    def test_link_dentro_do_prazo_e_aceito(self):
        self.pedir_link()
        link = self.link_do_email()
        dentro_do_prazo = datetime.now() + timedelta(minutes=50)
        with patch.object(PasswordResetTokenGenerator, '_now', return_value=dentro_do_prazo):
            self.assertContains(self.client.get(link, follow=True), 'Crie uma nova senha')

    def test_token_falso_e_recusado(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        url = reverse('password_reset_confirm', args=[uid, 'token-falso'])
        self.assertContains(self.client.get(url), 'Este link não vale mais')

    def test_senha_fraca_ou_diferente_nao_e_aceita(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)
        self.client.get(reverse('password_reset_confirm', args=[uid, token]))
        url = reverse('password_reset_confirm', args=[uid, 'set-password'])
        fraca = self.client.post(url, {'new_password1': '12345678', 'new_password2': '12345678'})
        diferente = self.client.post(url, {'new_password1': NEW_PASSWORD, 'new_password2': 'Outra-senha-111!'})
        self.assertEqual(fraca.status_code, 200)
        self.assertEqual(diferente.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(OLD_PASSWORD))

    def test_login_tem_link_para_recuperar_senha(self):
        self.assertContains(self.client.get(reverse('login_page')), reverse('password_reset_page'))
