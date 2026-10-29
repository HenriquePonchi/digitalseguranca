from decimal import Decimal
from .scoring import formatar


def recomendar(itens):
    candidatos = [i for i in itens if not i['nao_se_aplica'] and i['nivel'] < 4]
    candidatos.sort(key=lambda i: (-(4 - i['nivel']) * Decimal(i['peso']),
                                    not i['mandatorio'], not i['rsdm'], i['codigo']))
    return [{'codigo': i['codigo'], 'resposta_id': i.get('resposta_id'),
             'controle_id': i.get('controle_id'), 'recomendacao': i['recomendacao'],
             'prioridade': formatar((4 - i['nivel']) * Decimal(i['peso']))} for i in candidatos]
