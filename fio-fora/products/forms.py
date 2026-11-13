from decimal import Decimal
from urllib.parse import urlencode

from django import forms

from . import services
from .models import (LIMITE_LEVE, LIMITE_MODERADA, Defeito, Product, ProductImage,
                     detalhar_severidade)


class MultipleFileInput(forms.ClearableFileInput):
    """Input de arquivo que aceita vários de uma vez.

    O Django 5 deixou de permitir `multiple` no widget padrão; este widget e o
    campo abaixo são a receita da documentação oficial.
    """
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('widget', MultipleFileInput(attrs={'accept': 'image/*'}))
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        clean_one = super().clean
        if isinstance(data, (list, tuple)):
            return [clean_one(item, initial) for item in data]
        return [clean_one(data, initial)] if data else []


def discount_preview(original_price, tipo, localizacao, extensao):
    """Use o próprio model: não mantenha uma segunda fórmula no formulário.

    Monta um Product e um Defeito não salvos, ligados em memória: isso não
    toca o banco e o cálculo fica inteiramente a cargo das properties do model.
    """
    product = Product(original_price=original_price)
    product.defeito = Defeito(tipo=tipo, localizacao=localizacao, extensao=extensao)
    return {
        'severity': product.severity,
        'severity_label': product.severity_label,
        'severity_band': product.severity_band,
        'discount': product.suggested_discount,
        'original_price': product.original_price,
        'final_price': product.suggested_price,
        # Quanto cada critério somou na nota, para a tela mostrar a conta aberta.
        'breakdown': detalhar_severidade(tipo, localizacao, extensao),
        'limit_leve': LIMITE_LEVE,
        'limit_moderada': LIMITE_MODERADA,
    }


class DefectFieldsMixin(forms.Form):
    """Os três critérios do defeito, usados pelo simulador e pelo cadastro de peça."""
    defect_type = Defeito._meta.get_field('tipo').formfield()
    defect_location = Defeito._meta.get_field('localizacao').formfield()
    defect_extent = Defeito._meta.get_field('extensao').formfield()


class DiscountSimulationForm(DefectFieldsMixin):
    original_price = Product._meta.get_field('original_price').formfield(required=True, min_value=Decimal('0.01'))
    field_order = ['original_price', 'defect_type', 'defect_location', 'defect_extent']

    # Nome na URL (português, como todo caminho do site) -> campo do formulário (inglês).
    QUERY_PARAMS = {
        'tipo': 'defect_type',
        'local': 'defect_location',
        'extensao': 'defect_extent',
        'preco': 'original_price',
    }

    @classmethod
    def from_query(cls, params):
        """Formulário vindo de /simulador/?tipo=&local=&extensao=&preco=.

        Sem nenhum desses parâmetros o formulário fica vazio (sem erros em
        vermelho antes de a pessoa preencher qualquer coisa).
        """
        data = {campo: params[chave] for chave, campo in cls.QUERY_PARAMS.items() if params.get(chave)}
        return cls(data or None)

    @classmethod
    def query_for(cls, product):
        """Query string do link “Entender o desconto” que a página da peça mostra."""
        defeito = getattr(product, 'defeito', None)
        if defeito is None:
            return ''
        return urlencode({
            'tipo': defeito.tipo,
            'local': defeito.localizacao,
            'extensao': defeito.extensao,
            'preco': product.original_price or product.price,
        })

    def preview(self):
        data = self.cleaned_data
        return discount_preview(data['original_price'], data['defect_type'], data['defect_location'], data['defect_extent'])


