# TCC FH — beta de avaliação de maturidade

**S1 e S2 implementados em 2026-10-10.** Django/SQLite, importação versionada, login, cadastro,
questionário por função NIST, resultados e recomendações rastreáveis.
Os quatro dashboards gráficos estão disponíveis, com Chart.js 4.5.1 local, recomendações por perfil e resultado completo rastreável. Manual PDF e pacote S2 atualizados; ensaio e congelamento final ficam no S3.

Modelo experimental: escala 1–4, pesos e RSDM aguardam validação acadêmica.
O indicador LGPD representa lacunas nos controles associados à lei, não certificação de conformidade.
A Escola Alpha é um caso sintético, sem calibragem para reproduzir o 2,4 publicado no artigo.

## Executar localmente

Esta é uma cópia para instalação nova. Use `LEIA_PRIMEIRO.txt` e o instalador na raiz do pacote.
O banco, a chave local e as senhas serão criados na máquina de destino.
Os comandos abaixo são uma alternativa de instalação manual.

Python 3.13 e Django 5.2 LTS. Bootstrap 5.3.8 está incluído localmente; a demo não depende de CDN.

```sh
cd ~/Projetos/tcc-fh-maturidade
python3.13 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python manage.py migrate
.venv/bin/python manage.py importar_matriz docs/MATRIZ_CONTROLES_v0.csv --versao v0.1
.venv/bin/python manage.py createsuperuser
```

Crie a escola sintética e quatro usuários locais, informando uma senha sem eco e sem gravá-la no histórico:

```sh
read -rs 'TCC_DEMO_PASSWORD?Senha local da demo (mínimo 12 caracteres): '; echo
export TCC_DEMO_PASSWORD
.venv/bin/python manage.py seed_alpha --versao v0.1
unset TCC_DEMO_PASSWORD
.venv/bin/python manage.py runserver 127.0.0.1:8000
```

O comando `read` acima é para zsh; em bash use `read -rsp 'Senha local: ' TCC_DEMO_PASSWORD`.
Usuários: `alpha_gestor`, `alpha_tecnico`, `alpha_operacional`, `alpha_conselheiro`.
Reexecutar o seed preserva senhas e não duplica a avaliação finalizada.

Abra http://127.0.0.1:8000/ e entre com um usuário Alpha.
O superusuário administra usuários e vínculos em `/admin/`; na aplicação também precisa ser responsável
pela instituição ou possuir PerfilUsuario vinculado. Grupos não dão acesso global aos dados.
A URL do resultado mostra automaticamente o dashboard do PerfilUsuario vinculado à instituição; responsáveis sem perfil recebem a visão Gestor. Grupos não definem o dashboard nem ampliam acesso. O resultado completo continua disponível aos quatro perfis.

## Dashboards S2

- Gestor: scores, risco, lacunas LGPD, barras por função e cinco prioridades.
- Técnico: radar, controles aplicáveis abaixo do nível 3, prioridades e rastreabilidade.
- Operacional: DE/RS, prontidão existente e ações sugeridas dessas funções.
- Conselheiro: GV, distribuição dos controles por nível e prioridades de governança.

Todos usam o snapshot do resultado finalizado. Nulos permanecem sem dados aplicáveis;
nenhum indicador novo foi criado. Alinhamento estratégico é discutido pelos controles GV.
Chart.js e a licença acompanham os arquivos estáticos; a apresentação funciona offline.

## Fluxo e revisão

1. Cadastre instituição e inicie avaliação com a última matriz importada.
2. Responda por função; salve antes de navegar. Rascunhos podem ser retomados.
3. Finalize somente depois de responder os 31 controles, com nível ou não aplicabilidade justificada.
4. Confira scores, risco, lacunas e recomendações; cada ação aponta ao controle e à resposta.

Avaliações finalizadas são imutáveis. Para revisar respostas, crie nova avaliação.
Para revisar conteúdo, importe um novo CSV com `--versao v1` e crie nova avaliação.
Mesmo conteúdo e versão são idempotentes; conteúdo diferente na mesma versão é rejeitado.
O admin apresenta matrizes/controles/resultados somente para leitura, preservando o CSV como fonte.
Edição em massa via ORM/SQL não faz parte do fluxo suportado e deve ser evitada.

Contrato do CSV: cabeçalho exato da matriz fornecida; IDs únicos C01…; seis funções NIST;
campos obrigatórios, flags `sim`/`não` e pesos derivados da metodologia. Alteração de pesos exige
nova implementação/versão metodológica e testes, além de nova matriz.
SHA-256 refere-se ao conteúdo lógico normalizado e ordenado, não aos bytes do arquivo original.

Os documentos em `docs/` são cópias da versão de referência para reprodução do sistema.
A revisão humana permanece em `IESGO/20_PROJETOS/2026-02/TCC_FH/03_MODELO_AVALIACAO/`.
Não execute o antigo `gerar_matriz_v0.py` sobre a revisão. O renderizador `sincronizar_matriz.py`
do vault gera MD a partir do CSV sem reescrevê-lo; use saída nova para preservar observações humanas.

