"""Campos de formulário para dados brasileiros: CPF, CNPJ, telefone, estado e rede social.

Todos seguem a mesma receita:
1. No navegador: mostram o formato esperado, abrem o teclado certo no
   celular e, com static/js/masks.js, formatam enquanto a pessoa digita.
2. No servidor: aceitam o valor com ou sem pontuação, conferem se ele é
   possível e devolvem só os caracteres que importam (é o que vai para o banco).
3. Ao mostrar de novo: exibem o valor já formatado.
"""
import re

from django import forms
from django.core.exceptions import ValidationError


# ---------------------------------------------------------------------------
# Funções de apoio (sem Django): limpar, conferir e formatar.
# ---------------------------------------------------------------------------

def only_digits(value):
    return re.sub(r'\D', '', value or '')


def apply_pattern(chars, pattern):
    """Troca cada "#" do padrão pelo próximo caractere: ('11999998888', '(##) #####-####')."""
    chars = iter(chars)
    return re.sub('#', lambda match: next(chars, ''), pattern)


def cpf_is_valid(cpf):
    """Confere os 2 dígitos verificadores do CPF (os 2 últimos números)."""
    if len(cpf) != 11 or not cpf.isdigit() or cpf == cpf[0] * 11:
        return False
    for size in (9, 10):
        # Pesos decrescentes: 10, 9, ..., 2 para o 1º dígito; 11, 10, ..., 2 para o 2º.
        total = sum(int(digit) * weight for digit, weight in zip(cpf, range(size + 1, 1, -1)))
        if total * 10 % 11 % 10 != int(cpf[size]):
            return False
    return True


def cnpj_check_digit(base):
    """Dígito verificador do CNPJ. Desde 2026 a base pode ter letras.

    Regra da Receita Federal: cada caractere vale (código ASCII - 48), então
    "0" a "9" valem 0 a 9 e "A" vale 17. Os pesos vão de 2 a 9, da direita
    para a esquerda, e o resultado é um módulo 11.
    """
    weights = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2][-len(base):]
    rest = sum((ord(char) - 48) * weight for char, weight in zip(base, weights)) % 11
    return '0' if rest < 2 else str(11 - rest)


def cnpj_is_valid(cnpj):
    """12 caracteres de base (números ou letras) + 2 dígitos verificadores."""
    if not re.fullmatch(r'[0-9A-Z]{12}[0-9]{2}', cnpj) or cnpj == cnpj[0] * 14:
        return False
    first = cnpj_check_digit(cnpj[:12])
    second = cnpj_check_digit(cnpj[:12] + first)
    return cnpj[12:] == first + second


def phone_is_valid(phone):
    """DDD sem zero + celular (11 números, começa com 9) ou fixo (10 números, começa com 2 a 5)."""
    if '0' in phone[:2]:
        return False
    if len(phone) == 11:
        return phone[2] == '9'
    if len(phone) == 10:
        return phone[2] in '2345'
    return False


def format_cpf(cpf):
    return apply_pattern(cpf, '###.###.###-##') if len(cpf) == 11 else cpf


def format_cnpj(cnpj):
    return apply_pattern(cnpj, '##.###.###/####-##') if len(cnpj) == 14 else cnpj


def format_phone(phone):
    if len(phone) == 11:
        return apply_pattern(phone, '(##) #####-####')
    if len(phone) == 10:
        return apply_pattern(phone, '(##) ####-####')
    return phone


def format_cep(cep):
    return apply_pattern(cep, '#####-###') if len(cep) == 8 else cep


# ---------------------------------------------------------------------------
# Campos de formulário
# ---------------------------------------------------------------------------

class BrazilianField(forms.CharField):
    """Base dos campos abaixo. Cada filho só diz como limpar, conferir e formatar."""

    mask = ''          # nome da máscara em static/js/masks.js
    placeholder = ''   # formato que aparece dentro do campo vazio
    inputmode = 'numeric'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.widget.attrs.update({
            'data-mask': self.mask,
            'placeholder': self.placeholder,
            'inputmode': self.inputmode,
            'maxlength': len(self.placeholder),
        })

    def to_python(self, value):
        return self.normalize(super().to_python(value))

    def validate(self, value):
        super().validate(value)
        if value and not self.is_valid(value):
            raise ValidationError(self.error_messages['invalid'], code='invalid')

    def prepare_value(self, value):
        # Mostra o valor salvo (só números) já formatado.
        return self.display(self.normalize(value)) if value else value


class CPFField(BrazilianField):
    mask = 'cpf'
    placeholder = '000.000.000-00'
    default_error_messages = {'invalid': 'CPF inválido. Confira os 11 números.'}

    def normalize(self, value):
        return only_digits(value)

    def is_valid(self, value):
        return cpf_is_valid(value)

    def display(self, value):
        return format_cpf(value)


