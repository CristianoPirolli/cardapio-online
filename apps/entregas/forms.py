# =============================================================================
# apps/entregas/forms.py - Formularios para gestao de entregadores
# =============================================================================

from django import forms
from django.contrib.auth.models import User
from .models import Entregador


class EntregadorForm(forms.ModelForm):
    """Formulario para criar/editar entregadores."""

    usuario = forms.ModelChoiceField(
        queryset=User.objects.none(),
        required=False,
        label='Usuário de Login (opcional)',
        help_text='Se informado, este usuário terá acesso ao painel de entregas atribuídas.'
    )

    class Meta:
        model = Entregador
        fields = ['usuario', 'nome', 'telefone', 'veiculo', 'disponivel', 'ativo']
        widgets = {
            'telefone': forms.TextInput(attrs={'placeholder': '(00) 00000-0000'}),
        }

    def __init__(self, *args, restaurante=None, **kwargs):
        super().__init__(*args, **kwargs)
        usuarios = User.objects.filter(is_active=True, is_superuser=False)
        if restaurante:
            # Mantém o usuário já vinculado na edição e evita usuários já usados em outro entregador.
            usuarios_indisponiveis = Entregador.objects.exclude(
                pk=self.instance.pk if self.instance and self.instance.pk else None
            ).values_list('usuario_id', flat=True)
            usuarios = usuarios.exclude(id__in=usuarios_indisponiveis).exclude(
                restaurante__isnull=False
            )
        self.fields['usuario'].queryset = usuarios.order_by('username')
