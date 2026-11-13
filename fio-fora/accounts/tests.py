import re
from datetime import datetime, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import PasswordResetTokenGenerator, default_token_generator
from django.core import mail
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from .fields import CEPField, CNPJField, CPFField, PhoneField, SocialField, split_location
from .models import UserProfile

OLD_PASSWORD = 'Senha-antiga-524!'
NEW_PASSWORD = 'Senha-nova-9817!'


class AuthPageTests(TestCase):
    def test_login_is_the_initial_page(self):
        self.assertEqual(reverse('login'), '/')
        self.assertEqual(reverse('home'), '/vitrine/')

    def test_auth_pages_open_successfully(self):
        urls = [reverse('login'), reverse('password_reset'), reverse('signup')]
        urls += [reverse('register', args=[role]) for role in ('comprador', 'vendedor', 'marca')]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_login_has_help_link_to_example_accounts(self):
        self.assertContains(self.client.get(reverse('login')), 'fio-fora/seed/README.md')

    def test_unknown_account_type_returns_404(self):
        self.assertEqual(self.client.get(reverse('register', args=['outro'])).status_code, 404)

    def test_password_is_never_put_in_a_url(self):
        urls = [reverse('login')] + [reverse('register', args=[role]) for role in ('comprador', 'vendedor', 'marca')]
        for url in urls:
            with self.subTest(url=url):
                response = self.client.post(url, {'password': 'senha-de-teste'})
                self.assertEqual(response.status_code, 200)  # o formulário volta com erros, sem redirecionar
                self.assertNotIn('senha-de-teste', response.get('Location', ''))

    def test_shared_base_and_page_specific_styles(self):
        login = self.client.get(reverse('login'))
        vitrine = self.client.get(reverse('home'))
        for response in [login, vitrine]:
            self.assertContains(response, 'css/site.css')
            self.assertContains(response, 'images/logo-mark.png')
        self.assertContains(login, 'accounts/css/auth.css')
        self.assertNotContains(login, 'products/css/products.css')
        self.assertContains(vitrine, 'products/css/products.css')


class UserListTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        for username, name, role, store, active in [
            ("ana", "Ana Silva", "buyer", "", True),
            ("clara", "Clara Lima", "buyer", "", False),
            ("fabio", "Fábio Rocha", "brand", "Ateliê Circular", True),
        ]:
            user = get_user_model().objects.create_user(username, first_name=name, is_active=active)
            UserProfile.objects.create(user=user, role=role, store_name=store)
        cls.staff = get_user_model().objects.create_user("equipe", is_staff=True)

    def test_list_requires_staff(self):
        self.assertEqual(self.client.get(reverse("user_list")).status_code, 302)
        self.client.force_login(get_user_model().objects.get(username="ana"))
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


class RecuperarSenhaTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            'ana@example.com', email='ana@example.com', password=OLD_PASSWORD)

    def pedir_link(self, email='ana@example.com'):
        return self.client.post(reverse('password_reset'), {'email': email})

    def link_do_email(self):
        match = re.search(r'https?://\S+', mail.outbox[-1].body)
        self.assertIsNotNone(match)
        return match.group(0).replace('http://testserver', '')

    def test_telas_abrem(self):
        for name in ['password_reset', 'password_reset_done', 'password_reset_complete']:
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

    def test_email_tem_versao_html_com_botao_e_link(self):
        self.pedir_link()
        message = mail.outbox[0]
        self.assertEqual(message.subject, 'Recuperação de senha - FioFora')
        self.assertEqual(len(message.alternatives), 1)
        html, mimetype = message.alternatives[0]
        self.assertEqual(mimetype, 'text/html')
        for text in ['Criar nova senha', '/recuperar-senha/', '60 minutos', 'Equipe FioFora']:
            self.assertIn(text, html)

    def test_falha_no_envio_nao_da_erro_e_fica_no_log(self):
        # O Django registra a falha no log e mantém a resposta igual, para não revelar quem tem conta.
        with patch('django.contrib.auth.forms.EmailMultiAlternatives.send', side_effect=OSError('sem rede')):
            with self.assertLogs('django.contrib.auth', level='ERROR'):
                response = self.pedir_link()
        self.assertRedirects(response, reverse('password_reset_done'))

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
        self.assertContains(self.client.get(reverse('login')), reverse('password_reset'))


