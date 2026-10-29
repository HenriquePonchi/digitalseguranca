from django.urls import path
from . import views

urlpatterns = [
    path('', views.inicio, name='inicio'),
    path('instituicoes/nova/', views.nova_instituicao, name='nova_instituicao'),
    path('instituicoes/<int:instituicao_id>/avaliacoes/nova/', views.nova_avaliacao, name='nova_avaliacao'),
    path('avaliacoes/<int:pk>/questionario/<str:funcao>/', views.questionario, name='questionario'),
    path('avaliacoes/<int:pk>/finalizar/', views.finalizar_avaliacao, name='finalizar'),
    path('avaliacoes/<int:pk>/resultado/', views.resultado, name='resultado'),
    path('avaliacoes/<int:pk>/excluir/', views.excluir_avaliacao, name='excluir_avaliacao'),
]