from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Favorite, Product


class FavoritosTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user('ana@example.com', email='ana@example.com', password='Strong-test-524!')
        self.other = User.objects.create_user('bia@example.com', email='bia@example.com', password='Strong-test-524!')
        self.product = Product.objects.create(name='Vestido', description='Mancha na barra',
                                              price=Decimal('80'), original_price=Decimal('100'))
        self.inactive = Product.objects.create(name='Saia', description='Fio puxado',
                                               price=Decimal('50'), is_active=False)

    def test_visitante_e_enviado_para_o_login(self):
        for response in [
            self.client.get(reverse('favorites')),
            self.client.post(reverse('favorite_add', args=[self.product.pk])),
            self.client.post(reverse('favorite_remove', args=[self.product.pk])),
        ]:
            self.assertEqual(response.status_code, 302)
            self.assertIn(reverse('login'), response['Location'])
        self.assertEqual(Favorite.objects.count(), 0)

    def test_adicionar_grava_no_banco_e_aparece_na_pagina(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('favorite_add', args=[self.product.pk]), follow=True)
        self.assertTrue(Favorite.objects.filter(user=self.user, product=self.product).exists())
        self.assertContains(response, 'Vestido')

    def test_adicionar_duas_vezes_nao_duplica(self):
        self.client.force_login(self.user)
        for _ in range(2):
            self.client.post(reverse('favorite_add', args=[self.product.pk]))
        self.assertEqual(Favorite.objects.filter(user=self.user).count(), 1)

    def test_remover_apaga_do_banco(self):
        Favorite.objects.create(user=self.user, product=self.product)
        self.client.force_login(self.user)
        self.client.post(reverse('favorite_remove', args=[self.product.pk]))
        self.assertFalse(Favorite.objects.filter(user=self.user).exists())

    def test_remover_nao_mexe_no_favorito_de_outro_usuario(self):
        Favorite.objects.create(user=self.other, product=self.product)
        self.client.force_login(self.user)
        self.client.post(reverse('favorite_remove', args=[self.product.pk]))
        self.assertTrue(Favorite.objects.filter(user=self.other, product=self.product).exists())

    def test_pagina_mostra_so_os_favoritos_do_proprio_usuario(self):
        Favorite.objects.create(user=self.user, product=self.product)
        Favorite.objects.create(user=self.other, product=self.inactive)
        self.client.force_login(self.user)
        response = self.client.get(reverse('favorites'))
        self.assertContains(response, 'Vestido')
        self.assertNotContains(response, 'Saia')

    def test_pagina_vazia_tem_mensagem(self):
        self.client.force_login(self.user)
        self.assertContains(self.client.get(reverse('favorites')), 'ainda não favoritou')

    def test_nao_favorita_peca_inativa_nem_inexistente(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.post(reverse('favorite_add', args=[self.inactive.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse('favorite_add', args=[9999])).status_code, 404)
        self.assertEqual(Favorite.objects.count(), 0)

    def test_get_nao_altera_dados(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('favorite_add', args=[self.product.pk]))
        self.assertEqual(response.status_code, 405)
        self.assertEqual(Favorite.objects.count(), 0)

    def test_next_externo_e_ignorado(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('favorite_add', args=[self.product.pk]), {'next': 'https://evil.example/'})
        self.assertRedirects(response, reverse('favorites'))

    def test_next_interno_volta_para_a_vitrine(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('favorite_add', args=[self.product.pk]), {'next': reverse('home')})
        self.assertRedirects(response, reverse('home'))

    def test_vitrine_mostra_botao_conforme_o_estado(self):
        self.client.force_login(self.user)
        self.assertContains(self.client.get(reverse('home')), 'Favoritar')
        Favorite.objects.create(user=self.user, product=self.product)
        self.assertContains(self.client.get(reverse('home')), 'Favoritada')
