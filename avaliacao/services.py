from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from .models import Avaliacao, Resultado
from .scoring import calcular, METODOLOGIA_VERSAO


@transaction.atomic
def finalizar(avaliacao_id):
    avaliacao = Avaliacao.objects.select_for_update().select_related('matriz').get(pk=avaliacao_id)
    if avaliacao.finalizada_em:
        return avaliacao.resultado
    if avaliacao.metodologia_versao != METODOLOGIA_VERSAO:
        raise ValidationError('Versão de metodologia não suportada neste código.')
    respostas = list(avaliacao.respostas.select_related('controle').order_by('controle__codigo'))
    esperados = set(avaliacao.matriz.controles.values_list('pk', flat=True))
    if not esperados or {r.controle_id for r in respostas} != esperados:
        raise ValidationError('Responda todos os controles antes de finalizar.')
    itens = []
    for resposta in respostas:
        resposta.full_clean()
        controle = resposta.controle
        itens.append({
            'resposta_id': resposta.pk, 'controle_id': controle.pk,
            'codigo': controle.codigo, 'funcao': controle.funcao, 'codigo_csf': controle.codigo_csf,
            'controle': controle.controle, 'pergunta': controle.pergunta,
            'nivel': resposta.nivel, 'nao_se_aplica': resposta.nao_se_aplica,
            'justificativa': resposta.justificativa,
            'peso': str(controle.peso), 'contexto': controle.contexto,
            'mandatorio': controle.mandatorio, 'rsdm': controle.rsdm,
            'base_legal': controle.base_legal, 'recomendacao': controle.recomendacao,
        })
    dados = calcular(itens)
    dados['matriz_versao'] = avaliacao.matriz.versao
    dados['matriz_sha256'] = avaliacao.matriz.sha256
    resultado = Resultado.objects.create(avaliacao=avaliacao, dados=dados)
    avaliacao.finalizada_em = timezone.now()
    avaliacao.save(update_fields=['finalizada_em'])
    return resultado
