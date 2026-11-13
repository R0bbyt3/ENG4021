from django import forms

from accounts.forms import AddressFieldsMixin


class CheckoutAddressForm(AddressFieldsMixin):
    """Endereço de entrega do checkout: vem preenchido com o do perfil, mas pode ser trocado."""

    address_required = True

    save_to_profile = forms.BooleanField(label='Salvar como meu endereço padrão', required=False, initial=True)

    def __init__(self, *args, profile=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fill_address_from(profile)
