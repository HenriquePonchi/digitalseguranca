# Publicar no PythonAnywhere (plano gratuito "Beginner")

Resultado: `https://SEU_USUARIO.pythonanywhere.com`, com HTTPS, banco SQLite persistente e sem cartão de crédito.
Substitua **SEU_USUARIO** pelo nome de usuário que você escolher no cadastro.

## 1. Criar a conta
Cadastre-se em https://www.pythonanywhere.com e escolha o plano **Beginner** (grátis).
O nome de usuário vira o endereço do site. (Se usar a região EU, o domínio é `SEU_USUARIO.eu.pythonanywhere.com`.)

## 2. Enviar o projeto
1. Aba **Files** → *Upload a file* → envie `sistema_seguranca_digital_deploy.zip`.
2. Aba **Consoles** → *Bash* e rode:
   ```bash
   unzip sistema_seguranca_digital_deploy.zip
   ```
   Isso cria `/home/SEU_USUARIO/sistema`.

## 3. Instalar (um comando)
```bash
bash ~/sistema/deploy_pythonanywhere.sh
```
Cria o ambiente virtual em `~/venv`, instala as dependências, cria o banco, importa os 31 controles e coleta os estáticos.
Anote a versão do Python que o script exibir.

## 4. Configurar a aba Web
1. **Web** → *Add a new web app* → *Next* → **Manual configuration** → escolha a **mesma versão de Python** do passo 3.
2. Em **Virtualenv**, informe: `/home/SEU_USUARIO/venv`
3. Em **Code → Source code**, informe: `/home/SEU_USUARIO/sistema`
4. Clique no link do **WSGI configuration file**, **apague tudo** e cole:
   ```python
   import os, sys

   path = '/home/SEU_USUARIO/sistema'
   if path not in sys.path:
       sys.path.insert(0, path)

   os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
   os.environ['DJANGO_ALLOWED_HOSTS'] = 'SEU_USUARIO.pythonanywhere.com'

   from django.core.wsgi import get_wsgi_application
   application = get_wsgi_application()
   ```
   Salve.
5. Ative **Force HTTPS**.
6. Não precisa configurar "Static files": o WhiteNoise já serve CSS/JS.
7. Clique em **Reload**.

## 5. Criar os usuários
No console Bash:
```bash
cd ~/sistema

# Seu administrador (acesso a /admin/):
~/venv/bin/python manage.py createsuperuser

# OPCIONAL: caso sintético "Escola Alpha" + 4 usuários de demonstração
# (alpha_gestor, alpha_tecnico, alpha_operacional, alpha_conselheiro):
read -rsp 'Senha da demo (mín. 12 caracteres): ' TCC_DEMO_PASSWORD; echo
export TCC_DEMO_PASSWORD
~/venv/bin/python manage.py seed_alpha --versao v0.1
unset TCC_DEMO_PASSWORD
```
Abra `https://SEU_USUARIO.pythonanywhere.com` e entre.

## Segurança (o site agora é público na internet)
- Não há cadastro aberto: só entra quem você criar em `/admin/` ou via `seed_alpha`. Use **senhas fortes**, inclusive no admin.
- Conforme o README do projeto: **não insira dados reais** de menores, clientes ou evidências. Não há rate limiting nem MFA.
- O banco fica em `~/sistema/db.sqlite3`. Faça cópia de vez em quando (aba Files → baixar).

## Atualizar depois
Envie os arquivos novos, rode `~/venv/bin/python manage.py migrate` e `collectstatic --noinput`, e clique em **Reload**.

## Problemas comuns
- **"DisallowedHost" / erro 400**: o valor de `DJANGO_ALLOWED_HOSTS` no WSGI não bate com o endereço do site.
- **Erro 500**: aba Web → *Error log*. Quase sempre é versão de Python diferente entre o venv e a aba Web, ou caminho errado.
- **Site sem estilo**: rode `collectstatic --noinput` de novo e dê Reload.
- Planos gratuitos mudam; confira os limites atuais em https://www.pythonanywhere.com/pricing/
