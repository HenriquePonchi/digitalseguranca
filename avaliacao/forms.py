from django import forms
from .models import Instituicao


class InstituicaoForm(forms.ModelForm):
    class Meta:
        model = Instituicao
        fields = ['nome']
        widgets = {'nome': forms.TextInput(attrs={'class': 'form-control'})}


class QuestionarioForm(forms.Form):
    def __init__(self, *args, controles, respostas, **kwargs):
        super().__init__(*args, **kwargs)
        self.controles = controles
        for controle in controles:
            resposta = respostas.get(controle.pk)
            codigo = controle.codigo
            choices = [('', 'Ainda não respondido')]
            nomes = ('Inicial', 'Intermediário', 'Gerenciado', 'Otimizado')
            campos = ('nivel_1_inicial', 'nivel_2_intermediario', 'nivel_3_gerenciado', 'nivel_4_otimizado')
            choices.extend((str(n), f'{n} — {nomes[n-1]}: {getattr(controle, campos[n-1])}') for n in range(1, 5))
            choices.append(('NA', 'Não se aplica (justifique abaixo)'))
            initial = '' if not resposta else ('NA' if resposta.nao_se_aplica else str(resposta.nivel))
            self.fields[codigo] = forms.ChoiceField(label=f'{codigo} — {controle.pergunta}', choices=choices,
                required=False, initial=initial, help_text=f'{controle.codigo_csf} · Evidência sugerida: {controle.evidencia_sugerida}')
            self.fields[codigo + '_justificativa'] = forms.CharField(label=f'{codigo} — justificativa / observação',
                max_length=2000, required=False, widget=forms.Textarea(attrs={'rows': 2}),
                initial=resposta.justificativa if resposta else '')
            self.fields[codigo].widget.attrs.update({'class': 'form-select', 'style': 'max-width:100%'})
            self.fields[codigo + '_justificativa'].widget.attrs['class'] = 'form-control'

    def clean(self):
        cleaned = super().clean()
        for controle in self.controles:
            codigo = controle.codigo
            if cleaned.get(codigo) == 'NA' and not cleaned.get(codigo + '_justificativa', '').strip():
                self.add_error(codigo + '_justificativa', 'Justifique por que o controle não se aplica.')
        return cleaned
