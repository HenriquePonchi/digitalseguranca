"""Auxiliares de apresentação. Somente leitura: não calculam pontuação nem gravam dados."""
from django import template
from django.db.models import Count

from ..models import FUNCOES

register = template.Library()

NOMES_NIVEL = ('Inicial', 'Intermediário', 'Gerenciado', 'Otimizado')


@register.filter
def pct(valor, faixa='0,4'):
    """Converte um valor (str/Decimal/float) em porcentagem 0–100 dentro de 'mín,máx'. Nulo vira 0."""
    try:
        minimo, maximo = (float(x) for x in faixa.split(','))
        posicao = (float(valor) - minimo) / (maximo - minimo) * 100
    except (TypeError, ValueError, ZeroDivisionError):
        return '0'
    return f'{max(0.0, min(100.0, posicao)):.2f}'


@register.filter
def campo(form, nome):
    """Acessa um BoundField por nome dinâmico (códigos de controle como C01)."""
    return form[nome]


@register.filter
def niveis(controle):
    """Os quatro critérios de maturidade de um controle, na ordem 1–4."""
    textos = (controle.nivel_1_inicial, controle.nivel_2_intermediario,
              controle.nivel_3_gerenciado, controle.nivel_4_otimizado)
    return [{'valor': str(n), 'nome': NOMES_NIVEL[n - 1], 'criterio': textos[n - 1]} for n in range(1, 5)]


@register.filter
def como_texto(valor):
    return '' if valor is None else str(valor)


@register.simple_tag
def progresso(avaliacao):
    """Progresso salvo por função e geral (contagens de respostas já gravadas)."""
    totais = dict(avaliacao.matriz.controles.values_list('funcao').annotate(n=Count('pk')))
    feitos = dict(avaliacao.respostas.values_list('controle__funcao').annotate(n=Count('pk')))
    etapas = []
    for codigo, nome in FUNCOES:
        total, feito = totais.get(codigo, 0), feitos.get(codigo, 0)
        etapas.append({'codigo': codigo, 'nome': nome, 'total': total, 'feitos': feito,
                       'completa': bool(total) and feito >= total,
                       'percentual': f'{feito / total * 100:.1f}' if total else '0.0'})
    total, feito = sum(totais.values()), sum(feitos.values())
    return {'etapas': etapas, 'total': total, 'feitos': feito, 'faltam': max(total - feito, 0),
            'percentual': f'{feito / total * 100:.1f}' if total else '0.0'}


@register.simple_tag
def resumo_avaliacoes(avaliacoes):
    lista = list(avaliacoes)
    finalizadas = sum(1 for a in lista if a.finalizada_em)
    return {'total': len(lista), 'finalizadas': finalizadas, 'andamento': len(lista) - finalizadas}


@register.filter
def tom_risco(classe):
    """Classe textual do RSDM → tom visual. O texto da classe sempre acompanha a cor."""
    return {'Baixo': 'ok', 'Moderado': 'warn', 'Alto': 'danger', 'Crítico': 'danger'}.get(classe, 'neutral')
