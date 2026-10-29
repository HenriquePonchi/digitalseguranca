"""Modelo v0.1 experimental: funções puras; nenhum resultado é certificado legal."""
from decimal import Decimal, ROUND_HALF_UP

METODOLOGIA_VERSAO = 'v0.1-experimental'
FUNCOES = ('GV', 'ID', 'PR', 'DE', 'RS', 'RC')
PESOS = {'Dados de Menores': Decimal('1.5'), 'Dados Sensíveis': Decimal('1.3'),
         'Todos os Dados': Decimal('1.2'), 'Dados Acadêmicos': Decimal('1.0'),
         'Dados de Pesquisa': Decimal('1.0')}


def peso_controle(contexto, mandatorio=False):
    return PESOS[contexto] * (Decimal('1.5') if mandatorio else Decimal('1'))


def media_ponderada(itens):
    aplicaveis = [i for i in itens if not i['nao_se_aplica']]
    denominador = sum((Decimal(i['peso']) for i in aplicaveis), Decimal('0'))
    if not denominador:
        return None
    return sum((Decimal(i['peso']) * i['nivel'] for i in aplicaveis), Decimal('0')) / denominador


def score_funcao(itens, funcao):
    return media_ponderada([i for i in itens if i['funcao'] == funcao])


def score_geral(itens):
    return media_ponderada(itens)


def classificar(score):
    if score is None:
        return 'Sem dados aplicáveis'
    for limite, classe in [('1.75', 'Inicial'), ('2.50', 'Intermediário'), ('3.25', 'Gerenciado')]:
        if score < Decimal(limite):
            return classe
    return 'Otimizado'


def rsdm(itens):
    controles = [i for i in itens if i['rsdm']]
    media = media_ponderada(controles)
    if media is None:
        return {'valor': None, 'classe': 'Sem dados aplicáveis', 'piso_aplicado': False, 'motivo': ''}
    valor = (Decimal('4') - media) / Decimal('3') * Decimal('100')
    classe = 'Crítico'
    for limite, nome in [('25', 'Baixo'), ('50', 'Moderado'), ('75', 'Alto')]:
        if valor < Decimal(limite):
            classe = nome
            break
    gatilho = any(i['codigo'] == 'C04' and not i['nao_se_aplica'] and i['nivel'] == 1 for i in controles)
    piso = gatilho and classe in ('Baixo', 'Moderado')
    motivo = 'C04 nível 1: base legal não definida; classe mínima Alto (regra experimental).' if gatilho else ''
    return {'valor': valor, 'classe': 'Alto' if piso else classe, 'piso_aplicado': piso, 'motivo': motivo}


def gap_lgpd(itens):
    relevantes = [i for i in itens if 'LGPD' in i['base_legal'] and not i['nao_se_aplica']]
    total = sum((Decimal(i['peso']) for i in relevantes), Decimal('0'))
    if not total:
        return None
    lacunas = sum((Decimal(i['peso']) for i in relevantes if i['nivel'] < 3), Decimal('0'))
    return lacunas / total * Decimal('100')


def formatar(valor):
    return None if valor is None else str(valor.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))


def calcular(itens):
    """Dados JSON preservam entradas, contribuições e somas exatas como strings."""
    from .recomendacoes import recomendar
    for item in itens:
        if item['funcao'] not in FUNCOES or Decimal(item['peso']) <= 0:
            raise ValueError('Função ou peso inválido.')
        if item['nao_se_aplica']:
            if item['nivel'] is not None or not item['justificativa'].strip():
                raise ValueError('Não se aplica inválido.')
        elif type(item['nivel']) is not int or item['nivel'] not in (1, 2, 3, 4):
            raise ValueError('Nível inválido.')
    geral = score_geral(itens)
    risco = rsdm(itens)
    entradas = []
    for item in itens:
        row = dict(item)
        row['peso'] = str(Decimal(item['peso']))
        row['contribuicao'] = None if row['nao_se_aplica'] else str(Decimal(item['peso']) * item['nivel'])
        entradas.append(row)
    aplicaveis = [i for i in entradas if not i['nao_se_aplica']]
    return {
        'score_geral': formatar(geral), 'classe': classificar(geral),
        'scores_funcao': {f: formatar(score_funcao(itens, f)) for f in FUNCOES},
        'rsdm': {**risco, 'valor': formatar(risco['valor'])},
        'gap_lgpd': formatar(gap_lgpd(itens)),
        'prontidao_resposta': formatar(media_ponderada([i for i in itens if i['funcao'] in ('DE', 'RS')])),
        'numerador': str(sum((Decimal(i['contribuicao']) for i in aplicaveis), Decimal('0'))),
        'denominador': str(sum((Decimal(i['peso']) for i in aplicaveis), Decimal('0'))),
        'respostas': entradas, 'recomendacoes': recomendar(itens),
        'metodologia_versao': METODOLOGIA_VERSAO,
    }
