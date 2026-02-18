# =============================================================================
# apps/entregas/forms.py - Formularios para gestao de entregadores
# =============================================================================

from django import forms
from django.contrib.auth.models import User
from .models import Entregador


class EntregadorForm(forms.ModelForm):
    """Formulario para criar/editar entregadores e seu usuario de login."""

    username = forms.CharField(
        required=False,
        label='Usuário de Login',
        help_text='Se preenchido, cria/atualiza a conta do entregador. Em branco, remove o vínculo.'
    )
    email = forms.EmailField(
        required=False,
        label='E-mail do Usuário',
    )
    password1 = forms.CharField(
        required=False,
        label='Senha',
        widget=forms.PasswordInput(render_value=False),
        help_text='Obrigatória ao criar novo usuário de login.'
    )
    password2 = forms.CharField(
        required=False,
        label='Confirmar Senha',
        widget=forms.PasswordInput(render_value=False),
    )
    usuario_ativo = forms.BooleanField(
        required=False,
        label='Usuário de Login Ativo',
        initial=True
    )

    class Meta:
        model = Entregador
        fields = ['nome', 'telefone', 'veiculo', 'disponivel', 'ativo']
        widgets = {
            'telefone': forms.TextInput(attrs={'placeholder': '(00) 00000-0000'}),
        }

    def __init__(self, *args, restaurante=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.restaurante = restaurante
        self._existing_user = getattr(self.instance, 'usuario', None)

        if self._existing_user:
            self.fields['username'].initial = self._existing_user.username
            self.fields['email'].initial = self._existing_user.email
            self.fields['usuario_ativo'].initial = self._existing_user.is_active

        self.order_fields([
            'nome', 'telefone', 'veiculo', 'disponivel', 'ativo',
            'username', 'email', 'password1', 'password2', 'usuario_ativo'
        ])

    def clean_username(self):
        username = (self.cleaned_data.get('username') or '').strip()
        if not username:
            return ''

        qs = User.objects.filter(username__iexact=username)
        if self._existing_user:
            qs = qs.exclude(pk=self._existing_user.pk)
        if qs.exists():
            raise forms.ValidationError('Já existe um usuário com este login.')
        return username

    def clean(self):
        cleaned_data = super().clean()
        username = (cleaned_data.get('username') or '').strip()
        password1 = cleaned_data.get('password1') or ''
        password2 = cleaned_data.get('password2') or ''

        if username and password1 != password2:
            self.add_error('password2', 'As senhas não conferem.')

        if username and not self._existing_user and not password1:
            self.add_error('password1', 'Informe uma senha para o novo usuário.')

        if not username and (password1 or password2):
            self.add_error('username', 'Informe o usuário de login para definir senha.')

        return cleaned_data

    def save(self, commit=True):
        entregador = super().save(commit=False)

        username = (self.cleaned_data.get('username') or '').strip()
        email = (self.cleaned_data.get('email') or '').strip()
        password1 = self.cleaned_data.get('password1') or ''
        usuario_ativo = self.cleaned_data.get('usuario_ativo', True)

        if username:
            user = self._existing_user or User()
            user.username = username
            user.email = email
            user.is_active = usuario_ativo
            user.is_superuser = False
            user.is_staff = False
            if password1:
                user.set_password(password1)
            elif not user.pk:
                # Fallback defensivo para evitar salvar usuário sem senha válida.
                user.set_unusable_password()
            user.save()
            entregador.usuario = user
        else:
            entregador.usuario = None

        if commit:
            entregador.save()
        return entregador