## Validar e retomar

```sh
.venv/bin/python manage.py check
.venv/bin/python manage.py makemigrations --check --dry-run
.venv/bin/python manage.py test avaliacao
```

Validação em 2026-10-10: **33 testes passaram** na instalação definitiva; `check` sem alertas
e `makemigrations --check --dry-run` sem mudanças. Chromium/Playwright verificou login,
resultado com 31 controles, Bootstrap local, retomada do questionário e layout móvel (390 px)
sem overflow horizontal ou erros JavaScript. Os quatro dashboards foram conferidos em desktop e 390 px, sem erros JavaScript nem requisições externas; as tabelas também funcionam sem JavaScript. O manual e o ZIP S2 estão em TCC_FH/04_MANUAL_USO e TCC_FH/05_DISTRIBUICAO.

Testes cobrem cálculos/limites, exclusões, piso C04, ausência de dados, importação atômica,
versionamento, imutabilidade, questionário completo, CSRF, escape e isolamento institucional.
O seed sintetiza GV=2 (exceto C04=1), ID=3, PR=3, DE=2, RS=1 e RC=2; o resultado geral é calculado.
As notas do artigo e o 2,4 não são critérios de aprovação deste fixture.

S2 adiantado em 2026-10-10. Próximo passo: revisão humana da matriz e ensaio S3.
Fernanda revisa conteúdo até 2026-10-15. S3 em 2026-10-16: importar revisão, validar e preparar
demo local + PDF/resumo para envio, congelando até 17:45. Entrega oficial: 2026-10-17.
Se a revisão não chegar, a demo usa v0.1 identificada como provisória.

## Limites da beta local

Servidor somente em localhost; publicação e PostgreSQL dependem de configuração futura.
Não guardar dados reais de menores, evidências, senhas ou dados de clientes nesta demo.
O SQLite, o segredo local gerado automaticamente e o venv são ignorados pelo Git.
O segredo persistente `.local-secret` tem permissão 600; `DJANGO_SECRET_KEY` pode substituí-lo.
Não há upload de evidências, redefinição de senha por e-mail, MFA, rate limiting ou deploy de produção.

## Fontes consultadas

Acesso: **2026-10-10**. Parcialmente validado: INFOSEC indisponível; aprovação acadêmica pendente.

- [Caderno TCC](https://notebook.google.com/notebook/e516c873-817b-41f1-9076-018dc6679f7f): consulta sobre escala/Tiers, pesos, bases legais, lacunas, RSDM e Alpha; resposta e trechos citados lidos nesta sessão de planejamento/implementação. Sem fórmula específica RSDM ou respostas originais da Alpha.
- [Notebook obrigatório S17](https://notebook.google.com/notebook/c204a5de-6f06-4f76-b07a-f6681b51ad6a): consulta sobre autenticação, entradas e auditoria; conteúdo defensivo geral lido, sem orientação específica de Django/multitenancy.
- INFOSEC: `/run/media/r3v4n/jpeg_2tb/CyberVault_V2/Storage-Vault/10_RECURSOS/13_EDUCACIONAL/133_Bibliotecas_e_Acervos/11-PDFS_ESTUDOS_TIC/INFOSEC/` indisponível; `/mnt/seagate` também ausente. Nenhum arquivo/página consultado.
- HackTricks local: `80-APOIO/81-HACKTRICKS/hacktricks/src/network-services-pentesting/pentesting-web/django.md`, seções “Cache Manipulation to RCE” e “Host Header / Password Reset Poisoning”.
- [MITRE ATT&CK T1078](https://attack.mitre.org/techniques/T1078/), Valid Accounts: descrição de abuso de contas e acesso inicial, pertinente a identidade/acesso.
- [NIST CSWP 29](https://nvlpubs.nist.gov/nistpubs/CSWP/NIST.CSWP.29.pdf), §3 e Apêndices A/B; [Enunciado ANPD nº 1/2023](https://bibliotecadigital.mj.gov.br/bitstream/1/10215/2/Enunciado_ANPD_2023_1.html); [LGPD](https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm), dispositivos citados na metodologia.
- [Django 5.2](https://docs.djangoproject.com/en/5.2/) e [compatibilidade](https://docs.djangoproject.com/en/5.2/faq/install/): autenticação, formulários, ORM e beta SQLite.
- Projeto local: README, plano beta aprovado, CSV/MD e metodologia; revisão registrada em `docs/REVISAO_PROFESSOR_2026-10-10.md`.

Referências técnicas S2 (2026-10-10): [Chart.js 4.5.1](https://github.com/chartjs/Chart.js/releases/tag/v4.5.1), [integração UMD](https://www.chartjs.org/docs/latest/getting-started/integration.html) e [acessibilidade](https://www.chartjs.org/docs/latest/general/accessibility.html).

## Interface (redesign)

Tema escuro, tipografia Manrope embarcada, dashboards com Chart.js local. Veja `docs/DESIGN_SYSTEM.md`.
Nenhum modelo, cálculo, rota, formulário (nomes/valores de campo) ou regra de acesso foi alterado pelo redesign.
