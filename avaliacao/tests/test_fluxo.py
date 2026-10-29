import csv
import io
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import Client, TestCase
from django.urls import reverse
from avaliacao.models import Instituicao, Matriz, Controle, Avaliacao, Resposta, Resultado, PerfilUsuario
from avaliacao.services import finalizar

CSV = Path(settings.BASE_DIR) / 'docs' / 'MATRIZ_CONTROLES_v0.csv'


class BaseTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('importar_matriz', CSV, versao='v0.1', stdout=io.StringIO())
        cls.matriz = Matriz.objects.get()
        cls.user = User.objects.create_user('professor', password='senha-de-teste-somente')
        cls.outro = User.objects.create_user('outro', password='senha-de-teste-somente')
        cls.escola = Instituicao.objects.create(nome='Escola teste', responsavel=cls.user)

    def avaliacao_completa(self):
        avaliacao = Avaliacao.objects.create(instituicao=self.escola, matriz=self.matriz)
        for controle in self.matriz.controles.all():
            Resposta.objects.create(avaliacao=avaliacao, controle=controle, nivel=2)
        return avaliacao

    def csv_alterado(self, callback):
        rows = list(csv.DictReader(CSV.open(encoding='utf-8')))
        callback(rows)
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / 'matriz.csv'
        with path.open('w', encoding='utf-8', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        return path


class ImportacaoTests(BaseTests):
    def test_idempotencia(self):
        call_command('importar_matriz', CSV, versao='v0.1', stdout=io.StringIO())
        self.assertEqual(Controle.objects.count(), 31)
        self.assertEqual(Matriz.objects.count(), 1)

    def test_arquivo_invalido_sem_carga_parcial(self):
        for campo, valor in [('id', 'C01'), ('peso', '99'), ('nivel_3_gerenciado', ''), ('codigo_csf', 'PR.AA-03')]:
            with self.subTest(campo=campo):
                path = self.csv_alterado(lambda rows: rows[-1].update({campo: valor}))
                with self.assertRaises(CommandError):
                    call_command('importar_matriz', path, versao='v1', stdout=io.StringIO())
                self.assertFalse(Matriz.objects.filter(versao='v1').exists())
                self.assertEqual(Controle.objects.count(), 31)

    def test_conflito_versao_e_preservacao_resultado(self):
        avaliacao = self.avaliacao_completa()
        result = finalizar(avaliacao.pk)
        antes = json.dumps(result.dados, sort_keys=True)
        path = self.csv_alterado(lambda rows: rows[0].update(pergunta='Pergunta revisada'))
        with self.assertRaises(CommandError):
            call_command('importar_matriz', path, versao='v0.1', stdout=io.StringIO())
        call_command('importar_matriz', path, versao='v1', stdout=io.StringIO())
        result.refresh_from_db()
        self.assertEqual(json.dumps(result.dados, sort_keys=True), antes)
        self.assertEqual(result.dados['matriz_versao'], 'v0.1')

    def test_controle_e_matriz_imutaveis(self):
        controle = self.matriz.controles.first()
        controle.pergunta = 'Mudança'
        with self.assertRaises(ValidationError):
            controle.save()
        self.matriz.sha256 = '0' * 64
        with self.assertRaises(ValidationError):
            self.matriz.save()


class FluxoTests(BaseTests):
    def setUp(self):
        self.client.force_login(self.user)

    def test_fluxo_completo_pela_interface(self):
        response = self.client.post(reverse('nova_instituicao'), {'nome': 'Escola interface'})
        self.assertEqual(response.status_code, 302)
        escola = Instituicao.objects.get(nome='Escola interface')
        self.assertEqual(escola.responsavel, self.user)
        self.client.post(reverse('nova_avaliacao', args=[escola.pk]))
        avaliacao = escola.avaliacoes.get()
        for funcao in ['GV', 'ID', 'PR', 'DE', 'RS', 'RC']:
            controles = self.matriz.controles.filter(funcao=funcao)
            payload = {c.codigo: '3' for c in controles}
            response = self.client.post(reverse('questionario', args=[avaliacao.pk, funcao]), payload)
            self.assertEqual(response.status_code, 302)
        self.assertEqual(avaliacao.respostas.count(), 31)
        response = self.client.post(reverse('finalizar', args=[avaliacao.pk]), follow=True)
        self.assertContains(response, 'Rastreabilidade')
        self.assertContains(response, '3.00')
        self.assertEqual(avaliacao.resultado.dados['score_geral'], '3.00')
        self.assertEqual(len(avaliacao.resultado.dados['respostas']), 31)
        self.assertContains(response, 'Beta experimental')

    def test_retomada_e_incompleto(self):
        avaliacao = Avaliacao.objects.create(instituicao=self.escola, matriz=self.matriz)
        url = reverse('questionario', args=[avaliacao.pk, 'GV'])
        self.client.post(url, {'C01': '2'})
        self.assertContains(self.client.get(url), 'value="2" checked')
        response = self.client.post(reverse('finalizar', args=[avaliacao.pk]), follow=True)
        self.assertContains(response, 'Responda todos os controles')
        self.assertFalse(Resultado.objects.filter(avaliacao=avaliacao).exists())

    def test_na_exige_justificativa_e_nao_salva_parcialmente(self):
        avaliacao = Avaliacao.objects.create(instituicao=self.escola, matriz=self.matriz)
        url = reverse('questionario', args=[avaliacao.pk, 'GV'])
        response = self.client.post(url, {'C01': '2', 'C02': 'NA'})
        self.assertContains(response, 'Justifique')
        self.assertEqual(avaliacao.respostas.count(), 0)
        self.client.post(url, {'C02': 'NA', 'C02_justificativa': 'Justificativa de teste'})
        self.assertTrue(avaliacao.respostas.get().nao_se_aplica)

    def test_valor_forjado_e_versao_errada(self):
        avaliacao = Avaliacao.objects.create(instituicao=self.escola, matriz=self.matriz)
        response = self.client.post(reverse('questionario', args=[avaliacao.pk, 'GV']), {'C01': '99'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(avaliacao.respostas.count(), 0)
        call_command('importar_matriz', CSV, versao='v1', stdout=io.StringIO())
        controle = Controle.objects.filter(matriz__versao='v1').first()
        with self.assertRaises(ValidationError):
            Resposta.objects.create(avaliacao=avaliacao, controle=controle, nivel=2)

    def test_avaliacao_finalizada_e_respostas_imutaveis(self):
        avaliacao = self.avaliacao_completa()
        result = finalizar(avaliacao.pk)
        self.assertEqual(finalizar(avaliacao.pk).pk, result.pk)
        resposta = avaliacao.respostas.first()
        resposta.nivel = 4
        with self.assertRaises(ValidationError):
            resposta.save()
        with self.assertRaises(ValidationError):
            resposta.delete()
        avaliacao.refresh_from_db()
        avaliacao.finalizada_em = None
        with self.assertRaises(ValidationError):
            avaliacao.save()
        result.dados = {}
        with self.assertRaises(ValidationError):
            result.save()

    def test_isolamento_institucional_inclusive_superusuario(self):
        avaliacao = self.avaliacao_completa()
        finalizar(avaliacao.pk)
        self.outro.is_superuser = True
        self.outro.save()
        self.client.force_login(self.outro)
        self.assertNotContains(self.client.get(reverse('inicio')), self.escola.nome)
        for route, args in [('questionario', [avaliacao.pk, 'GV']), ('resultado', [avaliacao.pk])]:
            self.assertEqual(self.client.get(reverse(route, args=args)).status_code, 404)
        self.assertEqual(self.client.post(reverse('finalizar', args=[avaliacao.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse('nova_avaliacao', args=[self.escola.pk])).status_code, 404)

    def test_perfil_vinculado_tem_acesso(self):
        avaliacao = self.avaliacao_completa()
        PerfilUsuario.objects.create(usuario=self.outro, instituicao=self.escola, perfil='Técnico')
        self.client.force_login(self.outro)
        self.assertEqual(self.client.get(reverse('questionario', args=[avaliacao.pk, 'GV'])).status_code, 200)

    def test_csrf_login_metodos_e_escape(self):
        avaliacao = Avaliacao.objects.create(instituicao=self.escola, matriz=self.matriz)
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.get(reverse('inicio')).status_code, 302)
        client.force_login(self.user)
        self.assertEqual(client.post(reverse('finalizar', args=[avaliacao.pk])).status_code, 403)
        self.assertEqual(self.client.get(reverse('finalizar', args=[avaliacao.pk])).status_code, 405)
        self.escola.nome = '<script>alert(1)</script>'
        self.escola.save()
        self.assertContains(self.client.get(reverse('inicio')), '&lt;script&gt;')

    def test_todos_na_sem_dados(self):
        avaliacao = Avaliacao.objects.create(instituicao=self.escola, matriz=self.matriz)
        for controle in self.matriz.controles.all():
            Resposta.objects.create(avaliacao=avaliacao, controle=controle, nao_se_aplica=True,
                                    justificativa='Teste de denominador vazio')
        result = finalizar(avaliacao.pk)
        self.assertIsNone(result.dados['score_geral'])
        self.assertIsNone(result.dados['gap_lgpd'])
        self.assertContains(self.client.get(reverse('resultado', args=[avaliacao.pk])), 'Sem dados aplicáveis')


class AlphaTests(BaseTests):
    @patch.dict(os.environ, {'TCC_DEMO_PASSWORD': 'senha-sintetica-teste-2026'})
    def test_alpha_sintetica_reprodutivel_e_idempotente(self):
        call_command('seed_alpha', versao='v0.1', stdout=io.StringIO())
        resultado = Resultado.objects.get()
        self.assertEqual(resultado.dados['rsdm']['classe'], 'Alto')
        self.assertEqual(resultado.dados['score_geral'], '2.25')
        self.assertEqual(resultado.dados['rsdm']['valor'], '59.26')
        self.assertEqual(resultado.dados['gap_lgpd'], '54.55')
        self.assertTrue(all('sintética' in r['justificativa'] for r in resultado.dados['respostas']))
        call_command('seed_alpha', versao='v0.1', stdout=io.StringIO())
        self.assertEqual(Resultado.objects.count(), 1)
        self.assertEqual(PerfilUsuario.objects.count(), 4)
        for perfil in PerfilUsuario.objects.all():
            self.client.force_login(perfil.usuario)
            self.assertEqual(self.client.get(reverse('resultado', args=[resultado.avaliacao_id])).status_code, 200)
