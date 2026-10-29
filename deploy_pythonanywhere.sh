#!/usr/bin/env bash
# Instala o sistema no PythonAnywhere (rode no console Bash, dentro da pasta ~/sistema).
set -euo pipefail
cd "$(dirname "$0")"

PYV=""
for v in 3.13 3.12 3.11 3.10; do
  if command -v "python$v" >/dev/null 2>&1; then PYV="$v"; break; fi
done
[ -n "$PYV" ] || { echo "ERRO: Python 3.10+ não encontrado."; exit 1; }
echo ">> Usando Python $PYV  (escolha ESTA MESMA versão na aba Web)"

[ -d "$HOME/venv" ] || "python$PYV" -m venv "$HOME/venv"
"$HOME/venv/bin/pip" install --quiet --upgrade pip
"$HOME/venv/bin/pip" install --quiet -r requirements.txt

echo ">> Criando banco e importando a matriz de controles"
"$HOME/venv/bin/python" manage.py migrate --noinput
"$HOME/venv/bin/python" manage.py importar_matriz docs/MATRIZ_CONTROLES_v0.csv --versao v0.1

echo ">> Coletando arquivos estáticos"
"$HOME/venv/bin/python" manage.py collectstatic --noinput

echo
echo "Pronto. Próximos passos: configure a aba Web (veja DEPLOY_PYTHONANYWHERE.md, passo 4)"
echo "e depois crie o seu usuário administrador:  ~/venv/bin/python manage.py createsuperuser"
