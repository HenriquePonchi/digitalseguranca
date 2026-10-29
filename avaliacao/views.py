from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from .forms import InstituicaoForm, QuestionarioForm
from .models import Instituicao, Matriz, Avaliacao, Resposta, FUNCOES
from .services import finalizar
from .dashboards import contexto_dashboard


def instituicoes_visiveis(usuario):
    # Grupos de dashboard nunca concedem acesso global a outras instituições.
    return Instituicao.objects.filter(Q(responsavel=usuario) | Q(perfilusuario__usuario=usuario)).distinct()


def avaliacao_visivel(usuario, pk):
    return get_object_or_404(Avaliacao.objects.select_related('instituicao', 'matriz').filter(
        instituicao__in=instituicoes_visiveis(usuario)), pk=pk)


@login_required
def inicio(request):
    instituicoes = instituicoes_visiveis(request.user)
    return render(request, 'avaliacao/inicio.html', {
        'instituicoes': instituicoes,
        'avaliacoes': Avaliacao.objects.filter(instituicao__in=instituicoes).select_related('instituicao', 'matriz'),
        'matriz': Matriz.objects.order_by('-importada_em', '-pk').first(),
    })


@login_required
def nova_instituicao(request):
    form = InstituicaoForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        instituicao = form.save(commit=False)
        instituicao.responsavel = request.user
        instituicao.save()
        messages.success(request, 'Instituição cadastrada. Você já pode iniciar uma avaliação.')
        return redirect('inicio')
    return render(request, 'avaliacao/form.html', {'form': form, 'titulo': 'Cadastrar instituição'})


@login_required
@require_POST
def nova_avaliacao(request, instituicao_id):
    instituicao = get_object_or_404(instituicoes_visiveis(request.user), pk=instituicao_id)
    matriz = Matriz.objects.order_by('-importada_em', '-pk').first()
    if not matriz or not matriz.controles.exists():
        messages.error(request, 'Importe uma matriz antes de iniciar a avaliação.')
        return redirect('inicio')
    avaliacao = Avaliacao.objects.create(instituicao=instituicao, matriz=matriz)
    return redirect('questionario', pk=avaliacao.pk, funcao='GV')


@login_required
def questionario(request, pk, funcao):
    if funcao not in dict(FUNCOES):
        raise Http404
    avaliacao = avaliacao_visivel(request.user, pk)
    if avaliacao.finalizada_em:
        return redirect('resultado', pk=pk)
    controles = list(avaliacao.matriz.controles.filter(funcao=funcao))
    respostas = {r.controle_id: r for r in avaliacao.respostas.all()}
    form = QuestionarioForm(request.POST if request.method == 'POST' else None,
                            controles=controles, respostas=respostas)
    if request.method == 'POST' and form.is_valid():
        try:
            with transaction.atomic():
                atual = Avaliacao.objects.select_for_update().get(pk=pk)
                if atual.finalizada_em:
                    raise ValidationError('Avaliação já finalizada. As respostas não foram alteradas.')
                for controle in controles:
                    valor = form.cleaned_data[controle.codigo]
                    # Campo vazio mantém o rascunho pendente, inclusive após desmarcar uma resposta.
                    if not valor:
                        antiga = Resposta.objects.filter(avaliacao=atual, controle=controle).first()
                        if antiga:
                            antiga.delete()
                        continue
                    Resposta.objects.update_or_create(avaliacao=atual, controle=controle, defaults={
                        'nivel': None if valor == 'NA' else int(valor),
                        'nao_se_aplica': valor == 'NA',
                        'justificativa': form.cleaned_data[controle.codigo + '_justificativa'],
                    })
            messages.success(request, 'Respostas salvas. Você pode retomar depois.')
            ordem = [f for f, _ in FUNCOES]
            proxima = ordem[min(ordem.index(funcao) + 1, len(ordem) - 1)]
            return redirect('questionario', pk=pk, funcao=proxima)
        except ValidationError as error:
            form.add_error(None, error)
    return render(request, 'avaliacao/questionario.html', {
        'avaliacao': avaliacao, 'form': form, 'funcoes': FUNCOES, 'funcao': funcao,
        'respondidos': avaliacao.respostas.count(), 'total': avaliacao.matriz.controles.count(),
    })


@login_required
@require_POST
def finalizar_avaliacao(request, pk):
    avaliacao_visivel(request.user, pk)
    try:
        finalizar(pk)
    except ValidationError as error:
        messages.error(request, ' '.join(error.messages))
        return redirect('questionario', pk=pk, funcao='GV')
    return redirect('resultado', pk=pk)


@login_required
def resultado(request, pk):
    avaliacao = avaliacao_visivel(request.user, pk)
    if not avaliacao.finalizada_em:
        return redirect('questionario', pk=pk, funcao='GV')
    dados = avaliacao.resultado.dados
    contexto = {'avaliacao': avaliacao, 'dados': dados}
    contexto.update(contexto_dashboard(request.user, avaliacao, dados))
    return render(request, 'avaliacao/resultado.html', contexto)

def excluir_avaliacao(request, pk):
    avaliacao = get_object_or_404(Avaliacao, pk=pk)
    if request.method == 'POST':
        avaliacao.delete()
    return redirect('inicio')
