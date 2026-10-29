from decimal import Decimal
from django.test import SimpleTestCase
from avaliacao.scoring import (calcular, classificar, score_geral, score_funcao, rsdm,
                               gap_lgpd, peso_controle, formatar)
from avaliacao.recomendacoes import recomendar


def item(codigo='C01', nivel=2, peso='1.2', funcao='GV', **extra):
    return {'codigo': codigo, 'nivel': nivel, 'peso': peso, 'funcao': funcao,
            'nao_se_aplica': False, 'justificativa': '', 'rsdm': False,
            'mandatorio': False, 'base_legal': 'LGPD Art. 46',
            'recomendacao': 'Ação de teste', **extra}


class ScoringTests(SimpleTestCase):
    def test_contexto_e_mandatorio(self):
        self.assertEqual(peso_controle('Todos os Dados', True), Decimal('1.80'))
        self.assertEqual(peso_controle('Dados de Menores'), Decimal('1.5'))

    def test_media_ponderada_nao_e_media_das_funcoes(self):
        entradas = [item(nivel=1, peso='3'), item('C02', nivel=4, peso='1', funcao='ID')]
        self.assertEqual(score_geral(entradas), Decimal('1.75'))
        self.assertEqual(score_funcao(entradas, 'ID'), Decimal('4'))
        self.assertIsNone(score_funcao(entradas, 'RC'))

    def test_exclusao_na_e_vazio(self):
        entradas = [item(nivel=4), item('C02', nivel=None, nao_se_aplica=True, justificativa='Sem rede')]
        self.assertEqual(score_geral(entradas), Decimal('4'))
        self.assertIsNone(score_geral(entradas[1:]))
        self.assertEqual(calcular(entradas[1:])['classe'], 'Sem dados aplicáveis')
        self.assertIsNone(calcular([])['rsdm']['valor'])

    def test_extremos(self):
        for nivel, risco in [(1, Decimal('100')), (4, Decimal('0'))]:
            entradas = [item(nivel=nivel, rsdm=True)]
            self.assertEqual(score_geral(entradas), Decimal(nivel))
            self.assertEqual(rsdm(entradas)['valor'], risco)

    def test_limites_maturidade(self):
        for numero, classe in [('1.7499', 'Inicial'), ('1.75', 'Intermediário'),
                              ('2.4999', 'Intermediário'), ('2.50', 'Gerenciado'),
                              ('3.2499', 'Gerenciado'), ('3.25', 'Otimizado')]:
            with self.subTest(numero=numero):
                self.assertEqual(classificar(Decimal(numero)), classe)
        self.assertEqual(formatar(Decimal('1.7499')), '1.75')
        self.assertEqual(classificar(Decimal('1.7499')), 'Inicial')

    def test_limites_rsdm(self):
        # Com níveis 1 e 4, o peso do nível 1 determina o risco percentual.
        for valor, classe in [('24.999', 'Baixo'), ('25', 'Moderado'), ('49.999', 'Moderado'),
                             ('50', 'Alto'), ('74.999', 'Alto'), ('75', 'Crítico')]:
            entradas = [item('C03', nivel=1, peso=valor, rsdm=True),
                        item('C06', nivel=4, peso=str(Decimal('100') - Decimal(valor)), rsdm=True)]
            self.assertEqual(rsdm(entradas)['classe'], classe)

    def test_piso_nao_altera_numero(self):
        entradas = [item('C04', nivel=1, rsdm=True, peso='1'), item('C06', nivel=4, rsdm=True, peso='99')]
        risco = rsdm(entradas)
        self.assertEqual(risco['valor'], Decimal('1'))
        self.assertEqual(risco['classe'], 'Alto')
        self.assertTrue(risco['piso_aplicado'])
        entradas[0].update(nivel=None, nao_se_aplica=True, justificativa='Outra hipótese aplicável')
        self.assertEqual(rsdm(entradas)['classe'], 'Baixo')
        self.assertFalse(rsdm(entradas)['piso_aplicado'])

    def test_gap_percentual(self):
        entradas = [item(nivel=2, peso='3'), item('C02', nivel=3, peso='1'),
                    item('C03', nivel=1, peso='9', base_legal='—')]
        self.assertEqual(gap_lgpd(entradas), Decimal('75'))
        self.assertIsNone(gap_lgpd([entradas[2]]))

    def test_recomendacoes_desempate(self):
        entradas = [item('C03'), item('C02', rsdm=True), item('C01', mandatorio=True), item('C04', nivel=4)]
        self.assertEqual([r['codigo'] for r in recomendar(entradas)], ['C01', 'C02', 'C03'])

    def test_validacao_e_reprodutibilidade(self):
        entradas = [item()]
        self.assertEqual(calcular(entradas), calcular(entradas))
        for invalido in [item(nivel=0), item(nivel=True), item(peso='-1'),
                         item(nivel=None, nao_se_aplica=True)]:
            with self.assertRaises(ValueError):
                calcular([invalido])
