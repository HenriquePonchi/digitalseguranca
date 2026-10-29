import copy
import io
from unittest.mock import patch
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.urls import reverse
from avaliacao.dashboards import contexto_dashboard
from avaliacao.models import PerfilUsuario, Resposta, Avaliacao
from avaliacao.services import finalizar
from .test_fluxo import BaseTests


class DashboardTests(BaseTests):
    def setUp(self):
        self.avaliacao = self.avaliacao_completa()
        self.resultado = finalizar(self.avaliacao.pk)
        self.url = reverse('resultado', args=[self.avaliacao.pk])
        self.client.force_login(self.user)

    def test_quatro_perfis_e_conteudo_especifico(self):
        for perfil, titulo in [('Gestor', 'Cinco prioridades para decisão'), ('Técnico', 'Controles com lacunas'), ('Operacional', 'Ações sugeridas'), ('Conselheiro', 'Prioridades de governança')]:
            with self.subTest(perfil=perfil):
                PerfilUsuario.objects.update_or_create(usuario=self.user, defaults={'instituicao': self.escola, 'perfil': perfil})
                response = self.client.get(self.url)
                self.assertContains(response, 'Dashboard ' + perfil)
                self.assertContains(response, titulo)
                self.assertContains(response, 'Rastreabilidade')
                self.assertContains(response, 'chart.umd.min.js')
                dados = response.context['graficos_dashboard']
                self.assertEqual(dados[0]['tipo'], 'radar' if perfil == 'Técnico' else 'bar')
                self.assertEqual(len(response.context['recomendacoes_dashboard']), 5 if perfil == 'Gestor' else 8 if perfil == 'Operacional' else 7 if perfil == 'Conselheiro' else 31)
                codigos = {r['codigo'] for r in response.context['recomendacoes_dashboard']}
                funcoes = {r['funcao'] for r in self.resultado.dados['respostas'] if r['codigo'] in codigos}
                if perfil in ('Operacional', 'Conselheiro'):
                    self.assertEqual(funcoes, {'DE', 'RS'} if perfil == 'Operacional' else {'GV'})

    def test_responsavel_sem_perfil_recebe_gestor(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'Dashboard Gestor')
        self.assertEqual(response.context['graficos_dashboard'][0]['valores'], [2.0] * 6)

    def test_grupo_nao_concede_acesso_institucional(self):
        self.outro.groups.add(Group.objects.create(name='Técnico'))
        self.client.force_login(self.outro)
        self.assertEqual(self.client.get(self.url).status_code, 404)
        PerfilUsuario.objects.create(usuario=self.outro, instituicao=self.escola, perfil='Técnico')
        self.assertContains(self.client.get(self.url), 'Dashboard Técnico')

    def test_anonimo_e_rascunho(self):
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code, 302)
        self.client.force_login(self.user)
        rascunho = Avaliacao.objects.create(instituicao=self.escola, matriz=self.matriz)
        response = self.client.get(reverse('resultado', args=[rascunho.pk]))
        self.assertRedirects(response, reverse('questionario', args=[rascunho.pk, 'GV']))

    def test_snapshot_preservado_sem_recalcular(self):
        antes = copy.deepcopy(self.resultado.dados)
        with patch('avaliacao.scoring.calcular', side_effect=AssertionError('Não recalcular')):
            response = self.client.get(self.url)
        self.assertEqual(response.context['dados'], antes)
        self.resultado.refresh_from_db()
        self.assertEqual(self.resultado.dados, antes)
        chart = response.context['graficos_dashboard'][0]
        self.assertEqual(chart['valores'], [float(antes['scores_funcao'][f]) for f in ('GV', 'ID', 'PR', 'DE', 'RS', 'RC')])

    def test_sem_aplicaveis_em_todos_os_perfis(self):
        avaliacao = Avaliacao.objects.create(instituicao=self.escola, matriz=self.matriz)
        for controle in self.matriz.controles.all():
            Resposta.objects.create(avaliacao=avaliacao, controle=controle, nao_se_aplica=True, justificativa='Dados sintéticos não aplicáveis')
        result = finalizar(avaliacao.pk)
        for perfil in ('Gestor', 'Técnico', 'Operacional', 'Conselheiro'):
            PerfilUsuario.objects.update_or_create(usuario=self.user, defaults={'instituicao': self.escola, 'perfil': perfil})
            response = self.client.get(reverse('resultado', args=[avaliacao.pk]))
            self.assertContains(response, 'Sem dados aplicáveis')
            self.assertFalse(response.context['recomendacoes_dashboard'])
            for g in response.context['graficos_dashboard']:
                if perfil == 'Conselheiro': self.assertTrue(g['sem_dados'])
                else: self.assertTrue(all(v is None for v in g['valores']))
        self.assertIsNone(result.dados['score_geral'])

    def test_funcao_parcialmente_na_nao_virar_zero(self):
        dados = copy.deepcopy(self.resultado.dados)
        dados['scores_funcao']['GV'] = None
        ctx = contexto_dashboard(self.user, self.avaliacao, dados)
        self.assertIsNone(ctx['graficos_dashboard'][0]['valores'][0])
        self.assertEqual(ctx['graficos_dashboard'][0]['valores'][1], 2.0)

    def test_json_seguro_e_recomendacoes_escapadas(self):
        self.escola.nome = '</script><script>alert("x")</script>'
        self.escola.save()
        response = self.client.get(self.url)
        self.assertContains(response, '&lt;/script&gt;')
        self.assertNotContains(response, '<script>alert("x")</script>')
        self.assertContains(response, 'id="dashboard-dados" type="application/json"')

    @patch.dict('os.environ', {'TCC_DEMO_PASSWORD': 'senha-sintetica-teste-2026'})
    def test_alpha_no_dashboard(self):
        call_command('seed_alpha', versao='v0.1', stdout=io.StringIO())
        perfil = PerfilUsuario.objects.get(usuario__username='alpha_gestor')
        self.client.force_login(perfil.usuario)
        response = self.client.get(reverse('resultado', args=[perfil.instituicao.avaliacoes.get().pk]))
        self.assertEqual(response.context['dados']['score_geral'], '2.25')
        self.assertEqual(response.context['dados']['rsdm']['valor'], '59.26')
        self.assertEqual(response.context['graficos_dashboard'][1]['valores'], [59.26, 54.55])
