# =============================================================================
# apps/restaurantes/forms.py - Formulários do app restaurantes
#
# Formulários para registro de usuários e gestão de restaurantes.
# Usa crispy-forms com Bootstrap 5 para renderização bonita.
# =============================================================================

from django import forms
from django.forms import inlineformset_factory
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Restaurante, TamanhoPizza


class RegistroUsuarioForm(UserCreationForm):
    """
    Formulário de registro de novos usuários (proprietários de restaurante).

    Campos extras além do padrão UserCreationForm:
    - email: obrigatório para contato
    - first_name / last_name: nome completo
    """

    email = forms.EmailField(
        required=True,
        help_text='Obrigatório. Usado para notificações e recuperação de senha.'
    )
    first_name = forms.CharField(max_length=100, label='Nome')
    last_name = forms.CharField(max_length=100, label='Sobrenome')

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2']


class RestauranteForm(forms.ModelForm):
    """
    Formulário para criação e edição de restaurantes.

    Todos os campos essenciais são obrigatórios.
    O subdomínio é gerado automaticamente se não fornecido.
    """

    class Meta:
        model = Restaurante
        fields = [
            'nome', 'subdominio', 'descricao', 'endereco', 'cidade',
            'estado', 'cep', 'telefone', 'email', 'logo',
            'taxa_entrega', 'pedido_minimo', 'raio_entrega_km',
            'taxa_imposto', 'tempo_retirada_min', 'tempo_entrega_min',
            'funciona_segunda', 'funciona_terca', 'funciona_quarta',
            'funciona_quinta', 'funciona_sexta', 'funciona_sabado', 'funciona_domingo',
            'horario_abertura', 'horario_fechamento'
        ]
        widgets = {
            'descricao': forms.Textarea(attrs={'rows': 3}),
            'horario_abertura': forms.TimeInput(attrs={'type': 'time'}),
            'horario_fechamento': forms.TimeInput(attrs={'type': 'time'}),
        }


class TamanhoPizzaForm(forms.ModelForm):
    class Meta:
        model = TamanhoPizza
        fields = ['nome', 'fatias', 'diametro_cm', 'max_sabores', 'preco_base', 'ordem', 'ativo']
        widgets = {
            'diametro_cm': forms.NumberInput(attrs={'step': '0.1', 'min': '0.1'}),
            'preco_base': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
        }


TamanhoPizzaFormSet = inlineformset_factory(
    Restaurante,
    TamanhoPizza,
    form=TamanhoPizzaForm,
    fields=['nome', 'fatias', 'diametro_cm', 'max_sabores', 'preco_base', 'ordem', 'ativo'],
    extra=1,
    can_delete=True
)
