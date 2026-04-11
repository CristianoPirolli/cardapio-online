from django import forms
from django.core.exceptions import ValidationError

from .models import ChavePix, PagamentoRevisaoHistorico


class ChavePixForm(forms.ModelForm):
    class Meta:
        model = ChavePix
        fields = ['tipo', 'valor', 'ativo', 'padrao', 'prioridade']
        widgets = {
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'valor': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Informe a chave PIX'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'padrao': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'prioridade': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
        }

    def __init__(self, *args, restaurante=None, **kwargs):
        self.restaurante = restaurante
        super().__init__(*args, **kwargs)
        self.fields['prioridade'].required = True

    def clean(self):
        cleaned_data = super().clean()
        tipo = cleaned_data.get('tipo')
        valor = cleaned_data.get('valor')
        ativo = bool(cleaned_data.get('ativo'))
        padrao = bool(cleaned_data.get('padrao'))
        prioridade = cleaned_data.get('prioridade')

        if not self.restaurante:
            raise forms.ValidationError('Restaurante invalido para cadastro de chave PIX.')

        if padrao and not ativo:
            self.add_error('padrao', 'A chave padrao precisa estar ativa.')

        instance = self.instance if self.instance and self.instance.pk else ChavePix(restaurante=self.restaurante)
        instance.restaurante = self.restaurante
        instance.tipo = tipo
        instance.valor = valor
        instance.ativo = ativo
        instance.padrao = padrao
        instance.prioridade = prioridade

        try:
            instance.full_clean(exclude=['restaurante'])
        except ValidationError as exc:
            for field, errors in exc.message_dict.items():
                if field == '__all__':
                    self.add_error(None, errors)
                    continue
                for error in errors:
                    self.add_error(field, error)

        if ativo and prioridade is not None:
            qs = ChavePix.objects.filter(
                restaurante=self.restaurante,
                ativo=True,
                prioridade=prioridade,
            )
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                self.add_error('prioridade', 'Ja existe uma chave ativa com essa prioridade.')

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.restaurante = self.restaurante
        if commit:
            instance.save()
        return instance


class RevisaoManualForm(forms.Form):
    motivo_revisao = forms.ChoiceField(
        choices=PagamentoRevisaoHistorico.Motivo.choices,
        required=True,
    )
    justificativa_revisao = forms.CharField(
        required=True,
        min_length=10,
        strip=True,
        widget=forms.Textarea,
    )

    def clean_justificativa_revisao(self):
        justificativa = (self.cleaned_data.get('justificativa_revisao') or '').strip()
        if len(justificativa) < 10:
            raise forms.ValidationError('Informe uma justificativa com no minimo 10 caracteres.')
        return justificativa
