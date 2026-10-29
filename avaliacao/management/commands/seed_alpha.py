import os
from django.contrib.auth.models import User, Group
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from avaliacao.models import Instituicao, Matriz, Avaliacao, Resposta, PerfilUsuario
from avaliacao.services import finalizar


class Command(BaseCommand):
    help = 'Cria Escola Alpha sintética e quatro usuários; exige TCC_DEMO_PASSWORD no ambiente.'

    def add_arguments(self, parser):
        parser.add_argument('--versao', default='v0.1')

    @transaction.atomic
    def handle(self, *args, **options):
        senha = os.environ.get('TCC_DEMO_PASSWORD', '')
        if len(senha) < 12:
            raise CommandError('Defina TCC_DEMO_PASSWORD com ao menos 12 caracteres. Não será impressa.')
        matriz = Matriz.objects.filter(versao=options['versao']).first()
        if not matriz:
            raise CommandError('Importe a matriz primeiro.')
        perfis = {'alpha_gestor': 'Gestor', 'alpha_tecnico': 'Técnico',
                  'alpha_operacional': 'Operacional', 'alpha_conselheiro': 'Conselheiro'}
        usuarios = {}
        for username, perfil in perfis.items():
            user, criado = User.objects.get_or_create(username=username)
            if criado:
                user.set_password(senha)
                user.save()
            # Repetição nunca redefine senhas nem privilégios existentes.
            usuarios[username] = user
            group, _ = Group.objects.get_or_create(name=perfil)
            user.groups.add(group)
        escola, _ = Instituicao.objects.get_or_create(nome='Escola Fictícia Alpha (caso sintético)',
                                                      responsavel=usuarios['alpha_gestor'])
        for username, perfil in perfis.items():
            profile, criado = PerfilUsuario.objects.get_or_create(usuario=usuarios[username],
                defaults={'instituicao': escola, 'perfil': perfil})
            if not criado and (profile.instituicao_id != escola.pk or profile.perfil != perfil):
                raise CommandError('Usuário Alpha já vinculado a outro contexto; nenhuma alteração aplicada.')
        existente = escola.avaliacoes.filter(matriz=matriz, finalizada_em__isnull=False).first()
        if existente:
            self.stdout.write(f'Alpha já disponível: avaliação {existente.pk}. Senhas preservadas.')
            return
        avaliacao = Avaliacao.objects.create(instituicao=escola, matriz=matriz)
        niveis = {'GV': 2, 'ID': 3, 'PR': 3, 'DE': 2, 'RS': 1, 'RC': 2}
        for controle in matriz.controles.all():
            Resposta.objects.create(avaliacao=avaliacao, controle=controle,
                nivel=1 if controle.codigo == 'C04' else niveis[controle.funcao],
                justificativa='Resposta sintética para demonstração; não reproduz dados empíricos do artigo.')
        resultado = finalizar(avaliacao.pk)
        self.stdout.write(self.style.SUCCESS(f'Alpha criada: avaliação {avaliacao.pk}; score {resultado.dados["score_geral"]}.'))
        self.stdout.write('Usuários: ' + ', '.join(perfis))