class BrazilianFieldsTests(TestCase):
    """Campos de accounts/fields.py: aceitam com ou sem pontuação e guardam só o que importa."""

    def test_cpf(self):
        field = CPFField()
        self.assertEqual(field.clean('123.456.789-09'), '12345678909')
        self.assertEqual(field.clean('12345678909'), '12345678909')
        for wrong in ['123.456.789-00', '111.111.111-11', '1234567890']:
            with self.subTest(cpf=wrong), self.assertRaises(ValidationError):
                field.clean(wrong)
        self.assertEqual(field.prepare_value('12345678909'), '123.456.789-09')

    def test_cep(self):
        field = CEPField()
        self.assertEqual(field.clean('20040-020'), '20040020')
        self.assertEqual(field.clean('20040020'), '20040020')
        for wrong in ['2004-020', '00000-000', '2004002', 'abcde-fgh']:
            with self.subTest(cep=wrong), self.assertRaises(ValidationError):
                field.clean(wrong)
        self.assertEqual(field.prepare_value('20040020'), '20040-020')

    def test_cnpj_numeric_and_alphanumeric(self):
        field = CNPJField()
        self.assertEqual(field.clean('11.222.333/0001-81'), '11222333000181')
        # Exemplo oficial do CNPJ com letras (Serpro), aceito também em minúsculas.
        self.assertEqual(field.clean('12.abc.345/01de-35'), '12ABC34501DE35')
        for wrong in ['11.222.333/0001-80', '00.000.000/0000-00', '12.ABC.345/01DE-3X']:
            with self.subTest(cnpj=wrong), self.assertRaises(ValidationError):
                field.clean(wrong)
        self.assertEqual(field.prepare_value('12ABC34501DE35'), '12.ABC.345/01DE-35')

    def test_phone_mobile_landline_and_country_code(self):
        field = PhoneField()
        self.assertEqual(field.clean('(21) 99999-8888'), '21999998888')
        self.assertEqual(field.clean('(11) 3333-4444'), '1133334444')
        self.assertEqual(field.clean('+55 21 99999-8888'), '21999998888')
        for wrong in ['(21) 89999-8888', '(01) 99999-8888', '99999-8888', '(11) 7333-4444']:
            with self.subTest(phone=wrong), self.assertRaises(ValidationError):
                field.clean(wrong)
        self.assertEqual(field.prepare_value('1133334444'), '(11) 3333-4444')

    def test_social(self):
        field = SocialField(required=False)
        self.assertEqual(field.clean('https://www.instagram.com/fios.do_rio/'), '@fios.do_rio')
        self.assertEqual(field.clean('fiosdorio.com.br'), 'fiosdorio.com.br')
        for wrong in ['@fios do rio', 'fiosdorio']:
            with self.subTest(social=wrong), self.assertRaises(ValidationError):
                field.clean(wrong)

    def test_split_location(self):
        self.assertEqual(split_location('Rio de Janeiro, RJ'), ('Rio de Janeiro', 'RJ'))
        # Texto antigo, fora do padrão "Cidade, UF", vai inteiro para a cidade.
        self.assertEqual(split_location('Niterói'), ('Niterói', ''))


class RegistrationFieldsTests(TestCase):
    def post_register(self, role, **overrides):
        data = {'name': 'Julia Prado', 'email': 'julia@example.com', 'phone': '(11) 98888-2001',
                'store_name': 'Segunda Volta', 'document': '123.456.789-09',
                'city': 'São Paulo', 'state': 'SP',
                'password1': 'Senha-forte-524!', 'password2': 'Senha-forte-524!', 'terms': 'on'}
        data.update(overrides)
        return self.client.post(reverse('register', args=[role]), data)

    def test_seller_profile_saves_only_digits_and_joins_location(self):
        self.assertRedirects(self.post_register('vendedor'), reverse('login'))
        profile = UserProfile.objects.get(user__email='julia@example.com')
        self.assertEqual(profile.document, '12345678909')
        self.assertEqual(profile.phone, '11988882001')
        self.assertEqual(profile.location, 'São Paulo, SP')

    def test_invalid_cpf_or_state_keeps_the_form_with_errors(self):
        for overrides in [{'document': '123.456.789-00'}, {'state': 'XX'}, {'phone': '9999-8888'}]:
            with self.subTest(overrides=overrides):
                response = self.post_register('vendedor', **overrides)
                self.assertEqual(response.status_code, 200)
                self.assertFalse(UserProfile.objects.exists())

    def test_brand_accepts_alphanumeric_cnpj_and_instagram_link(self):
        response = self.post_register('marca', document='12.ABC.345/01DE-35', legal_name='Segunda Volta Ltda.',
                                      segment='moda', social='instagram.com/segundavolta')
        self.assertRedirects(response, reverse('login'))
        profile = UserProfile.objects.get(user__email='julia@example.com')
        self.assertEqual(profile.document, '12ABC34501DE35')
        self.assertEqual(profile.social, '@segundavolta')

    def test_register_page_shows_formats(self):
        response = self.client.get(reverse('register', args=['vendedor']))
        self.assertContains(response, 'placeholder="000.000.000-00"')
        self.assertContains(response, 'data-mask="phone"')
        self.assertContains(response, '<option value="RJ">Rio de Janeiro</option>', html=True)


class AccountPageFieldsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('julia@example.com', email='julia@example.com',
                                                         first_name='Julia Prado')
        UserProfile.objects.create(user=self.user, role='seller', phone='11988882001',
                                   location='São Paulo, SP')
        self.client.force_login(self.user)

    def test_shows_saved_values_formatted(self):
        response = self.client.get(reverse('account'))
        self.assertContains(response, 'value="(11) 98888-2001"')
        self.assertContains(response, 'value="São Paulo"')
        self.assertContains(response, '<option value="SP" selected>São Paulo</option>', html=True)

    def test_saves_city_and_state_together(self):
        data = {'name': 'Julia Prado', 'email': 'julia@example.com', 'phone': '(21) 3333-4444',
                'store_name': 'Segunda Volta', 'city': 'Niterói', 'state': 'RJ'}
        self.assertRedirects(self.client.post(reverse('account'), data), reverse('account'))
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.location, 'Niterói, RJ')
        self.assertEqual(self.user.profile.phone, '2133334444')

        response = self.client.post(reverse('account'), {**data, 'state': ''})
        self.assertContains(response, 'Preencha a cidade e o estado juntos.')


class AccountAddressTests(TestCase):
    """Endereço de entrega no perfil do comprador."""

    DATA = {'name': 'Ana Lima', 'email': 'ana@example.com', 'phone': '', 'store_name': '', 'city': '', 'state': '',
            'cep': '20040-020', 'street': 'Rua da Assembleia', 'number': '10', 'complement': '',
            'district': 'Centro', 'address_city': 'Rio de Janeiro', 'address_state': 'RJ'}

    def setUp(self):
        self.user = get_user_model().objects.create_user('ana@example.com', email='ana@example.com',
                                                         first_name='Ana Lima')
        UserProfile.objects.create(user=self.user, role='buyer')
        self.client.force_login(self.user)

    def test_buyer_saves_address_with_digits_only_cep(self):
        self.assertRedirects(self.client.post(reverse('account'), self.DATA), reverse('account'))
        profile = UserProfile.objects.get(user=self.user)
        self.assertEqual(profile.address_cep, '20040020')
        self.assertEqual(profile.address_street, 'Rua da Assembleia')
        self.assertEqual(profile.address_location, 'Rio de Janeiro, RJ')
        response = self.client.get(reverse('account'))
        self.assertContains(response, 'value="20040-020"')
        self.assertContains(response, 'value="Rua da Assembleia"')

    def test_address_is_optional_but_cannot_be_half_filled(self):
        empty = {**self.DATA, 'cep': '', 'street': '', 'number': '', 'district': '',
                 'address_city': '', 'address_state': ''}
        self.assertRedirects(self.client.post(reverse('account'), empty), reverse('account'))
        response = self.client.post(reverse('account'), {**empty, 'cep': '20040-020'})
        self.assertContains(response, 'Preencha o endereço completo')
        self.assertEqual(UserProfile.objects.get(user=self.user).address_cep, '')

    def test_cleaning_the_fields_removes_the_saved_address(self):
        self.client.post(reverse('account'), self.DATA)
        empty = {**self.DATA, 'cep': '', 'street': '', 'number': '', 'district': '',
                 'address_city': '', 'address_state': ''}
        self.client.post(reverse('account'), empty)
        self.assertEqual(UserProfile.objects.get(user=self.user).address_street, '')

    def test_seller_does_not_get_the_address_section(self):
        seller = get_user_model().objects.create_user('loja@example.com', email='loja@example.com')
        UserProfile.objects.create(user=seller, role='seller', address_street='Rua Antiga')
        self.client.force_login(seller)
        self.assertNotContains(self.client.get(reverse('account')), 'Endereço de entrega')
        data = {'name': 'Loja', 'email': 'loja@example.com', 'phone': '', 'store_name': 'Loja', 'city': '', 'state': ''}
        self.assertRedirects(self.client.post(reverse('account'), data), reverse('account'))
        self.assertEqual(UserProfile.objects.get(user=seller).address_street, 'Rua Antiga')
