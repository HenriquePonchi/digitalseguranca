"""Apresentação dos resultados imutáveis; não recalcula indicadores."""
from .models import FUNCOES, PerfilUsuario


def contexto_dashboard(usuario, avaliacao, dados):
    perfil = PerfilUsuario.objects.filter(usuario=usuario, instituicao_id=avaliacao.instituicao_id).values_list('perfil', flat=True).first() or 'Gestor'
    if perfil not in dict(PerfilUsuario.PERFIS):
        perfil = 'Gestor'
    entradas = dados['respostas']
    aplicaveis = [r for r in entradas if not r['nao_se_aplica']]
    por_codigo = {r['codigo']: r for r in entradas}
    funcoes = [{'codigo': c, 'nome': n, 'score': dados['scores_funcao'].get(c)} for c, n in FUNCOES]
    filtradas = {'Operacional': {'DE', 'RS'}, 'Conselheiro': {'GV'}}.get(perfil)
    recomendacoes = [r for r in dados['recomendacoes'] if filtradas is None or por_codigo[r['codigo']]['funcao'] in filtradas]
    if perfil == 'Gestor':
        recomendacoes = recomendacoes[:5]
    def grafico(tipo, titulo, linhas, percentual=False):
        return {'tipo': tipo, 'titulo': titulo, 'labels': [r[0] for r in linhas],
                'valores': [None if r[1] is None else float(r[1]) for r in linhas],
                'percentual': percentual}
    lista_graficos = []
    if perfil in ('Gestor', 'Técnico'):
        lista_graficos.append(grafico('radar' if perfil == 'Técnico' else 'bar', 'Maturidade por função NIST', [(f['codigo'] + ' · ' + f['nome'], f['score']) for f in funcoes]))
    if perfil == 'Gestor':
        lista_graficos.append(grafico('bar', 'Indicadores de risco e lacunas (%)', [('RSDM', dados['rsdm']['valor']), ('Lacunas LGPD', dados['gap_lgpd'])], True))
    if perfil == 'Operacional':
        lista_graficos.append(grafico('bar', 'Detectar e responder', [(f['codigo'] + ' · ' + f['nome'], f['score']) for f in funcoes if f['codigo'] in ('DE', 'RS')]))
    governanca = [r for r in aplicaveis if r['funcao'] == 'GV']
    distribuicao = [{'nivel': n, 'total': sum(r['nivel'] == n for r in governanca)} for n in range(1, 5)]
    if perfil == 'Conselheiro':
        lista_graficos.append({'tipo': 'bar', 'titulo': 'Controles de governança por nível', 'labels': ['Nível ' + str(d['nivel']) for d in distribuicao], 'valores': [d['total'] for d in distribuicao], 'contagem': True, 'sem_dados': not governanca})
    for g in lista_graficos:
        g['linhas'] = [{'indicador': label, 'valor': value} for label, value in zip(g['labels'], g['valores'])]
    subtitulos = {
        'Gestor': 'Visão executiva para priorizar melhorias e recursos.',
        'Técnico': 'Funções NIST, controles com lacunas e evidências do diagnóstico.',
        'Operacional': 'Detecção, resposta e ações sugeridas para a rotina.',
        'Conselheiro': 'Governança e decisões estratégicas apoiadas pelos controles GV.',
    }
    return {'perfil_dashboard': perfil, 'subtitulo_dashboard': subtitulos[perfil],
            'graficos_dashboard': lista_graficos, 'funcoes_dashboard': funcoes,
            'recomendacoes_dashboard': recomendacoes,
            'falhas_dashboard': [r for r in aplicaveis if r['nivel'] < 3],
            'governanca_dashboard': governanca, 'distribuicao_dashboard': distribuicao,
            'aplicaveis_dashboard': len(aplicaveis), 'na_dashboard': len(entradas) - len(aplicaveis)}
