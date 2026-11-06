from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import (
    LoginView, PasswordResetCompleteView, PasswordResetConfirmView, PasswordResetDoneView, PasswordResetView,
)
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.db.models import Q
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy

from .forms import (
    AccountProfileForm, BrandRegistrationForm, BuyerRegistrationForm, EmailAuthenticationForm, SellerRegistrationForm,
)
from .models import UserProfile

# Cada tipo de conta tem seu formulário e seu título; a URL usa o nome em português.
REGISTRATION_FORMS = {
    'comprador': (BuyerRegistrationForm, 'Crie sua conta de comprador'),
    'vendedor': (SellerRegistrationForm, 'Crie sua conta de vendedor'),
    'marca': (BrandRegistrationForm, 'Apresente sua marca ao FioFora'),
}


class AccountLoginView(LoginView):
    template_name = 'accounts/login.html'
    authentication_form = EmailAuthenticationForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        response = super().form_valid(form)
        expiry = settings.SESSION_COOKIE_AGE if form.cleaned_data['remember'] else 0
        self.request.session.set_expiry(expiry)
        return response

    def get_success_url(self):
        return reverse('home')


def signup(request):
    """Etapa 1 do cadastro: escolher o tipo de conta."""
    return render(request, 'accounts/signup.html')


def register(request, role):
    """Etapa 2 do cadastro: o formulário do tipo de conta escolhido."""
    if role not in REGISTRATION_FORMS:
        raise Http404('Tipo de conta desconhecido.')
    form_class, title = REGISTRATION_FORMS[role]
    form = form_class(request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        try:
            form.save()
        except IntegrityError:
            form.add_error(None, 'Não foi possível criar a conta. Confira os dados e tente novamente.')
        else:
            messages.success(request, 'Conta criada. Entre com seu e-mail e senha.')
            return redirect('login')
    return render(request, 'accounts/register.html', {'form': form, 'title': title})


class PasswordResetRequestView(PasswordResetView):
    """1) O usuário informa o e-mail e recebe o link com o token."""
    template_name = 'accounts/password_reset.html'
    email_template_name = 'accounts/email/password_reset_email.txt'
    html_email_template_name = 'accounts/email/password_reset_email.html'
    subject_template_name = 'accounts/email/password_reset_subject.txt'
    success_url = reverse_lazy('password_reset_done')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['expiry_minutes'] = settings.PASSWORD_RESET_TIMEOUT // 60
        return context

    def form_valid(self, form):
        self.extra_email_context = {'expiry_minutes': settings.PASSWORD_RESET_TIMEOUT // 60}
        return super().form_valid(form)


class PasswordResetSentView(PasswordResetDoneView):
    """2) Aviso de envio. A mensagem é a mesma exista ou não a conta, para não revelar quem tem cadastro."""
    template_name = 'accounts/password_reset_done.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['expiry_minutes'] = settings.PASSWORD_RESET_TIMEOUT // 60
        return context


class PasswordResetNewPasswordView(PasswordResetConfirmView):
    """3) Link do e-mail: valida o token (e a expiração) e pede a nova senha."""
    template_name = 'accounts/password_reset_confirm.html'
    success_url = reverse_lazy('password_reset_complete')


class PasswordResetFinishedView(PasswordResetCompleteView):
    """4) Confirmação de que a senha foi trocada."""
    template_name = 'accounts/password_reset_complete.html'


@login_required
def account_page(request):
    form = AccountProfileForm(request.user)
    if request.method == 'POST':
        form = AccountProfileForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            if form.cleaned_data['password']:
                update_session_auth_hash(request, user)
            messages.success(request, 'Seus dados foram atualizados.')
            return redirect('account')

    profile = getattr(request.user, 'profile', None)
    display_name = request.user.get_full_name() or request.user.username
    return render(request, 'accounts/account.html', {
        'form': form,
        'profile': profile,
        'initials': display_name[:2].upper(),
    })


# Listagem administrativa: não expõe dados de usuários a visitantes.
@staff_member_required
def user_list(request):
    users = get_user_model().objects.select_related("profile").order_by("first_name", "last_name", "pk")
    q = request.GET.get("q", "").strip()[:120]
    role = request.GET.get("role", "")
    status = request.GET.get("status", "")
    if q:
        users = users.filter(Q(first_name__icontains=q) | Q(last_name__icontains=q)
                             | Q(username__icontains=q) | Q(email__icontains=q)
                             | Q(profile__store_name__icontains=q))
    if role in UserProfile.Role.values:
        users = users.filter(profile__role=role)
    elif role == "unassigned":
        users = users.filter(profile__isnull=True)
    if status in ["active", "inactive"]:
        users = users.filter(is_active=(status == "active"))
    total = users.count()
    page = Paginator(users, 10).get_page(request.GET.get("page"))
    query = request.GET.copy()
    query.pop("page", None)
    return render(request, "accounts/user_list.html", {
        "page_obj": page, "total": total, "q": q, "role": role, "status": status,
        "roles": UserProfile.Role.choices, "filter_query": query.urlencode(),
    })
