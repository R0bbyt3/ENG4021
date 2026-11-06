from django import forms
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .fields import (
    CityField, CNPJField, CPFField, PhoneField, SocialField, StateField, join_location, split_location,
)
from .models import UserProfile


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(label='E-mail', max_length=150, widget=forms.EmailInput(attrs={
        'autocomplete': 'email', 'autofocus': True,
    }))
    remember = forms.BooleanField(label='Lembrar de mim', required=False, initial=True)
    error_messages = {
        'invalid_login': 'E-mail ou senha inválidos. Confira os dados e tente novamente.',
        'inactive': 'E-mail ou senha inválidos. Confira os dados e tente novamente.',
    }

    def clean(self):
        email = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        if email and password:
            self.user_cache = authenticate(self.request, email=email, password=password)
            if self.user_cache is None:
                raise self.get_invalid_login_error()
            self.confirm_login_allowed(self.user_cache)
        return self.cleaned_data


class BuyerRegistrationForm(UserCreationForm):
    name = forms.CharField(label='Nome completo', max_length=150)
    email = forms.EmailField(label='E-mail', max_length=150)
    phone = PhoneField(required=False)
    terms = forms.BooleanField(label='Li e aceito os termos de uso e a política de privacidade.')
    role = UserProfile.Role.BUYER
    profile_fields = ['phone']

    class Meta:
        model = get_user_model()
        fields = ['name', 'email', 'phone', 'password1', 'password2', 'terms']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].widget.attrs['autocomplete'] = 'name'
        self.fields['email'].widget.attrs['autocomplete'] = 'email'

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        users = get_user_model().objects.filter(Q(email__iexact=email) | Q(username__iexact=email))
        if users.exists():
            raise forms.ValidationError('Já existe uma conta com este e-mail.')
        return email

    def clean(self):
        cleaned_data = super().clean()
        self.instance.username = cleaned_data.get('email', '')
        self.instance.first_name = cleaned_data.get('name', '')
        return cleaned_data

    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            profile_data = {field: self.cleaned_data[field] for field in self.profile_fields}
            UserProfile.objects.create(
                user=user,
                role=self.role,
                terms_accepted_at=timezone.now(),
                **profile_data,
            )
        return user


class SellerRegistrationForm(BuyerRegistrationForm):
    store_name = forms.CharField(label='Nome da loja', max_length=120, required=False)
    document = CPFField(label='CPF')
    city = CityField()
    state = StateField()
    role = UserProfile.Role.SELLER
    # "location" não é um campo do formulário: o clean() junta cidade e estado nele.
    profile_fields = ['phone', 'store_name', 'document', 'location']

    class Meta(BuyerRegistrationForm.Meta):
        fields = [
            'name', 'email', 'phone', 'store_name', 'document', 'city', 'state',
            'password1', 'password2', 'terms',
        ]

    def clean(self):
        cleaned_data = super().clean()
        cleaned_data['location'] = join_location(cleaned_data.get('city'), cleaned_data.get('state'))
        return cleaned_data


class BrandRegistrationForm(SellerRegistrationForm):
    name = forms.CharField(label='Responsável pela marca', max_length=150)
    store_name = forms.CharField(label='Nome da marca', max_length=120)
    document = CNPJField(label='CNPJ')
    legal_name = forms.CharField(label='Razão social', max_length=150)
    segment = forms.ChoiceField(label='Atividade principal', choices=[
        ('', 'Selecione uma opção'),
        ('moda', 'Moda e vestuário'),
        ('acessorios', 'Acessórios'),
        ('calcados', 'Calçados'),
        ('casa', 'Casa e decoração'),
    ])
    social = SocialField(max_length=200, required=False)
    role = UserProfile.Role.BRAND
    profile_fields = SellerRegistrationForm.profile_fields + ['legal_name', 'segment', 'social']

    class Meta(BuyerRegistrationForm.Meta):
        fields = [
            'store_name', 'document', 'legal_name', 'segment', 'city', 'state',
            'name', 'email', 'phone', 'social', 'password1', 'password2', 'terms',
        ]


class AccountProfileForm(forms.Form):
    name = forms.CharField(label='Nome completo', max_length=150)
    email = forms.EmailField(label='E-mail', max_length=150)
    phone = PhoneField(required=False)
    password = forms.CharField(
        label='Nova senha',
        required=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
        help_text='Opcional. Deixe em branco para manter a senha atual.',
    )
    store_name = forms.CharField(label='Loja ou marca', max_length=120, required=False)
    city = CityField(required=False)
    state = StateField(required=False)

    def __init__(self, user, *args, **kwargs):
        self.user = user
        self.profile = getattr(user, 'profile', None)
        super().__init__(*args, **kwargs)
        self.initial.setdefault('name', user.get_full_name() or user.username)
        self.initial.setdefault('email', user.email)
        self.initial.setdefault('phone', self.profile.phone if self.profile else '')
        self.initial.setdefault('store_name', self.profile.store_name if self.profile else '')
        city, state = split_location(self.profile.location if self.profile else '')
        self.initial.setdefault('city', city)
        self.initial.setdefault('state', state)
        for field in self.fields.values():
            field.widget.attrs['autocomplete'] = 'off'
        self.fields['name'].widget.attrs['autocomplete'] = 'name'
        self.fields['email'].widget.attrs['autocomplete'] = 'email'
        self.fields['phone'].widget.attrs['autocomplete'] = 'tel'
        self.fields['city'].widget.attrs['autocomplete'] = 'address-level2'
        self.fields['state'].widget.attrs['autocomplete'] = 'address-level1'
        self.fields['password'].widget.attrs['autocomplete'] = 'new-password'

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        users = get_user_model().objects.filter(
            Q(email__iexact=email) | Q(username__iexact=email)
        ).exclude(pk=self.user.pk)
        if users.exists():
            raise forms.ValidationError('Este e-mail já está associado a outra conta.')
        return email

    def clean(self):
        cleaned_data = super().clean()
        # Cidade e estado andam juntos: os dois preenchidos ou os dois vazios.
        if bool(cleaned_data.get('city')) != bool(cleaned_data.get('state')):
            raise forms.ValidationError('Preencha a cidade e o estado juntos.')
        return cleaned_data

    def clean_password(self):
        password = self.cleaned_data['password']
        if password:
            validate_password(password, user=self.user)
        return password

    @transaction.atomic
    def save(self):
        self.user.first_name = self.cleaned_data['name'].strip()
        self.user.email = self.cleaned_data['email']
        self.user.username = self.cleaned_data['email']
        if self.cleaned_data['password']:
            self.user.set_password(self.cleaned_data['password'])
        self.user.save()

        if not self.profile:
            self.profile = UserProfile(user=self.user)
        self.profile.phone = self.cleaned_data['phone']
        self.profile.store_name = self.cleaned_data['store_name'].strip()
        self.profile.location = join_location(self.cleaned_data['city'].strip(), self.cleaned_data['state'])
        self.profile.save()
        return self.user
