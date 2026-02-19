# =============================================================================
# apps/produtos/forms.py - Formulários para produtos e categorias
#
# Formulários usados no painel do restaurante para gestão de produtos.
# =============================================================================

from django import forms
from django.forms import inlineformset_factory
from apps.restaurantes.models import Restaurante
from .models import Categoria, Produto


class CategoriaForm(forms.ModelForm):
    """Formulário para criar/editar categorias de produtos."""

    class Meta:
        model = Categoria
        fields = ['nome', 'descricao', 'ordem', 'eh_pizza', 'adicional_sabor', 'ativo']
        widgets = {
            'descricao': forms.Textarea(attrs={'rows': 2}),
            'adicional_sabor': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
        }


class ProdutoForm(forms.ModelForm):
    """
    Formulário para criar/editar produtos.

    Inclui campo de upload de imagem com preview.
    O campo 'categoria' é filtrado para mostrar apenas categorias
    do restaurante atual.
    """

    class Meta:
        model = Produto
        fields = [
            'categoria', 'nome', 'descricao', 'preco',
            'imagem', 'disponivel', 'destaque'
        ]
        widgets = {
            'descricao': forms.Textarea(attrs={'rows': 3}),
            'preco': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
        }

    def __init__(self, *args, restaurante=None, **kwargs):
        """
        Inicializa o formulário filtrando categorias pelo restaurante.

        Args:
            restaurante: Instância do Restaurante para filtrar categorias.
        """
        super().__init__(*args, **kwargs)
        self.fields['categoria'].label = 'Categoria'
        self.fields['nome'].label = 'Nome do Produto'
        self.fields['preco'].label = 'Preço Padrão'
        self.fields['preco'].help_text = (
            'Usado como preço padrão do produto. Para pizzas, pode ser complemento quando houver tamanhos.'
        )
        self.fields['preco'].required = False
        if restaurante:
            self.fields['categoria'].queryset = Categoria.objects.filter(
                restaurante=restaurante, ativo=True
            )


class TipoSaborForm(forms.ModelForm):
    """Formulário para configurar tipo de sabor (categoria + adicional)."""

    class Meta:
        model = Categoria
        fields = ['nome', 'adicional_sabor', 'ordem', 'ativo']
        widgets = {
            'adicional_sabor': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
        }


TipoSaborFormSet = inlineformset_factory(
    parent_model=Restaurante,
    model=Categoria,
    form=TipoSaborForm,
    fields=['nome', 'adicional_sabor', 'ordem', 'ativo'],
    extra=1,
    can_delete=True
)
