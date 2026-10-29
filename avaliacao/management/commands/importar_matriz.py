import csv
import hashlib
import io
import json
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ValidationError
from django.db import transaction
from avaliacao.models import Controle, Matriz, FUNCOES, CONTEXTOS
from avaliacao.scoring import peso_controle

COLUNAS = ['id', 'funcao', 'codigo_csf', 'controle', 'pergunta', 'categoria', 'tipo_funcional',
           'contexto', 'base_legal', 'mandatorio', 'rsdm', 'nivel_1_inicial', 'nivel_2_intermediario',
           'nivel_3_gerenciado', 'nivel_4_otimizado', 'evidencia_sugerida', 'recomendacao', 'peso']


class Command(BaseCommand):
    help = 'Importa CSV validado, sem sobrescrever versões. Operação transacional e idempotente.'

    def add_arguments(self, parser):
        parser.add_argument('csv', type=Path)
        parser.add_argument('--versao', required=True)

    @transaction.atomic
    def handle(self, *args, **options):
        versao = options['versao']
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,49}', versao):
            raise CommandError('Versão deve ter até 50 caracteres alfanuméricos, ponto, hífen ou sublinhado.')
        try:
            reader = csv.DictReader(io.StringIO(options['csv'].read_text(encoding='utf-8-sig')))
            if reader.fieldnames != COLUNAS:
                raise CommandError('Cabeçalho CSV diferente do contrato da matriz v0.')
            linhas = list(reader)
        except (OSError, UnicodeError, csv.Error) as error:
            raise CommandError(str(error)) from error
        if not linhas:
            raise CommandError('Matriz vazia.')
        codigos = set()
        controles = []
        canonico = []
        for numero, linha in enumerate(linhas, 2):
            if None in linha or any(v is None or not v.strip() for v in linha.values()):
                raise CommandError(f'Linha {numero}: célula vazia ou coluna adicional.')
            linha = {k: v.strip() for k, v in linha.items()}
            codigo = linha.pop('id')
            if not re.fullmatch(r'C[0-9]{2,}', codigo) or codigo in codigos:
                raise CommandError(f'Linha {numero}: código inválido ou duplicado.')
            codigos.add(codigo)
            if linha['funcao'] not in dict(FUNCOES) or not re.fullmatch(r'(GV|ID|PR|DE|RS|RC)\.[A-Z]{2}-[0-9]{2}', linha['codigo_csf']):
                raise CommandError(f'Linha {numero}: função ou código CSF inválido.')
            if not linha['codigo_csf'].startswith(linha['funcao'] + '.'):
                raise CommandError(f'Linha {numero}: código CSF pertence a outra função.')
            if linha['contexto'] not in CONTEXTOS or linha['categoria'] not in ('Técnico', 'Administrativo', 'Físico') or linha['tipo_funcional'] not in ('Preventivo', 'Detectivo', 'Corretivo'):
                raise CommandError(f'Linha {numero}: contexto, categoria ou tipo inválido.')
            for campo in ('mandatorio', 'rsdm'):
                if linha[campo] not in ('sim', 'não'):
                    raise CommandError(f'Linha {numero}: {campo} deve ser sim ou não.')
                linha[campo] = linha[campo] == 'sim'
            try:
                peso = Decimal(linha['peso'])
                if not peso.is_finite() or peso != peso_controle(linha['contexto'], linha['mandatorio']):
                    raise CommandError(f'Linha {numero}: peso difere da metodologia v0.1.')
                linha['peso'] = peso
            except InvalidOperation as error:
                raise CommandError(f'Linha {numero}: peso inválido.') from error
            controle = Controle(codigo=codigo, **linha)
            try:
                controle.full_clean(exclude=['matriz'], validate_unique=False, validate_constraints=False)
            except ValidationError as error:
                raise CommandError(f'Linha {numero}: {error}') from error
            controles.append(controle)
            canonico.append({'codigo': codigo, **{k: str(v) if isinstance(v, Decimal) else v for k, v in linha.items()}})
        if {c.funcao for c in controles} != set(dict(FUNCOES)):
            raise CommandError('A matriz deve conter as seis funções NIST.')
        # Ordenação e espaços externos não alteram o conteúdo lógico da versão.
        digest = hashlib.sha256(json.dumps(sorted(canonico, key=lambda x: x['codigo']), ensure_ascii=False, sort_keys=True).encode()).hexdigest()
        existente = Matriz.objects.filter(versao=versao).first()
        if existente:
            if existente.sha256 != digest:
                raise CommandError('Versão já existe com outro conteúdo. Escolha nova versão.')
            self.stdout.write(f'{versao}: já importada; nenhuma alteração.')
            return
        matriz = Matriz.objects.create(versao=versao, sha256=digest)
        for controle in controles:
            controle.matriz = matriz
            controle.save()
        self.stdout.write(self.style.SUCCESS(f'{versao}: {len(controles)} controles importados.'))
