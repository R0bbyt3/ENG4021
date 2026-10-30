from decimal import Decimal

from django import forms

from .models import Product, Defeito


SIMULATION_FIELDS = ('original_price', 'defect_type', 'defect_location', 'defect_extent')


def discount_preview(cleaned_data):
    """Use o próprio model: não mantenha uma segunda fórmula no formulário.

    Tipo/localização/extensão agora vivem no model Defeito, não em Product.
    Para uma simulação sem peça salva, montamos um Product e um Defeito
    não salvos e os ligamos em memória: isso não toca o banco, e o cálculo
    continua inteiramente a cargo das properties do model.
    """
    product = Product(original_price=cleaned_data['original_price'])
    product.defeito = Defeito(
        tipo=cleaned_data['defect_type'],
        localizacao=cleaned_data['defect_location'],
        extensao=cleaned_data['defect_extent'],
    )
    return {
        'severity': product.severity,
        'severity_label': product.severity_label,
        'discount': product.suggested_discount,
        'original_price': product.original_price,
        'final_price': product.suggested_price,
    }


def style_fields(fields):
    for field in fields.values():
        field.widget.attrs['class'] = 'form-control'
        if isinstance(field, forms.DecimalField):
            field.widget.attrs.update({'step': '0.01', 'min': '0.01'})


class DiscountSimulationForm(forms.Form):
    original_price = Product._meta.get_field('original_price').formfield(
        required=True, min_value=Decimal('0.01')
    )
    defect_type = Defeito._meta.get_field('tipo').formfield()
    defect_location = Defeito._meta.get_field('localizacao').formfield()
    defect_extent = Defeito._meta.get_field('extensao').formfield()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_fields(self.fields)

    def preview(self):
        return discount_preview(self.cleaned_data)


class ProductRegistrationForm(forms.ModelForm):
    # Tipo/localização/extensão não são mais campos de Product: vivem no
    # model Defeito, ligado 1-para-1 à peça. Ficam declarados aqui fora do
    # Meta.fields porque o ModelForm só sabe popular automaticamente campos
    # do próprio model; clean()/save_defeito() cuidam de ligá-los à peça.
    defect_type = Defeito._meta.get_field('tipo').formfield()
    defect_location = Defeito._meta.get_field('localizacao').formfield()
    defect_extent = Defeito._meta.get_field('extensao').formfield()

    # Preserva a ordem original dos campos no formulário (os campos
    # declarados acima viriam antes dos de Meta.fields, por padrão).
    field_order = [
        'name', 'brand', 'category', 'size', 'condition', 'measurements',
        'description', 'original_price', 'defect_type', 'defect_location',
        'defect_extent', 'defect_measure_cm', 'visible_when_worn', 'stock', 'is_active',
    ]

    class Meta:
        model = Product
        # Preço final e vendedor são definidos no servidor, nunca pelo POST.
        fields = [
            'name', 'brand', 'category', 'size', 'condition', 'measurements',
            'description', 'original_price', 'defect_measure_cm', 'visible_when_worn',
            'stock', 'is_active',
        ]
        labels = {'name': 'Nome da peça', 'description': 'Descrição da peça e do defeito',
                  'is_active': 'Exibir na vitrine'}
        widgets = {'description': forms.Textarea(attrs={'rows': 4}),
                   'measurements': forms.Textarea(attrs={'rows': 2})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['original_price'].required = True
        style_fields(self.fields)
        self.fields['defect_measure_cm'].widget.attrs['min'] = '0'
        self.fields['stock'].widget.attrs['min'] = '1'
        self.fields['stock'].min_value = 1
        self.fields['original_price'].help_text = (
            'O preço final será calculado pela regra de severidade do model.'
        )

    def clean(self):
        cleaned = super().clean()
        if all(name in cleaned and cleaned[name] is not None for name in SIMULATION_FIELDS):
            self.calculation = discount_preview(cleaned)
            # Antes da validação das constraints do ModelForm.
            self.instance.price = self.calculation['final_price']
            # Liga o defeito (ainda não salvo) à peça em memória, para que
            # instance.severity/suggested_price funcionem mesmo antes de
            # qualquer um dos dois ser gravado no banco.
            self.instance.defeito = Defeito(
                tipo=cleaned['defect_type'],
                localizacao=cleaned['defect_location'],
                extensao=cleaned['defect_extent'],
            )
        return cleaned

    def clean_stock(self):
        stock = self.cleaned_data['stock']
        if stock < 1:
            raise forms.ValidationError('Informe pelo menos uma peça em estoque.')
        return stock

    def save_defeito(self, product):
        """Chame depois de product.save(): grava o Defeito já ligado à peça salva."""
        defeito = self.instance.defeito
        defeito.product = product
        defeito.save()
        return defeito