class CNPJField(BrazilianField):
    mask = 'cnpj'
    placeholder = '00.000.000/0000-00'
    inputmode = 'text'  # o CNPJ novo pode ter letras
    default_error_messages = {'invalid': 'CNPJ inválido. Confira os 14 caracteres.'}

    def normalize(self, value):
        return re.sub(r'[^0-9A-Z]', '', (value or '').upper())

    def is_valid(self, value):
        return cnpj_is_valid(value)

    def display(self, value):
        return format_cnpj(value)


class PhoneField(BrazilianField):
    mask = 'phone'
    placeholder = '(00) 00000-0000'
    inputmode = 'tel'
    default_error_messages = {'invalid': 'Telefone inválido. Informe o DDD e o número, como (21) 99999-8888.'}

    def __init__(self, **kwargs):
        kwargs.setdefault('label', 'Telefone')
        super().__init__(**kwargs)
        self.widget.attrs['autocomplete'] = 'tel'
        # Folga para o "+55 " do preenchimento automático não ser cortado.
        self.widget.attrs['maxlength'] = 20

    def normalize(self, value):
        phone = only_digits(value)
        # O preenchimento automático do navegador costuma colocar +55 na frente.
        if len(phone) in (12, 13) and phone.startswith('55'):
            phone = phone[2:]
        return phone

    def is_valid(self, value):
        return phone_is_valid(value)

    def display(self, value):
        return format_phone(value)


class CEPField(BrazilianField):
    mask = 'cep'
    placeholder = '00000-000'
    default_error_messages = {'invalid': 'CEP inválido. Informe os 8 números.'}

    def __init__(self, **kwargs):
        kwargs.setdefault('label', 'CEP')
        super().__init__(**kwargs)
        self.widget.attrs['autocomplete'] = 'postal-code'

    def normalize(self, value):
        return only_digits(value)

    def is_valid(self, value):
        return len(value) == 8 and value != '0' * 8

    def display(self, value):
        return format_cep(value)


STATES = [
    ('AC', 'Acre'), ('AL', 'Alagoas'), ('AP', 'Amapá'), ('AM', 'Amazonas'),
    ('BA', 'Bahia'), ('CE', 'Ceará'), ('DF', 'Distrito Federal'), ('ES', 'Espírito Santo'),
    ('GO', 'Goiás'), ('MA', 'Maranhão'), ('MT', 'Mato Grosso'), ('MS', 'Mato Grosso do Sul'),
    ('MG', 'Minas Gerais'), ('PA', 'Pará'), ('PB', 'Paraíba'), ('PR', 'Paraná'),
    ('PE', 'Pernambuco'), ('PI', 'Piauí'), ('RJ', 'Rio de Janeiro'), ('RN', 'Rio Grande do Norte'),
    ('RS', 'Rio Grande do Sul'), ('RO', 'Rondônia'), ('RR', 'Roraima'), ('SC', 'Santa Catarina'),
    ('SP', 'São Paulo'), ('SE', 'Sergipe'), ('TO', 'Tocantins'),
]


class StateField(forms.ChoiceField):
    """Lista dos 27 estados: escolher evita erro de digitação ("Rj", "R.J.", "Rio")."""

    def __init__(self, **kwargs):
        kwargs.setdefault('label', 'Estado')
        super().__init__(choices=[('', 'Selecione')] + STATES, **kwargs)
        self.widget.attrs['autocomplete'] = 'address-level1'


class CityField(forms.CharField):
    def __init__(self, **kwargs):
        kwargs.setdefault('label', 'Cidade')
        kwargs.setdefault('max_length', 100)
        super().__init__(**kwargs)
        self.widget.attrs.update({'autocomplete': 'address-level2', 'placeholder': 'Ex.: Rio de Janeiro'})


def join_location(city, state):
    """Cidade e estado viram um texto só no perfil: "Rio de Janeiro, RJ"."""
    return f'{city}, {state}' if city and state else ''


def split_location(location):
    """O contrário de join_location, para preencher os dois campos ao editar."""
    city, _, state = (location or '').rpartition(', ')
    if state in dict(STATES):
        return city, state
    return location or '', ''


class SocialField(forms.CharField):
    """Instagram (@perfil) ou endereço de site."""

    def __init__(self, **kwargs):
        kwargs.setdefault('label', 'Site ou Instagram')
        super().__init__(**kwargs)
        self.widget.attrs.update({'placeholder': '@sualoja ou sualoja.com.br', 'autocomplete': 'url'})

    def to_python(self, value):
        value = super().to_python(value)
        # Link do Instagram vira só o @perfil.
        match = re.search(r'instagram\.com/([\w.]+)', value)
        return f'@{match.group(1)}' if match else value

    def validate(self, value):
        super().validate(value)
        if not value:
            return
        if value.startswith('@'):
            if not re.fullmatch(r'@[\w.]{1,30}', value):
                raise ValidationError('Perfil do Instagram inválido. Use letras, números, ponto ou _.')
        elif ' ' in value or '.' not in value:
            raise ValidationError('Informe um @perfil do Instagram ou um site, como sualoja.com.br.')
