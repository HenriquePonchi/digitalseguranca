from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models

FUNCOES = [('GV', 'Governar'), ('ID', 'Identificar'), ('PR', 'Proteger'),
           ('DE', 'Detectar'), ('RS', 'Responder'), ('RC', 'Recuperar')]
CONTEXTOS = ['Dados de Menores', 'Dados Sensíveis', 'Todos os Dados',
             'Dados Acadêmicos', 'Dados de Pesquisa']


class Instituicao(models.Model):
    nome = models.CharField(max_length=180)
    responsavel = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['nome', 'pk']

    def __str__(self):
        return self.nome


class Matriz(models.Model):
    versao = models.CharField(max_length=50, unique=True)
    sha256 = models.CharField(max_length=64)
    importada_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.versao

    def save(self, *args, **kwargs):
        if self.pk:
            original = type(self).objects.get(pk=self.pk)
            if self.versao != original.versao or self.sha256 != original.sha256:
                raise ValidationError('Versões importadas são imutáveis. Importe uma nova versão.')
        super().save(*args, **kwargs)


class Controle(models.Model):
    matriz = models.ForeignKey(Matriz, related_name='controles', on_delete=models.PROTECT)
    codigo = models.CharField(max_length=12)
    funcao = models.CharField(max_length=2, choices=FUNCOES)
    codigo_csf = models.CharField(max_length=20)
    controle = models.CharField(max_length=200)
    pergunta = models.TextField()
    categoria = models.CharField(max_length=30)
    tipo_funcional = models.CharField(max_length=30)
    contexto = models.CharField(max_length=30, choices=[(x, x) for x in CONTEXTOS])
    base_legal = models.TextField()
    mandatorio = models.BooleanField(default=False)
    rsdm = models.BooleanField(default=False)
    nivel_1_inicial = models.TextField()
    nivel_2_intermediario = models.TextField()
    nivel_3_gerenciado = models.TextField()
    nivel_4_otimizado = models.TextField()
    evidencia_sugerida = models.TextField()
    recomendacao = models.TextField()
    peso = models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])

    class Meta:
        ordering = ['codigo']
        constraints = [models.UniqueConstraint(fields=['matriz', 'codigo'], name='controle_unico_por_matriz')]

    def __str__(self):
        return f'{self.matriz} / {self.codigo} — {self.controle}'

    def save(self, *args, **kwargs):
        if self.pk:
            original = type(self).objects.get(pk=self.pk)
            if any(getattr(self, f.attname) != getattr(original, f.attname)
                   for f in self._meta.concrete_fields if f.name != 'id'):
                raise ValidationError('Controle importado é imutável. Use nova versão da matriz.')
        elif self.matriz_id and self.matriz.avaliacoes.exists():
            raise ValidationError('Não acrescente controles a uma matriz já usada.')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError('Controle importado é imutável.')


class Avaliacao(models.Model):
    instituicao = models.ForeignKey(Instituicao, related_name='avaliacoes', on_delete=models.PROTECT)
    matriz = models.ForeignKey(Matriz, related_name='avaliacoes', on_delete=models.PROTECT)
    metodologia_versao = models.CharField(max_length=50, default='v0.1-experimental')
    criada_em = models.DateTimeField(auto_now_add=True)
    finalizada_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-criada_em']

    def __str__(self):
        return f'{self.instituicao} / avaliação {self.pk}'

    def save(self, *args, **kwargs):
        if self.pk:
            original = type(self).objects.get(pk=self.pk)
            if (self.matriz_id, self.instituicao_id, self.metodologia_versao) != (
                    original.matriz_id, original.instituicao_id, original.metodologia_versao):
                raise ValidationError('Instituição e versões da avaliação são fixas.')
            if original.finalizada_em:
                raise ValidationError('Avaliação finalizada é imutável.')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.finalizada_em:
            raise ValidationError('Avaliação finalizada é imutável.')
        super().delete(*args, **kwargs)


class Resposta(models.Model):
    avaliacao = models.ForeignKey(Avaliacao, related_name='respostas', on_delete=models.PROTECT)
    controle = models.ForeignKey(Controle, on_delete=models.PROTECT)
    nivel = models.PositiveSmallIntegerField(null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(4)])
    nao_se_aplica = models.BooleanField(default=False)
    justificativa = models.TextField(blank=True, max_length=2000)
    atualizada_em = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['avaliacao', 'controle'], name='resposta_unica'),
            models.CheckConstraint(condition=(models.Q(nao_se_aplica=True, nivel__isnull=True) |
                models.Q(nao_se_aplica=False, nivel__gte=1, nivel__lte=4, nivel__isnull=False)), name='resposta_nivel_ou_na'),
        ]

    def clean(self):
        super().clean()
        if self.avaliacao_id:
            evaluation = Avaliacao.objects.get(pk=self.avaliacao_id)
            if evaluation.finalizada_em:
                raise ValidationError('Avaliação finalizada é imutável.')
            if self.controle_id and self.controle.matriz_id != evaluation.matriz_id:
                raise ValidationError('Controle não pertence à versão desta avaliação.')
        if self.nao_se_aplica:
            if self.nivel is not None or not self.justificativa.strip():
                raise ValidationError('Não se aplica exige justificativa e nível vazio.')
        elif self.nivel not in (1, 2, 3, 4):
            raise ValidationError('Selecione nível 1 a 4 ou não se aplica.')

    def save(self, *args, **kwargs):
        if self.pk:
            original = type(self).objects.get(pk=self.pk)
            if (self.avaliacao_id, self.controle_id) != (original.avaliacao_id, original.controle_id):
                raise ValidationError('A resposta não pode ser transferida.')
        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if Avaliacao.objects.get(pk=self.avaliacao_id).finalizada_em:
            raise ValidationError('Avaliação finalizada é imutável.')
        super().delete(*args, **kwargs)


class Resultado(models.Model):
    avaliacao = models.OneToOneField(Avaliacao, related_name='resultado', on_delete=models.PROTECT)
    dados = models.JSONField()
    criado_em = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError('Resultado finalizado é imutável.')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError('Resultado finalizado é imutável.')


class PerfilUsuario(models.Model):
    PERFIS = [(p, p) for p in ('Gestor', 'Técnico', 'Operacional', 'Conselheiro')]
    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    instituicao = models.ForeignKey(Instituicao, on_delete=models.PROTECT)
    perfil = models.CharField(max_length=20, choices=PERFIS, default='Gestor')

    def __str__(self):
        return f'{self.usuario} / {self.instituicao} / {self.perfil}'