class ProductForm(DefectFieldsMixin, forms.ModelForm):
    """Cadastro e edição de peça pelo vendedor.

    O preço final e o vendedor são definidos no servidor, nunca pelo POST:
    o preço vem da severidade do defeito e o vendedor vem da view.
    """
    photos = MultipleFileField(
        label='Fotos da peça', required=False,
        help_text=f'Até {services.MAX_PHOTOS} fotos, {services.FORMAT_NAMES}, '
                  f'{services.MAX_BYTES // (1024 * 1024)} MB cada, mínimo '
                  f'{services.MIN_SIDE} px no menor lado. A primeira vira a capa.',
    )
    defect_photo = forms.ImageField(
        label='Foto do defeito', required=False,
        widget=forms.ClearableFileInput(attrs={'accept': 'image/*'}),
        help_text='Enquadre o defeito de perto. É a foto que explica o desconto.',
    )

    field_order = [
        'name', 'brand', 'category', 'size', 'condition', 'measurements',
        'description', 'original_price', 'defect_type', 'defect_location',
        'defect_extent', 'defect_measure_cm', 'visible_when_worn', 'stock',
        'photos', 'defect_photo', 'is_active',
    ]

    class Meta:
        model = Product
        fields = [
            'name', 'brand', 'category', 'size', 'condition', 'measurements',
            'description', 'original_price', 'defect_measure_cm', 'visible_when_worn',
            'stock', 'is_active',
        ]
        labels = {'name': 'Nome da peça', 'description': 'Descrição da peça e do defeito',
                  'is_active': 'Exibir na vitrine'}
        help_texts = {'original_price': 'O preço final será calculado pela regra de severidade do model.'}
        widgets = {'description': forms.Textarea(attrs={'rows': 4}),
                   'measurements': forms.Textarea(attrs={'rows': 2})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['original_price'].required = True
        self.fields['original_price'].widget.attrs['min'] = '0.01'
        self.fields['defect_measure_cm'].widget.attrs['min'] = '0'
        self.fields['stock'].min_value = 1
        self.fields['stock'].widget.attrs['min'] = '1'
        self.fields['size'].widget.attrs['placeholder'] = 'Ex.: P, M, G ou 38'
        self.fields['measurements'].widget.attrs['placeholder'] = 'Ex.: Busto 100 cm · Comprimento 70 cm'
        defeito = getattr(self.instance, 'defeito', None)
        if defeito is not None:
            self.initial.update(defect_type=defeito.tipo, defect_location=defeito.localizacao,
                                defect_extent=defeito.extensao)

    def clean_size(self):
        # "m", " M " e "M" viram o mesmo tamanho, e o filtro da vitrine não repete opções.
        return self.cleaned_data['size'].strip().upper()

    def clean_stock(self):
        stock = self.cleaned_data['stock']
        if stock < 1:
            raise forms.ValidationError('Informe pelo menos uma peça em estoque.')
        return stock

    def clean_photos(self):
        """Abre cada arquivo para conferir que é mesmo uma imagem."""
        uploads = self.cleaned_data.get('photos') or []
        self._photos = services.validate_images(uploads, 'As fotos da peça')
        return uploads

    def clean_defect_photo(self):
        """A foto do defeito é obrigatória enquanto a peça não tiver uma.

        Anunciar defeito sem mostrar o defeito é o que as entrevistas
        apontaram como motivo de ninguém confiar em brechó online.
        """
        upload = self.cleaned_data.get('defect_photo')
        if not upload:
            tem_foto = self.instance.pk and self.instance.images.filter(is_defect=True).exists()
            if not tem_foto:
                raise forms.ValidationError('Envie a foto do defeito: sem ela a peça não pode ser publicada.')
            return None
        self._defect_photo = services.validate_image(upload, 'A foto do defeito')
        return upload

    def clean(self):
        cleaned = super().clean()
        fields = ['original_price', 'defect_type', 'defect_location', 'defect_extent']
        if all(cleaned.get(name) is not None for name in fields):
            # Liga o defeito à peça em memória antes das validações do model,
            # para que o preço sugerido já possa ser calculado.
            defeito = getattr(self.instance, 'defeito', None) or Defeito()
            defeito.tipo = cleaned['defect_type']
            defeito.localizacao = cleaned['defect_location']
            defeito.extensao = cleaned['defect_extent']
            self.instance.defeito = defeito
            # O ModelForm só copia os campos para o model depois do clean().
            self.instance.original_price = cleaned['original_price']
            self.instance.price = self.instance.suggested_price
        return cleaned

    def save(self, commit=True):
        product = super().save(commit=commit)
        if commit:
            product.defeito.product = product
            product.defeito.save()
            self._save_photos(product)
        return product

    def _save_photos(self, product):
        """Grava as fotos enviadas. Uma foto do defeito nova substitui a antiga."""
        for image in getattr(self, '_photos', []):
            ProductImage.objects.create(
                product=product, image=image, is_defect=False,
                alt_text=f'{product.name} — foto da peça'[:160],
            )
        defect = getattr(self, '_defect_photo', None)
        if defect:
            for old in product.images.filter(is_defect=True):
                old.delete()
            ProductImage.objects.create(
                product=product, image=defect, is_defect=True,
                alt_text=f'{product.name} — close do defeito'[:160],
            )
