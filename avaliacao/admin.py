from django.contrib import admin
from .models import Instituicao, Matriz, Controle, Avaliacao, Resposta, Resultado, PerfilUsuario


@admin.register(Instituicao)
class InstituicaoAdmin(admin.ModelAdmin):
    list_display = ['nome', 'responsavel', 'criada_em']
    search_fields = ['nome']


class SomenteLeitura(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Controle)
class ControleAdmin(SomenteLeitura):
    list_display = ['codigo', 'matriz', 'funcao', 'controle', 'contexto', 'mandatorio', 'rsdm', 'peso']
    list_filter = ['matriz', 'funcao', 'contexto', 'mandatorio', 'rsdm']
    search_fields = ['codigo', 'controle', 'pergunta']


@admin.register(Avaliacao)
class AvaliacaoAdmin(SomenteLeitura):
    list_display = ['id', 'instituicao', 'matriz', 'finalizada_em']


admin.site.register(Matriz, SomenteLeitura)
admin.site.register(Resposta, SomenteLeitura)
admin.site.register(Resultado, SomenteLeitura)
admin.site.register(PerfilUsuario)
admin.site.site_header = 'TCC FH — beta experimental'
